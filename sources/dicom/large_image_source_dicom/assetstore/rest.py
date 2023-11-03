import json

from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import Resource
from girder.constants import TokenScope
from girder.exceptions import RestException
from girder.models.assetstore import Assetstore
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext


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

        destinationType = params.get('destinationType', 'folder')
        if destinationType not in ('folder', 'user', 'collection'):
            msg = f'Invalid destinationType: {destinationType}'
            raise RestException(msg)

        parent = ModelImporter.model(destinationType).load(params['destinationId'], force=True,
                                                           exc=True)

        limit = params.get('limit') or None
        if limit is not None:
            error_msg = 'Invalid limit'
            try:
                limit = int(limit)
            except ValueError:
                raise RestException(error_msg)

            if limit < 1:
                raise RestException(error_msg)

        try:
            search_filters = json.loads(params.get('filters') or '{}')
        except json.JSONDecodeError as e:
            msg = f'Invalid filters: {e}'
            raise RestException(msg)

        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)
        items = adapter.importData(
            parent,
            destinationType,
            {
                'limit': limit,
                'search_filters': search_filters,
                'auth': None,
            },
            progress,
            user,
        )

        if not items:
            msg = 'No DICOM objects matching the search filters were found'
            raise RestException(msg)

    @access.admin(scope=TokenScope.DATA_WRITE)
    @autoDescribeRoute(
        Description('Import references to DICOM objects from a DICOMweb server')
        .modelParam('id', 'The ID of the assetstore representing the DICOMweb server.',
                    model=Assetstore)
        .param('destinationId', 'The ID of the parent folder, collection, or user '
               'in the Girder data hierarchy under which to import the files.')
        .param('destinationType', 'The type of the parent object to import into.',
               enum=('folder', 'user', 'collection'),
               required=True)
        .param('limit', 'The maximum number of results to import.',
               required=False, default=None)
        .param('filters', 'Any search parameters to filter DICOM objects.',
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
