import requests
from requests.exceptions import HTTPError

from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.utility.abstract_assetstore_adapter import AbstractAssetstoreAdapter

from ..dicom_tags import dicom_key_to_tag

DICOMWEB_META_KEY = 'dicomweb_meta'


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
        # FIXME: do we want to support downloading files? We probably
        # wouldn't download them the regular way, but we could instead
        # use a dicomweb-client like so:
        # instance = client.retrieve_instance(
        #     study_instance_uid=...,
        #     series_instance_uid=...,
        #     sop_instance_uid=...,
        # )
        # pydicom.filewriter.write_file('output_name.dcm', instance)
        msg = 'Download support not yet implemented for DICOMweb files.'
        raise NotImplementedError(
            msg,
        )

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

            # Create a placeholder file with the same name
            file = File().createFile(
                name=f'{series_uid}.dcm',
                creator=user,
                item=item,
                reuseExisting=True,
                assetstore=self.assetstore,
                mimeType=None,
                size=0,
                saveFile=False,
            )
            file['dicomweb_meta'] = {
                'study_uid': study_uid,
                'series_uid': series_uid,
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
