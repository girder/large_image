#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import contextlib
import importlib.metadata
import json
import logging
import re
import threading
import warnings
from pathlib import Path

import yaml

import large_image
from girder import events
from girder.api import filter_logging
from girder.constants import AccessType, SortDir
from girder.exceptions import RestException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from girder.plugin import GirderPlugin, getPlugin, registerPluginStaticContent
from girder.settings import SettingDefault
from girder.utility import config, search, setting_utilities
from girder.utility.model_importer import ModelImporter

from . import constants, girder_tilesource
from .girder_tilesource import getGirderTileSource  # noqa
from .handlers import (_postUpload, _updateJob, checkForLargeImageFiles,
                       handleCopyItem, handleFileSave, handleRemoveFile,
                       handleSettingSave, prepareCopyItem, removeThumbnails)
from .loadmodelcache import invalidateLoadModelCache
from .models.image_item import ImageItem
from .rest import addSystemEndpoints
from .rest.item_meta import InternalMetadataItemResource
from .rest.large_image_resource import LargeImageResource
from .rest.tiles import TilesItemResource

with contextlib.suppress(importlib.metadata.PackageNotFoundError):
    __version__ = importlib.metadata.version(__name__)


logger = logging.getLogger(__name__)
mimetypes = None
_configWriteLock = threading.RLock()


# Some pymongo warnings aren't relevant
warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')


def metadataSearchHandler(  # noqa
        query, types, user=None, level=None, limit=0, offset=0, models=None,
        searchModels=None, metakey='meta'):
    """
    Provide a substring search on metadata.
    """
    models = models or {'item', 'folder'}
    if any(typ not in models for typ in types):
        raise RestException('The metadata search is only able to search in %r.' % models)
    if not isinstance(query, str):
        msg = 'The search query must be a string.'
        raise RestException(msg)
    # If we have the beginning of the field specifier, don't do a search
    if re.match(r'^(k|ke|key|key:)$', query.strip()):
        return {k: [] for k in types}
    phrases = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', query)
    fields = {phrase.split('key:', 1)[1] for phrase in phrases
              if phrase.startswith('key:') and len(phrase.split('key:', 1)[1])}
    phrases = [phrase for phrase in phrases
               if not phrase.startswith('key:') or not len(phrase.split('key:', 1)[1])]
    if not len(fields):
        pipeline = [
            {'$project': {'arrayofkeyvalue': {'$objectToArray': '$$ROOT.%s' % metakey}}},
            {'$unwind': '$arrayofkeyvalue'},
            {'$group': {'_id': None, 'allkeys': {'$addToSet': '$arrayofkeyvalue.k'}}},
        ]
        for model in (searchModels or types):
            modelInst = ModelImporter.model(*model if isinstance(model, tuple) else [model])
            result = list(modelInst.collection.aggregate(pipeline, allowDiskUse=True))
            if len(result):
                fields.update(list(result)[0]['allkeys'])
    if not len(fields):
        return {k: [] for k in types}
    logger.debug('Will search the following fields: %r', fields)
    usedPhrases = set()
    filter = []
    for phrase in phrases:
        if phrase[0] == phrase[-1] and phrase[0] in '"\'':
            phrase = phrase[1:-1]
        if not len(phrase) or phrase in usedPhrases:
            continue
        usedPhrases.add(phrase)
        try:
            numval = float(phrase)
            delta = abs(float(re.sub(r'[1-9]', '1', re.sub(
                r'\d(?=.*[1-9](0*\.|)0*$)', '0', str(numval)))))
        except Exception:
            numval = None
        phrase = re.escape(phrase)
        clause = []
        for field in fields:
            key = '%s.%s' % (metakey, field)
            clause.append({key: {'$regex': phrase, '$options': 'i'}})
            if numval is not None:
                clause.append({key: {'$eq': numval}})
                if numval > 0 and delta:
                    clause.append({key: {'$gte': numval, '$lt': numval + delta}})
                elif numval < 0 and delta:
                    clause.append({key: {'$lte': numval, '$gt': numval + delta}})
        if len(clause) > 1:
            filter.append({'$or': clause})
        else:
            filter.append(clause[0])
    if not len(filter):
        return []
    filter = {'$and': filter} if len(filter) > 1 else filter[0]
    result = {}
    logger.debug('Metadata search uses filter: %r', filter)
    for model in searchModels or types:
        modelInst = ModelImporter.model(*model if isinstance(model, tuple) else [model])
        if searchModels is None:
            result[model] = [
                modelInst.filter(doc, user)
                for doc in modelInst.filterResultsByPermission(
                    modelInst.find(filter), user, level, limit, offset)]
        else:
            resultModelInst = ModelImporter.model(searchModels[model]['model'])
            result[searchModels[model]['model']] = []
            foundIds = set()
            for doc in modelInst.filterResultsByPermission(modelInst.find(filter), user, level):
                id = doc[searchModels[model]['reference']]
                if id in foundIds:
                    continue
                foundIds.add(id)
                try:
                    entry = resultModelInst.load(id=id, user=user, level=level, exc=False)
                except Exception:
                    # We might have permission to view an annotation but not
                    # the item
                    continue
                if entry is not None and offset:
                    offset -= 1
                    continue
                if entry is not None:
                    result[searchModels[model]['model']].append(resultModelInst.filter(entry, user))
                    if limit and len(result[searchModels[model]['model']]) == limit:
                        break
    return result


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
    # Do this after merging groups, because the group access-level values can
    # override the base access-level options.  For instance, if the base has
    # an admin option, and the group has a user option, then doing this before
    # group application can end up with user options for an admin.
    if isinstance(config.get('access'), dict):
        accessList = config.pop('access')
        if user and isinstance(accessList.get('user'), dict):
            config = _mergeDictionaries(config, accessList['user'])
        if user and user.get('admin') and isinstance(accessList.get('admin'), dict):
            config = _mergeDictionaries(config, accessList['admin'])
    if isinstance(config.get('users'), dict):
        users = config.pop('users')
        if user and user['login'] in users:
            config = _mergeDictionaries(config, users[user['login']])
    return config


