import json

import cherrypy
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

    def setContentHeaders(self, file, offset, endByte, contentDisposition=None):
        """
        Sets the Content-Length, Content-Disposition, Content-Type, and also
        the Content-Range header if this is a partial download.

        :param file: The file being downloaded.
        :param offset: The start byte of the download.
        :type offset: int
        :param endByte: The end byte of the download (non-inclusive).
        :type endByte: int or None
        :param contentDisposition: Content-Disposition response header
            disposition-type value, if None, Content-Disposition will
            be set to 'attachment; filename=$filename'.
        :type contentDisposition: str or None
        """
        isRangeRequest = cherrypy.request.headers.get('Range')
        setResponseHeader('Content-Type', file['mimeType'])
        setContentDisposition(file['name'], contentDisposition or 'attachment')

        if file.get('size') is not None:
            # Only set Content-Length and range request headers if we have a file size
            size = file['size']
            if endByte is None or endByte > size:
                endByte = size

            setResponseHeader('Content-Length', max(endByte - offset, 0))

            if offset or endByte < size or isRangeRequest:
                setResponseHeader('Content-Range', f'bytes {offset}-{endByte - 1}/{size}')

    def downloadFile(self, file, offset=0, headers=True, endByte=None,
                     contentDisposition=None, extraParameters=None, **kwargs):

        if headers:
            setResponseHeader('Accept-Ranges', 'bytes')
            self.setContentHeaders(file, offset, endByte, contentDisposition)

        def stream():
            # Perform the request
            # Try a single-part download first. If that doesn't work, do multipart.
            response = self._request_retrieve_instance_prefer_singlepart(file)

            bytes_read = 0
            for chunk in self._stream_retrieve_instance_response(response):
                if bytes_read < offset:
                    # We haven't reached the start of the offset yet
                    bytes_needed = offset - bytes_read
                    if bytes_needed >= len(chunk):
                        # Skip over the whole chunk...
                        bytes_read += len(chunk)
                        continue
                    else:
                        # Discard all bytes before the offset
                        chunk = chunk[bytes_needed:]
                        bytes_read += bytes_needed

                if endByte is not None and bytes_read + len(chunk) >= endByte:
                    # We have reached the end... remove all bytes after endByte
                    chunk = chunk[:endByte - bytes_read]
                    if chunk:
                        yield chunk

                    bytes_read += len(chunk)
                    break

                yield chunk
                bytes_read += len(chunk)

        return stream

    def _request_retrieve_instance_prefer_singlepart(self, file, transfer_syntax='*'):
        # Try to perform a singlepart request. If it fails, perform a multipart request
        # instead.
        response = None
        try:
            response = self._request_retrieve_instance(file, multipart=False,
                                                       transfer_syntax=transfer_syntax)
        except requests.HTTPError:
            # If there is an HTTPError, the server might not accept single-part requests...
            pass

        if self._is_singlepart_response(response):
            return response

        # Perform the multipart request instead
        return self._request_retrieve_instance(file, transfer_syntax=transfer_syntax)

    def _request_retrieve_instance(self, file, multipart=True, transfer_syntax='*'):
        # Multipart requests are officially supported by the DICOMweb standard.
        # Singlepart requests are not officially supported, but they are easier
        # to work with.
        # Google Healthcare API support it.
        # See here: https://cloud.google.com/healthcare-api/docs/dicom#dicom_instances

        # Create the URL
        client = _create_dicomweb_client(self.assetstore_meta)
        url = self._create_retrieve_instance_url(client, file)

        # Build the headers
        headers = {}
        if multipart:
            # This is officially supported by the DICOMweb standard.
            headers['Accept'] = '; '.join((
                'multipart/related',
                'type="application/dicom"',
                f'transfer-syntax={transfer_syntax}',
            ))
        else:
            # This is not officially supported by the DICOMweb standard,
            # but it is easier to work with, and some servers such as
            # Google Healthcare API support it.
            # See here: https://cloud.google.com/healthcare-api/docs/dicom#dicom_instances
            headers['Accept'] = f'application/dicom; transfer-syntax={transfer_syntax}'

        return client._http_get(url, headers=headers, stream=True)

    def _create_retrieve_instance_url(self, client, file):
        from dicomweb_client.web import _Transaction

        dicom_uids = file['dicom_uids']
        study_uid = dicom_uids['study_uid']
        series_uid = dicom_uids['series_uid']
        instance_uid = dicom_uids['instance_uid']

        return client._get_instances_url(
            _Transaction.RETRIEVE,
            study_uid,
            series_uid,
            instance_uid,
        )

    def _stream_retrieve_instance_response(self, response):
        # Check if the original request asked for multipart data
        if 'multipart/related' in response.request.headers.get('Accept', ''):
            yield from self._stream_dicom_multipart_response(response)
        else:
            # The content should *only* contain the DICOM file
            with response:
                yield from response.iter_content(BUF_SIZE)

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

    def _stream_dicom_multipart_response(self, response):
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

    def _infer_file_size(self, file):
        # Try various methods to infer the file size, without streaming the
        # whole file. Returns the file size if successful, or `None` if unsuccessful.
        if file.get('size') is not None:
            # The file size was already determined.
            return file['size']

        # Only method currently is inferring from single-part content_length
        return self._infer_file_size_singlepart_content_length(file)

    def _is_singlepart_response(self, response):
        if response is None:
            return False

        content_type = response.headers.get('Content-Type')
        return (
            response.status_code == 200 and
            not any(x in content_type for x in ('multipart/related', 'boundary'))
        )

    def _infer_file_size_singlepart_content_length(self, file):
        # First, try to see if single-part requests work, and if the Content-Length
        # is returned. This works for Google Healthcare API.
        try:
            response = self._request_retrieve_instance(file, multipart=False)
        except requests.HTTPError:
            # If there is an HTTPError, the server might not accept single-part requests...
            return

        if not self._is_singlepart_response(response):
            # Does not support single-part requests...
            return

        content_length = response.headers.get('Content-Length')
        if not content_length:
            # The server did not return a Content-Length
            return

        try:
            # The DICOM file size is equal to the Content-Length
            return int(content_length)
        except ValueError:
            return

    def _importData(self, parent, parentType, params, progress, user):
        if parentType not in ('folder', 'user', 'collection'):
            msg = f'Invalid parent type: {parentType}'
            raise ValidationException(msg)

        limit = params.get('limit')
        search_filters = params.get('search_filters', {})

        meta = self.assetstore_meta

        client = _create_dicomweb_client(meta)

        study_uid_key = dicom_key_to_tag('StudyInstanceUID')
        series_uid_key = dicom_key_to_tag('SeriesInstanceUID')
        instance_uid_key = dicom_key_to_tag('SOPInstanceUID')

        # Search for studies. Apply the limit and search filters.
        fields = [
            study_uid_key,
        ]
        if progress:
            progress.update(message='Searching for studies...')

        studies_results = client.search_for_studies(
            limit=limit,
            fields=fields,
            search_filters=search_filters,
        )

        # Search for all series in the returned studies.
        fields = [
            study_uid_key,
            series_uid_key,
        ]
        if progress:
            progress.update(message='Searching for series...')

        series_results = []
        for study in studies_results:
            study_uid = study[study_uid_key]['Value'][0]
            series_results += client.search_for_series(study_uid, fields=fields)

        # Create folders for each study, items for each series, and files for each instance.
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

                # Inferring the file size can take a long time, so don't
                # do it right away, unless we figure out a way to make it faster.
                # file['size'] = self._infer_file_size(file)
                file = File().save(file)

            items.append(item)

        return items

    def importData(self, parent, parentType, params, progress, user, **kwargs):
        """
        Import DICOMweb WSI instances from a DICOMweb server.

        :param parent: The parent object to import into.
        :param parentType: The model type of the parent object.
        :type parentType: str
        :param params: Additional parameters required for the import process.
            This dictionary may include the following keys:

            :limit: (optional) limit the number of studies imported.
            :filters: (optional) a dictionary/JSON string of additional search
                filters to use with dicomweb_client's `search_for_series()`
                function.

        :type params: dict
        :param progress: Object on which to record progress if possible.
        :type progress: :py:class:`girder.utility.progress.ProgressContext`
        :param user: The Girder user performing the import.
        :type user: dict or None
        :return: a list of items that were created
        """
        # Validate the parameters
        limit = params.get('limit') or None
        if limit is not None:
            error_msg = f'Invalid limit: {limit}'
            try:
                limit = int(limit)
            except ValueError:
                raise ValidationException(error_msg)

            if limit < 1:
                raise ValidationException(error_msg)

        search_filters = params.get('filters', {})
        if isinstance(search_filters, str):
            try:
                search_filters = json.loads(search_filters)
            except json.JSONDecodeError as e:
                msg = f'Invalid filters: "{params.get("filters")}". {e}'
                raise ValidationException(msg)

        items = self._importData(
            parent,
            parentType,
            {
                'limit': limit,
                'search_filters': search_filters,
            },
            progress,
            user,
        )

        if not items:
            msg = 'No studies matching the search filters were found'
            raise ValidationException(msg)

        return items

    @property
    def auth_session(self):
        return _create_auth_session(self.assetstore_meta)

    def getFileSize(self, file):
        # This function will compute the size of the DICOM file (a potentially
        # expensive operation, since it may have to stream the whole file).
        # The caller is expected to cache the result in file['size'].
        # This function is called when the size is needed, such as the girder
        # fuse mount code, and range requests.
        if file.get('size') is not None:
            # It has already been computed once. Return the cached size.
            return file['size']

        # Try to infer the file size without streaming, if possible.
        size = self._infer_file_size(file)
        if size:
            return size

        # We must stream the whole file to get the file size...
        size = 0
        response = self._request_retrieve_instance_prefer_singlepart(file)
        for chunk in self._stream_retrieve_instance_response(response):
            size += len(chunk)

        # This should get cached in file['size'] in File().updateSize().
        return size


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
