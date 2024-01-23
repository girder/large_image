import requests
from large_image_source_dicom.dicom_tags import dicom_key_to_tag
from large_image_source_dicom.dicomweb_utils import get_dicomweb_metadata
from requests.exceptions import HTTPError

from girder.api.rest import setContentDisposition, setResponseHeader
from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter

DICOMWEB_META_KEY = 'dicomweb_meta'

BUF_SIZE = 65536


class DICOMwebAssetstoreAdapter(AbstractAssetstoreAdapter):
    """
    This defines the interface to be used by all assetstore adapters.
    """

    def __init__(self, assetstore):
        super().__init__(assetstore)

    @staticmethod
    def validateInfo(doc):
        # Ensure that the assetstore is marked read-only
        doc['readOnly'] = True

        required_fields = [
            'url',
        ]

        info = doc.get(DICOMWEB_META_KEY, {})

        for field in required_fields:
            if field not in info:
                raise ValidationException('Missing field: ' + field)

        # If these are empty, they need to be converted to None
        convert_empty_fields_to_none = [
            'qido_prefix',
            'wado_prefix',
            'auth_type',
        ]

        for field in convert_empty_fields_to_none:
            if isinstance(info.get(field), str) and not info[field].strip():
                info[field] = None

        if info['auth_type'] == 'token' and not info.get('auth_token'):
            msg = 'A token must be provided if the auth type is "token"'
            raise ValidationException(msg)

        # Verify that we can connect to the server, if the authentication type
        # allows it.
        if info['auth_type'] in (None, 'token'):
            study_instance_uid_tag = dicom_key_to_tag('StudyInstanceUID')
            series_instance_uid_tag = dicom_key_to_tag('SeriesInstanceUID')

            client = _create_dicomweb_client(info)
            # Try to search for series. If we get an http error, raise
            # a validation exception.
            try:
                series = client.search_for_series(
                    limit=1,
                    fields=(study_instance_uid_tag, series_instance_uid_tag),
                )
            except HTTPError as e:
                msg = f'Failed to validate DICOMweb server settings: {e}'
                raise ValidationException(msg)

            # If we found a series, then test the wado prefix as well
            if series:
                # The previous query should have obtained uids for a specific
                # study and series.
                study_uid = series[0][study_instance_uid_tag]['Value'][0]
                series_uid = series[0][series_instance_uid_tag]['Value'][0]
                try:
                    # Retrieve the metadata of this series as a wado prefix test
                    client.retrieve_series_metadata(
                        study_instance_uid=study_uid,
                        series_instance_uid=series_uid,
                    )
                except HTTPError as e:
                    msg = f'Failed to validate DICOMweb WADO prefix: {e}'
                    raise ValidationException(msg)

        return doc

    @property
    def assetstore_meta(self):
        return self.assetstore[DICOMWEB_META_KEY]

    def initUpload(self, upload):
        msg = 'DICOMweb assetstores are import only.'
        raise NotImplementedError(msg)

    def finalizeUpload(self, upload, file):
        msg = 'DICOMweb assetstores are import only.'
        raise NotImplementedError(msg)

    def deleteFile(self, file):
        # We don't actually need to do anything special
        pass

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):

        if offset != 0 or endByte is not None:
            # FIXME: implement range requests
            msg = 'Range requests are not yet implemented'
            raise NotImplementedError(msg)

        from dicomweb_client.web import _Transaction

        dicom_uids = file['dicom_uids']
        study_uid = dicom_uids['study_uid']
        series_uid = dicom_uids['series_uid']
        instance_uid = dicom_uids['instance_uid']

        client = _create_dicomweb_client(self.assetstore_meta)

        if headers:
            setResponseHeader('Content-Type', file['mimeType'])
            setContentDisposition(file['name'], contentDisposition or 'attachment')

            # The filesystem assetstore calls the following function, which sets
            # the above and also sets the range and content-length headers:
            # `self.setContentHeaders(file, offset, endByte, contentDisposition)`
            # However, we can't call that since we don't have a great way of
            # determining the DICOM file size without downloading the whole thing.
            # FIXME: call that function if we find a way to determine file size.

        # Create the URL
        url = client._get_instances_url(
            _Transaction.RETRIEVE,
            study_uid,
            series_uid,
            instance_uid,
        )

        # Build the headers
        transfer_syntax = '*'
        accept_parts = [
            'multipart/related',
            'type="application/dicom"',
            f'transfer-syntax={transfer_syntax}',
        ]
        headers = {
            'Accept': '; '.join(accept_parts),
        }

        def stream():
            # Perform the request
            response = client._http_get(url, headers=headers, stream=True)
            yield from self._stream_retrieve_instance_response(response)

        return stream

    def _extract_media_type_and_boundary(self, response):
        content_type = response.headers['content-type']
        media_type, *ct_info = (ct.strip() for ct in content_type.split(';'))
        boundary = None
        for item in ct_info:
            attr, _, value = item.partition('=')
            if attr.lower() == 'boundary':
                boundary = value.strip('"').encode()
                break

        return media_type, boundary

    def _stream_retrieve_instance_response(self, response):
        # The first part of this function was largely copied from dicomweb-client's
        # _decode_multipart_message() function. But we can't use that function here
        # because it relies on reading the whole DICOM file into memory. We want to
        # avoid that and stream in chunks.

        # Split the content-type to find the media type and boundary.
        media_type, boundary = self._extract_media_type_and_boundary(response)
        if media_type.lower() != 'multipart/related':
            msg = f'Unexpected media type: "{media_type}". Expected "multipart/related".'
            raise ValueError(msg)

        # Ensure we have the multipart/related boundary.
        # The beginning boundary and end boundary look slightly different (in my
        # examples, beginning looks like '--{boundary}\r\n', and ending looks like
        # '\r\n--{boundary}--'). But we skip over the beginning boundary anyways
        # since it is before the message body. An end boundary might look like this:
        # \r\n--50d7ccd118978542c422543a7156abfce929e7615bc024e533c85801cd77--
        if boundary is None:
            content_type = response.headers['content-type']
            msg = f'Failed to locate boundary in content-type: {content_type}'
            raise ValueError(msg)

        # Both dicomweb-client and requests-toolbelt check for
        # the ending boundary exactly like so:
        ending = b'\r\n--' + boundary

        # Sometimes, there are a few extra bytes after the ending, such
        # as '--' and '\r\n'. Imaging Data Commons has '--\r\n' at the end.
        # But we don't care about what comes after the ending. As soon as we
        # encounter the ending, we are done.
        ending_size = len(ending)

        # Make sure the buffer is at least large enough to contain the
        # ending_size - 1, so that the ending cannot be split between more than 2 chunks.
        buffer_size = max(BUF_SIZE, ending_size - 1)

        with response:
            # Create our iterator
            iterator = response.iter_content(buffer_size)

            # First, stream until we encounter the first `\r\n\r\n`,
            # which denotes the end of the header section.
            header_found = False
            end_header_delimiter = b'\r\n\r\n'
            for chunk in iterator:
                if end_header_delimiter in chunk:
                    idx = chunk.index(end_header_delimiter)
                    # Save the first section of data. We will yield it later.
                    prev_chunk = chunk[idx + len(end_header_delimiter):]
                    header_found = True
                    break

            if not header_found:
                msg = 'Failed to find header in response content'
                raise ValueError(msg)

            # Now the header has been finished. Stream the data until
            # we encounter the ending boundary or finish the data.
            # The "prev_chunk" will start out set to the section right after the header.
            for chunk in iterator:
                # Ensure the chunk is large enough to contain the ending_size - 1, so
                # we can be sure the ending won't be split across more than 2 chunks.
                while len(chunk) < ending_size - 1:
                    try:
                        chunk += next(iterator)
                    except StopIteration:
                        break

                # Check if the ending is split between the previous and current chunks.
                if ending in prev_chunk + chunk[:ending_size - 1]:
                    # We found the ending! Remove the ending boundary and return.
                    data = prev_chunk + chunk[:ending_size - 1]
                    yield data.split(ending, maxsplit=1)[0]
                    return

                if prev_chunk:
                    yield prev_chunk

                prev_chunk = chunk

            # We did not find the ending while looping.
            # Check if it is in the final chunk.
            if ending in prev_chunk:
                # Found the ending in the final chunk.
                yield prev_chunk.split(ending, maxsplit=1)[0]
                return

            # We should have encountered the ending earlier and returned
            msg = 'Failed to find ending boundary in response content'
            raise ValueError(msg)

    def importData(self, parent, parentType, params, progress, user, **kwargs):
        """
        Import DICOMweb WSI instances from a DICOMweb server.

        :param parent: The parent object to import into.
        :param parentType: The model type of the parent object.
        :type parentType: str
        :param params: Additional parameters required for the import process.
            This dictionary may include the following keys:

            :limit: (optional) limit the number of studies imported.
            :search_filters: (optional) a dictionary of additional search
                filters to use with dicomweb_client's `search_for_series()`
                function.

        :type params: dict
        :param progress: Object on which to record progress if possible.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param user: The Girder user performing the import.
        :type user: dict or None
        :return: a list of items that were created
        """
        if parentType not in ('folder', 'user', 'collection'):
            msg = f'Invalid parent type: {parentType}'
            raise RuntimeError(msg)

        from wsidicom.uid import WSI_SOP_CLASS_UID

        limit = params.get('limit')
        search_filters = params.get('search_filters', {})

        meta = self.assetstore_meta

        client = _create_dicomweb_client(meta)

        study_uid_key = dicom_key_to_tag('StudyInstanceUID')
        series_uid_key = dicom_key_to_tag('SeriesInstanceUID')
        instance_uid_key = dicom_key_to_tag('SOPInstanceUID')

        # We are only searching for WSI datasets. Ignore all others.
        # FIXME: is this actually working? For the SLIM server at
        # https://imagingdatacommons.github.io/slim/, none of the series
        # report a SOPClassUID, but we still get all results anyways.
        search_filters = {
            'SOPClassUID': WSI_SOP_CLASS_UID,
            **search_filters,
        }
        fields = [
            study_uid_key,
            series_uid_key,
        ]
        if progress:
            progress.update(message='Searching for series...')

        # FIXME: might need to search in chunks for larger web servers
        series_results = client.search_for_series(
            fields=fields, limit=limit, search_filters=search_filters)
        items = []
        for i, result in enumerate(series_results):
            if progress:
                progress.update(total=len(series_results), current=i,
                                message='Importing series...')

            study_uid = result[study_uid_key]['Value'][0]
            series_uid = result[series_uid_key]['Value'][0]

            # Create a folder for the study, and an item for the series
            folder = Folder().createFolder(parent, parentType=parentType,
                                           name=study_uid, creator=user,
                                           reuseExisting=True)
            item = Item().createItem(name=series_uid, creator=user, folder=folder,
                                     reuseExisting=True)

            # Set the DICOMweb metadata
            item['dicomweb_meta'] = get_dicomweb_metadata(client, study_uid, series_uid)
            item['dicom_uids'] = {
                'study_uid': study_uid,
                'series_uid': series_uid,
            }
            item = Item().save(item)

            instance_results = client.search_for_instances(study_uid, series_uid)
            for instance in instance_results:
                instance_uid = instance[instance_uid_key]['Value'][0]

                file = File().createFile(
                    name=f'{instance_uid}.dcm',
                    creator=user,
                    item=item,
                    reuseExisting=True,
                    assetstore=self.assetstore,
                    mimeType='application/dicom',
                    size=None,
                    saveFile=False,
                )
                file['dicom_uids'] = {
                    'study_uid': study_uid,
                    'series_uid': series_uid,
                    'instance_uid': instance_uid,
                }
                file['imported'] = True
                File().save(file)

            items.append(item)

        return items

    @property
    def auth_session(self):
        return _create_auth_session(self.assetstore_meta)


def _create_auth_session(meta):
    auth_type = meta.get('auth_type')
    if auth_type is None:
        return None

    if auth_type == 'token':
        return _create_token_auth_session(meta['auth_token'])

    msg = f'Unhandled auth type: {auth_type}'
    raise NotImplementedError(msg)


def _create_token_auth_session(token):
    s = requests.Session()
    s.headers.update({'Authorization': f'Bearer {token}'})
    return s


def _create_dicomweb_client(meta):
    from dicomweb_client.api import DICOMwebClient

    session = _create_auth_session(meta)

    # Make the DICOMwebClient
    return DICOMwebClient(
        url=meta['url'],
        qido_url_prefix=meta.get('qido_prefix'),
        wado_url_prefix=meta.get('wado_prefix'),
        session=session,
    )
