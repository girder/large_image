from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import TokenScope
from girder.exceptions import RestException
from girder.models.assetstore import Assetstore
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext

from .dicomweb_assetstore_adapter import DICOMwebAssetstoreAdapter


class DICOMwebAssetstoreResource(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'dicomweb_assetstore'
        self.route('POST', (':id', 'import'), self.importData)

    def _importData(self, assetstore, params, progress):
        """

        :param assetstore: the destination assetstore.
        :param params: a dictionary of parameters including destinationId,
            destinationType, progress, and filters.
        """
        user = self.getCurrentUser()

        destinationType = params['destinationType']
        if destinationType not in ('folder', 'user', 'collection'):
            msg = f'Invalid destinationType: {destinationType}'
            raise RestException(msg)

        parent = ModelImporter.model(destinationType).load(params['destinationId'], force=True,
                                                           exc=True)

        return DICOMwebAssetstoreAdapter(assetstore).importData(
            parent,
            destinationType,
            params,
            progress,
            user,
        )

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Import references to DICOM objects from a DICOMweb server')
        .modelParam('id', 'The ID of the assetstore representing the DICOMweb server.',
                    model=Assetstore)
        .param('destinationId', 'The ID of the parent folder, collection, or user '
               'in the Girder data hierarchy under which to import the files.')
        .param('destinationType', 'The type of the parent object to import into.',
               enum=('folder', 'user', 'collection'),
               required=False, default='folder')
        .param('limit', 'The maximum number of studies to import.',
               required=False, default=None)
        .param('filters', 'Any search parameters to filter the studies query.',
               required=False, default='{}')
        .param('progress', 'Whether to record progress on this operation.',
               required=False, default=False, dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403),
    )
    def importData(self, assetstore, destinationId, destinationType, limit, filters, progress):
        user = self.getCurrentUser()

        with ProgressContext(
            progress, user=user, title='Importing DICOM references',
        ) as ctx:
            return self._importData(assetstore, params={
                'destinationId': destinationId,
                'destinationType': destinationType,
                'limit': limit,
                'filters': filters,
            }, progress=ctx)