def addSettingsToConfig(config, user, name=None):
    """
    Add the settings for showing thumbnails and images in item lists to a
    config file if the itemList or itemListDialog options are not set.

    :param config: the config dictionary to modify.
    :param user: the current user.
    :param name: the name of the config file.
    """
    if name and name != '.large_image_config.yaml':
        return
    columns = []

    showThumbnails = Setting().get(constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS)
    if showThumbnails:
        columns.append({'type': 'image', 'value': 'thumbnail', 'title': 'Thumbnail'})

    extraSetting = constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC
    if user is not None:
        if user['admin']:
            extraSetting = constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN
        else:
            extraSetting = constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA

    showExtra = None
    with contextlib.suppress(Exception):
        showExtra = json.loads(Setting().get(extraSetting))
    if (isinstance(showExtra, dict) and 'images' in showExtra and
            isinstance(showExtra['images'], list)):
        for value in showExtra['images']:
            if value != '*':
                columns.append({'type': 'image', 'value': value, 'title': value.title()})

    columns.append({'type': 'record', 'value': 'name', 'title': 'Name'})
    columns.append({'type': 'record', 'value': 'controls', 'title': 'Controls'})
    columns.append({'type': 'record', 'value': 'size', 'title': 'Size'})

    if 'itemList' not in config:
        config['itemList'] = {'columns': columns}
    if 'itemListDialog' not in config:
        config['itemListDialog'] = {'columns': columns}


def yamlConfigFile(folder, name, user):
    """
    Get a resolved named config file based on a folder and user.

    :param folder: a Girder folder model.
    :param name: the name of the config file.
    :param user: the user that the response if adjusted for.
    :returns: either None if no config file, or a yaml record.
    """
    addConfig = None
    last = False
    while folder:
        item = Item().findOne({'folderId': folder['_id'], 'name': name})
        if item:
            for file in Item().childFiles(item):
                if file['size'] > 10 * 1024 ** 2:
                    logger.info('Not loading %s -- too large', file['name'])
                    continue
                with File().open(file) as fptr:
                    config = yaml.safe_load(fptr)
                    if isinstance(config, list) and len(config) == 1:
                        config = config[0]
                    # combine and adjust config values based on current user
                    if isinstance(config, dict) and (
                            'access' in config or 'groups' in config or 'users' in config):
                        config = adjustConfigForUser(config, user)
                    if addConfig and isinstance(config, dict):
                        config = _mergeDictionaries(config, addConfig)
                    if not isinstance(config, dict) or config.get('__inherit__') is not True:
                        addConfig = config
                        last = True
                        break
                    config.pop('__inherit__')
                    addConfig = config
        if last:
            break
        if folder['parentCollection'] != 'folder':
            if folder['name'] != '.config':
                folder = Folder().findOne({
                    'parentId': folder['parentId'],
                    'parentCollection': folder['parentCollection'],
                    'name': '.config'})
            else:
                last = 'setting'
            if not folder or last == 'setting':
                folderId = Setting().get(constants.PluginSettings.LARGE_IMAGE_CONFIG_FOLDER)
                if not folderId:
                    break
                folder = Folder().load(folderId, force=True)
                last = True
        else:
            folder = Folder().load(folder['parentId'], user=user, level=AccessType.READ)

    addConfig = {} if addConfig is None else addConfig
    addSettingsToConfig(addConfig, user, name)
    return addConfig


