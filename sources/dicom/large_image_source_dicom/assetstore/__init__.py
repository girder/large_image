from girder import events
from girder.api.v1.assetstore import Assetstore as AssetstoreResource
from girder.constants import AssetstoreType
from girder.models.assetstore import Assetstore
from girder.utility.assetstore_utilities import setAssetstoreAdapter

from .dicomweb_assetstore_adapter import DICOMWEB_META_KEY, DICOMwebAssetstoreAdapter
from .rest import DICOMwebAssetstoreResource

__all__ = [
    'DICOMWEB_META_KEY',
    'DICOMwebAssetstoreAdapter',
    'load',
]


def createAssetstore(event):
    """
    When an assetstore is created, make sure it has a well-formed DICOMweb
    information record.

    :param event: Girder rest.post.assetstore.before event.
    """
    params = event.info['params']

    if params.get('type') == AssetstoreType.DICOMWEB:
        event.addResponse(Assetstore().save({
            'type': AssetstoreType.DICOMWEB,
            'name': params.get('name'),
            DICOMWEB_META_KEY: {
                'url': params['url'],
                'qido_prefix': params.get('qido_prefix'),
                'wado_prefix': params.get('wado_prefix'),
                'auth_type': params.get('auth_type'),
                'auth_token': params.get('auth_token'),
            },
        }))
        event.preventDefault()


def updateAssetstore(event):
    """
    When an assetstore is updated, make sure the result has a well-formed set
    of DICOMweb information.

    :param event: Girder assetstore.update event.
    """
    params = event.info['params']
    store = event.info['assetstore']

    if store['type'] == AssetstoreType.DICOMWEB:
        store[DICOMWEB_META_KEY] = {
            'url': params['url'],
            'qido_prefix': params.get('qido_prefix'),
            'wado_prefix': params.get('wado_prefix'),
            'auth_type': params.get('auth_type'),
            'auth_token': params.get('auth_token'),
        }


def load(info):
    """
    Load the plugin into Girder.

    :param info: a dictionary of plugin information.  The name key contains the
                 name of the plugin according to Girder.
    """
    AssetstoreType.DICOMWEB = 'dicomweb'
    setAssetstoreAdapter(AssetstoreType.DICOMWEB, DICOMwebAssetstoreAdapter)
    events.bind('assetstore.update', 'dicomweb_assetstore', updateAssetstore)
    events.bind('rest.post.assetstore.before', 'dicomweb_assetstore',
                createAssetstore)

    (AssetstoreResource.createAssetstore.description
        .param('url', 'The base URL for the DICOMweb server (for DICOMweb)',
               required=False)
        .param('qido_prefix', 'The QIDO URL prefix for the server, if needed (for DICOMweb)',
               required=False)
        .param('wado_prefix', 'The WADO URL prefix for the server, if needed (for DICOMweb)',
               required=False)
        .param('auth_type',
               'The authentication type required for the server, if needed (for DICOMweb)',
               required=False)
        .param('auth_token',
               'Token for authentication if needed (for DICOMweb)',
               required=False))

    info['apiRoot'].dicomweb_assetstore = DICOMwebAssetstoreResource()
