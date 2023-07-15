from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, loadmodel
from girder.exceptions import RestException
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from girder.utility.progress import ProgressContext


class DICOMwebAssetstoreResource(Resource):
    def __init__(self):
        super().__init__()
        self.resourceName = 'dicomweb_assetstore'
        self.route('PUT', (':id', 'import'), self.importData)

    def _importData(self, assetstore, params):
        """

        :param assetstore: the destination assetstore.
        :param params: a dictionary of parameters including parentId,
            parentType, progress, and filters.
        """
        self.requireParams(('parentId'), params)

        user = self.getCurrentUser()

        parentType = params.get('parentType', 'folder')
        if parentType not in ('folder', 'user', 'collection'):
            msg = f'Invalid parentType: {parentType}'
            raise RestException(msg)

        parent = ModelImporter.model(parentType).load(params['parentId'], force=True,
                                                      exc=True)

        progress = self.boolParam('progress', params, default=False)

        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

        with ProgressContext(
            progress, user=user, title='Importing DICOM references',
        ) as ctx:
            adapter.importData(
                parent,
                parentType,
                {
                    'search_filters': params.get('filters', {}),
                    'auth': None,
                },
                ctx,
                user,
            )

    @access.admin
    @loadmodel(model='assetstore')
    @describeRoute(
        Description('Import references to DICOM objects from a DICOMweb server')
        .param('id', 'The ID of the assetstore representing the DICOMweb server.',
               paramType='path')
        .param('parentId', 'The ID of the parent folder, collection, or user '
               'in the Girder data hierarchy under which to import the files.')
        .param('parentType', 'The type of the parent object to import into.',
               enum=('folder', 'user', 'collection'),
               required=False)
        .param('filters', 'Any search parameters to filter DICOM objects.',
               required=False)
        .param('progress', 'Whether to record progress on this operation ('
               'default=False)', required=False, dataType='boolean')
        .errorResponse()
        .errorResponse('You are not an administrator.', 403),
    )
    def importData(self, assetstore, params):
        return self._importData(assetstore, params)