def yamlConfigFileWrite(folder, name, user, yaml_config, user_context):
    """
    If the user has appropriate permissions, create or modify an item in the
    specified folder with the specified name, storing the config value as a
    file.

    :param folder: a Girder folder model.
    :param name: the name of the config file.
    :param user: the user that the response if adjusted for.
    :param yaml_config: a yaml config string.
    :param user_context: whether these settings should only apply to the current user.
    """
    yaml_parsed = yaml.safe_load(yaml_config)
    item = Item().createItem(name, user, folder, reuseExisting=True)
    existingFiles = list(Item().childFiles(item))
    if (len(existingFiles) == 1 and
            existingFiles[0]['mimeType'] == 'application/yaml' and
            existingFiles[0]['name'] == name):
        if user_context:
            file = yaml.safe_load(File().open(existingFiles[0]).read())
            file.setdefault('users', {})
            file['users'].setdefault(user['login'], {})
            file['users'][user['login']].update(yaml_parsed)
            yaml_config = yaml.safe_dump(file)
        upload = Upload().createUploadToFile(
            existingFiles[0], user, size=len(yaml_config))
    else:
        if user_context:
            yaml_config = yaml.safe_dump({'users': {user['login']: yaml_parsed}})
        upload = Upload().createUpload(
            user, name, 'item', item, size=len(yaml_config),
            mimeType='application/yaml', save=True)
    newfile = Upload().handleChunk(upload, yaml_config)
    with _configWriteLock:
        for entry in list(Item().childFiles(item)):
            if entry['_id'] != newfile['_id'] and len(list(Item().childFiles(item))) > 1:
                File().remove(entry)


# Validators

@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
    constants.PluginSettings.LARGE_IMAGE_MERGE_DICOM,
})
def validateBoolean(doc):
    val = doc['value']
    if str(val).lower() not in ('false', 'true', ''):
        raise ValidationException('%s must be a boolean.' % doc['key'], 'value')
    doc['value'] = str(val).lower() != 'false'


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_ICC_CORRECTION,
})
def validateBooleanOrICCIntent(doc):
    import PIL.ImageCms

    val = doc['value']
    if ((hasattr(PIL.ImageCms, 'Intent') and hasattr(PIL.ImageCms.Intent, str(val).upper())) or
            hasattr(PIL.ImageCms, 'INTENT_' + str(val).upper())):
        doc['value'] = str(val).upper()
    else:
        if str(val).lower() not in ('false', 'true', ''):
            raise ValidationException(
                '%s must be a boolean or a named intent.' % doc['key'], 'value')
        doc['value'] = str(val).lower() != 'false'


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_AUTO_SET,
})
def validateBooleanOrAll(doc):
    val = doc['value']
    if str(val).lower() not in ('false', 'true', 'all', ''):
        raise ValidationException('%s must be a boolean or "all".' % doc['key'], 'value')
    doc['value'] = val if val in {'all'} else (str(val).lower() != 'false')


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC,
    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA,
    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN,
    constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_PUBLIC,
    constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA,
    constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_ADMIN,
})
def validateDictOrJSON(doc):
    val = doc['value']
    try:
        if isinstance(val, dict):
            doc['value'] = json.dumps(val)
        elif val is None or val.strip() == '':
            doc['value'] = ''
        else:
            parsed = json.loads(val)
            if not isinstance(parsed, dict):
                raise ValidationException('%s must be a JSON object.' % doc['key'], 'value')
            doc['value'] = val.strip()
    except (ValueError, AttributeError):
        raise ValidationException('%s must be a JSON object.' % doc['key'], 'value')


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES,
    constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE,
})
def validateNonnegativeInteger(doc):
    val = doc['value']
    try:
        val = int(val)
        if val < 0:
            raise ValueError
    except ValueError:
        raise ValidationException('%s must be a non-negative integer.' % (
            doc['key'], ), 'value')
    doc['value'] = val


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER,
})
def validateDefaultViewer(doc):
    doc['value'] = str(doc['value']).strip()


@setting_utilities.validator(constants.PluginSettings.LARGE_IMAGE_CONFIG_FOLDER)
def validateFolder(doc):
    if not doc.get('value', None):
        doc['value'] = None
    else:
        Folder().load(doc['value'], force=True, exc=True)


