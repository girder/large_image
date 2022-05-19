import yaml

from girder import logger
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute
from girder.api.rest import boundHandler
from girder.constants import AccessType, SortDir, TokenScope
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item


def addSystemEndpoints(apiRoot):
    """
    This adds endpoints to routes that already exist in Girder.

    :param apiRoot: Girder api root class.
    """
    apiRoot.folder.route('GET', (':id', 'yaml_config', ':name'), getYAMLConfigFile)


def _mergeDictionaries(a, b):
    """
    Merge two dictionaries recursively.  If the second dictionary (or any
    sub-dictionary) has a special key, value of '__all__': True, the updated
    dictionary only contains values from the second dictionary and excludes
    the __all__ key.

    :param a: the first dictionary.  Modified.
    :param b: the second dictionary that gets added to the first.
    :returns: the modified first dictionary.
    """
    if b.get('__all__') is True:
        a.clear()
    for key in b:
        if isinstance(a.get(key), dict) and isinstance(b[key], dict):
            _mergeDictionaries(a[key], b[key])
        elif key != '__all__' or b[key] is not True:
            a[key] = b[key]
    return a


def adjustConfigForUser(config, user):
    """
    Given the current user, adjust the config so that only relevant and
    combined values are used.  If the root of the config dictionary contains
    "access": {"user": <dict>, "admin": <dict>}, the base values are updated
    based on the user's access level.  If the root of the config contains
    "group": {<group-name>: <dict>, ...}, the base values are updated for
    every group the user is a part of.

    The order of update is groups in C-sort alphabetical order followed by
    access/user and then access/admin as they apply.

    :param config: a config dictionary.
    """
    if not isinstance(config, dict):
        return config
    if isinstance(config.get('groups'), dict):
        groups = config.pop('groups')
        if user:
            for group in Group().find(
                    {'_id': {'$in': user['groups']}}, sort=[('name', SortDir.ASCENDING)]):
                if isinstance(groups.get(group['name']), dict):
                    config = _mergeDictionaries(config, groups[group['name']])
    if isinstance(config.get('access'), dict):
        accessList = config.pop('access')
        if user and isinstance(accessList.get('user'), dict):
            config = _mergeDictionaries(config, accessList['user'])
        if user and user.get('admin') and isinstance(accessList.get('admin'), dict):
            config = _mergeDictionaries(config, accessList['admin'])
    return config


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
    .errorResponse()
)
@boundHandler()
def getYAMLConfigFile(self, folder, name):
    user = self.getCurrentUser()
    while folder:
        item = Item().findOne({'folderId': folder['_id'], 'name': name},
                              user=user, level=AccessType.READ)
        if item:
            for file in Item().childFiles(item):
                if file['size'] > 10 * 1024 ** 2:
                    logger.info('Not loading %s -- too large' % file['name'])
                    continue
                with File().open(file) as fptr:
                    config = yaml.safe_load(fptr)
                    # combine and adjust config values based on current user
                    if isinstance(config, dict) and 'access' in config or 'group' in config:
                        config = adjustConfigForUser(config, user)
                    return config
        if folder['parentCollection'] != 'folder':
            if folder['name'] == '.config':
                break
            folder = Folder().findOne({
                'parentId': folder['parentId'],
                'parentCollection': folder['parentCollection'],
                'name': '.config'})
        else:
            folder = Folder().load(folder['parentId'], user=user, level=AccessType.READ)
