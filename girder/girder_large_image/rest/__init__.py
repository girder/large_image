import json

from girder import logger
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import boundHandler
from girder.constants import AccessType, TokenScope
from girder.models.folder import Folder
from girder.models.item import Item


def addSystemEndpoints(apiRoot):
    """
    This adds endpoints to routes that already exist in Girder.

    :param apiRoot: Girder api root class.
    """
    apiRoot.folder.route('GET', (':id', 'yaml_config', ':name'), getYAMLConfigFile)
    apiRoot.folder.route('PUT', (':id', 'yaml_config', ':name'), putYAMLConfigFile)

    origItemFind = apiRoot.item._find
    origFolderFind = apiRoot.folder._find

    @boundHandler(apiRoot.item)
    def altItemFind(self, folderId, text, name, limit, offset, sort, filters=None):
        if sort and sort[0][0][0] == '[':
            sort = json.loads(sort[0][0])
        recurse = False
        if text and text.startswith('_recurse_:'):
            recurse = True
            text = text.split('_recurse_:', 1)[1]
        if filters is None and text and text.startswith('_filter_:'):
            try:
                filters = json.loads(text.split('_filter_:', 1)[1].strip())
                text = None
            except Exception as exc:
                logger.warning('Failed to parse _filter_ from text field: %r', exc)
        if filters:
            try:
                logger.debug('Item find filters: %s', json.dumps(filters))
            except Exception:
                pass
        if recurse:
            return _itemFindRecursive(
                self, origItemFind, folderId, text, name, limit, offset, sort, filters)
        return origItemFind(folderId, text, name, limit, offset, sort, filters)

    @boundHandler(apiRoot.item)
    def altFolderFind(self, parentType, parentId, text, name, limit, offset, sort, filters=None):
        if sort and sort[0][0][0] == '[':
            sort = json.loads(sort[0][0])
        return origFolderFind(parentType, parentId, text, name, limit, offset, sort, filters)

    if not hasattr(origItemFind, '_origFunc'):
        apiRoot.item._find = altItemFind
        altItemFind._origFunc = origItemFind
        apiRoot.folder._find = altFolderFind
        altFolderFind._origFunc = origFolderFind


def _itemFindRecursive(self, origItemFind, folderId, text, name, limit, offset, sort, filters):
    """
    If a recursive search within a folderId is specified, use an aggregation to
    find all folders that are descendants of the specified folder.  If there
    are any, then perform a search that matches any of those folders rather
    than just the parent.

    :param self: A reference to the Item() resource record.
    :param origItemFind: the original _find method, used as a fallback.

    For the remaining parameters, see girder/api/v1/item._find
    """
    from bson.objectid import ObjectId

    if folderId:
        pipeline = [
            {'$match': {'_id': ObjectId(folderId)}},
            {'$graphLookup': {
                'from': 'folder',
                'connectFromField': '_id',
                'connectToField': 'parentId',
                'depthField': '_depth',
                'as': '_folder',
                'startWith': '$_id',
            }},
            {'$group': {'_id': '$_folder._id'}},
        ]
        children = [ObjectId(folderId)] + next(Folder().collection.aggregate(pipeline))['_id']
        if len(children) > 1:
            filters = (filters.copy() if filters else {})
            if text:
                filters['$text'] = {
                    '$search': text,
                }
            if name:
                filters['name'] = name
            filters['folderId'] = {'$in': children}
            user = self.getCurrentUser()
            if isinstance(sort, list):
                sort.append(('parentId', 1))
            return Item().findWithPermissions(filters, offset, limit, sort=sort, user=user)
    return origItemFind(folderId, text, name, limit, offset, sort, filters)


@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Get a config file.')
    .notes(
        'This walks up the chain of parent folders until the file is found.  '
        'If not found, the .config folder in the parent collection or user is '
        'checked.\n\nAny yaml file can be returned.  If the top-level is a '
        'dictionary and contains keys "access" or "groups" where those are '
        'dictionaries, the returned value will be modified based on the '
        'current user.  The "groups" dictionary contains keys that are group '
        'names and values that update the main dictionary.  All groups that '
        'the user is a member of are merged in alphabetical order.  If a key '
        'and value of "\\__all\\__": True exists, the replacement is total; '
        'otherwise it is a merge.  If the "access" dictionary exists, the '
        '"user" and "admin" subdictionaries are merged if a calling user is '
        'present and if the user is an admin, respectively (both get merged '
        'for admins).')
    .modelParam('id', model=Folder, level=AccessType.READ)
    .param('name', 'The name of the file.', paramType='path')
    .errorResponse(),
)
@boundHandler()
def getYAMLConfigFile(self, folder, name):
    from .. import yamlConfigFile

    user = self.getCurrentUser()
    return yamlConfigFile(folder, name, user)


@access.public(scope=TokenScope.DATA_READ)
@autoDescribeRoute(
    Description('Get a config file.')
    .notes(
        'This replaces or creates an item in the specified folder with the '
        'specified name containing a single file also of the specified '
        'name.  The file is added to the default assetstore, and any existing '
        'file may be permanently deleted.')
    .modelParam('id', model=Folder, level=AccessType.READ)
    .param('name', 'The name of the file.', paramType='path')
    .param('user_context', 'Whether these settings should only apply to the '
           'current user.', paramType='query', dataType='boolean', default=False)
    .param('config', 'The contents of yaml config file to validate.',
           paramType='body'),
)
@boundHandler()
def putYAMLConfigFile(self, folder, name, config, user_context):
    from .. import yamlConfigFileWrite

    user = self.getCurrentUser()
    if not user_context:
        Folder().requireAccess(folder, user, AccessType.WRITE)
    config = config.read().decode('utf8')
    return yamlConfigFileWrite(folder, name, user, config, user_context)