# Defaults

# Defaults that have fixed values can just be added to the system defaults
# dictionary.
SettingDefault.defaults.update({
    constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS: True,
    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER: True,
    constants.PluginSettings.LARGE_IMAGE_AUTO_SET: True,
    constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES: 10,
    constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE: 4096,
    constants.PluginSettings.LARGE_IMAGE_ICC_CORRECTION: True,
    constants.PluginSettings.LARGE_IMAGE_MERGE_DICOM: False,
})


def unbindGirderEventsByHandlerName(handlerName):
    for eventName in events._mapping:
        events.unbind(eventName, handlerName)


def patchMount():
    try:
        import girder.cli.mount

        def _flatItemFile(self, item):
            return next(File().collection.aggregate([
                {'$match': {'itemId': item['_id']}},
            ] + ([
                {'$addFields': {'matchLI': {'$eq': ['$_id', item['largeImage']['fileId']]}}},
            ] if 'largeImage' in item and 'expected' not in item['largeImage'] else []) + [
                {'$addFields': {'matchName': {'$eq': ['$name', item['name']]}}},
                {'$sort': {'matchLI': -1, 'matchName': -1, '_id': 1}},
                {'$limit': 1},
            ]), None)

        girder.cli.mount.ServerFuse._flatItemFile = _flatItemFile
    except Exception:
        pass


class LargeImagePlugin(GirderPlugin):
    DISPLAY_NAME = 'Large Image'

    def load(self, info):
        with contextlib.suppress(Exception):
            # the mapnik binary files can complain about TLS exhaustion if they
            # aren't loaded early.  This seems to be somehow slightly
            # intractable in linux, so just load them now, but fail quietly
            # since they are optional
            import large_image_source_mapnik  # noqa
        try:
            getPlugin('worker').load(info)
        except Exception:
            logger.debug('worker plugin is unavailable')

        unbindGirderEventsByHandlerName('large_image')

        static_dir = Path(__file__).parent / 'web_client' / 'dist'

        registerPluginStaticContent(
            plugin='large_image',
            css=['/style.css'],
            js=[
                '/girder-plugin-large-image.umd.cjs',
                # geojs must be loaded after the plugin JS
                '/extra/geojs.js',
            ],
            staticDir=static_dir,
            tree=info['serverRoot'],
        )

        ModelImporter.registerModel('image_item', ImageItem, 'large_image')
        large_image.config.setConfig('logger', logger)
        large_image.config.setConfig('logprint', logger)
        # Load girder's large_image config
        curConfig = config.getConfig().get('large_image')
        for key, value in (curConfig or {}).items():
            large_image.config.setConfig(key, value)
        large_image.config.setConfig('icc_correction', Setting().get(
            constants.PluginSettings.LARGE_IMAGE_ICC_CORRECTION))
        addSystemEndpoints(info['apiRoot'])

        girder_tilesource.loadGirderTileSources()
        TilesItemResource(info['apiRoot'])
        InternalMetadataItemResource(info['apiRoot'])
        info['apiRoot'].large_image = LargeImageResource()

        Item().exposeFields(level=AccessType.READ, fields='largeImage')

        events.bind('data.process', 'large_image', _postUpload)
        events.bind('jobs.job.update.after', 'large_image', _updateJob)
        events.bind('model.job.save', 'large_image', _updateJob)
        events.bind('model.job.remove', 'large_image', _updateJob)
        events.bind('model.folder.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.group.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.user.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.collection.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.item.remove', 'large_image', invalidateLoadModelCache)
        events.bind('model.item.copy.prepare', 'large_image', prepareCopyItem)
        events.bind('model.item.copy.after', 'large_image', handleCopyItem)
        events.bind('model.item.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.file.save.after', 'large_image', checkForLargeImageFiles)
        filter_logging.addLoggingFilter(
            r'Handling file ([0-9a-f]{24}) \(',
            frequency=1000, duration=10)
        events.bind('model.item.remove', 'large_image.removeThumbnails', removeThumbnails)
        events.bind('server_fuse.unmount', 'large_image', large_image.cache_util.cachesClear)
        events.bind('model.file.remove', 'large_image', handleRemoveFile)
        events.bind('model.file.save', 'large_image', handleFileSave)
        events.bind('model.setting.save', 'large_image', handleSettingSave)

        search._allowedSearchMode.pop('li_metadata', None)
        search.addSearchMode('li_metadata', metadataSearchHandler)

        patchMount()
