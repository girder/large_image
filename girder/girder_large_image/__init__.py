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

import datetime
import json
import re
import warnings

from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

import girder
import large_image
from girder import events, logger
from girder.constants import AccessType
from girder.exceptions import RestException, ValidationException
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.notification import Notification
from girder.models.setting import Setting
from girder.plugin import GirderPlugin, getPlugin
from girder.settings import SettingDefault
from girder.utility import config, search, setting_utilities
from girder.utility.model_importer import ModelImporter

from . import constants, girder_tilesource
from .girder_tilesource import getGirderTileSource  # noqa
from .loadmodelcache import invalidateLoadModelCache
from .models.image_item import ImageItem
from .rest import addSystemEndpoints
from .rest.large_image_resource import LargeImageResource
from .rest.tiles import TilesItemResource

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _importlib_version
except ImportError:
    from importlib_metadata import PackageNotFoundError
    from importlib_metadata import version as _importlib_version
try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


mimetypes = None


# Girder 3 is pinned to use pymongo < 4; its warnings aren't relevant until
# that changes.
warnings.filterwarnings('ignore', category=UserWarning, module='pymongo')


def _postUpload(event):
    """
    Called when a file is uploaded. We check the parent item to see if it is
    expecting a large image upload, and if so we register this file as the
    result image.
    """
    fileObj = event.info['file']
    # There may not be an itemId (on thumbnails, for instance)
    if not fileObj.get('itemId'):
        return

    item = Item().load(fileObj['itemId'], force=True, exc=True)

    if item.get('largeImage', {}).get('expected') and (
            fileObj['name'].endswith('.tiff') or
            fileObj.get('mimeType') == 'image/tiff'):
        if fileObj.get('mimeType') != 'image/tiff':
            fileObj['mimeType'] = 'image/tiff'
            File().save(fileObj)
        del item['largeImage']['expected']
        item['largeImage']['fileId'] = fileObj['_id']
        item['largeImage']['sourceName'] = 'tiff'
        if fileObj['name'].endswith('.geo.tiff'):
            item['largeImage']['sourceName'] = 'gdal'
        Item().save(item)


def _updateJob(event):
    """
    Called when a job is saved, updated, or removed.  If this is a large image
    job and it is ended, clean up after it.
    """
    job = event.info['job'] if event.name == 'jobs.job.update.after' else event.info
    meta = job.get('meta', {})
    if (meta.get('creator') != 'large_image' or not meta.get('itemId') or
            meta.get('task') != 'createImageItem'):
        return
    status = job['status']
    if event.name == 'model.job.remove' and status not in (
            JobStatus.ERROR, JobStatus.CANCELED, JobStatus.SUCCESS):
        status = JobStatus.CANCELED
    if status not in (JobStatus.ERROR, JobStatus.CANCELED, JobStatus.SUCCESS):
        return
    item = Item().load(meta['itemId'], force=True)
    if not item or 'largeImage' not in item:
        return
    if item.get('largeImage', {}).get('expected'):
        # We can get a SUCCESS message before we get the upload message, so
        # don't clear the expected status on success.
        if status != JobStatus.SUCCESS:
            del item['largeImage']['expected']
        else:
            return
    notify = item.get('largeImage', {}).get('notify')
    msg = None
    if notify:
        del item['largeImage']['notify']
        if status == JobStatus.SUCCESS:
            msg = 'Large image created'
        elif status == JobStatus.CANCELED:
            msg = 'Large image creation canceled'
        else:  # ERROR
            msg = 'FAILED: Large image creation failed'
        msg += ' for item %s' % item['name']
    if (status in (JobStatus.ERROR, JobStatus.CANCELED) and
            'largeImage' in item):
        del item['largeImage']
    Item().save(item)
    if msg and event.name != 'model.job.remove':
        Job().updateJob(job, progressMessage=msg)
    if notify:
        Notification().createNotification(
            type='large_image.finished_image_item',
            data={
                'job_id': job['_id'],
                'item_id': item['_id'],
                'success': status == JobStatus.SUCCESS,
                'status': status
            },
            user={'_id': job.get('userId')},
            expires=datetime.datetime.utcnow() + datetime.timedelta(seconds=30))


def checkForLargeImageFiles(event):
    file = event.info
    possible = False
    mimeType = file.get('mimeType')
    if mimeType in girder_tilesource.KnownMimeTypes:
        possible = True
    exts = [ext.split()[0] for ext in file.get('exts') if ext]
    if set(exts[-2:]).intersection(girder_tilesource.KnownExtensions):
        possible = True
    if not file.get('itemId'):
        return
    autoset = Setting().get(constants.PluginSettings.LARGE_IMAGE_AUTO_SET)
    if not autoset or (not possible and autoset != 'all'):
        return
    item = Item().load(file['itemId'], force=True, exc=False)
    if not item or item.get('largeImage'):
        return
    try:
        ImageItem().createImageItem(item, file, createJob=False)
    except Exception:
        # We couldn't automatically set this as a large image
        girder.logger.info(
            'Saved file %s cannot be automatically used as a largeImage' % str(file['_id']))


def removeThumbnails(event):
    ImageItem().removeThumbnailFiles(event.info)


def prepareCopyItem(event):
    """
    When copying an item, adjust the largeImage fileId reference so it can be
    matched to the to-be-copied file.
    """
    srcItem, newItem = event.info
    if 'largeImage' in newItem:
        li = newItem['largeImage']
        for pos, file in enumerate(Item().childFiles(item=srcItem)):
            for key in ('fileId', 'originalId'):
                if li.get(key) == file['_id']:
                    li['_index_' + key] = pos
        Item().save(newItem, triggerEvents=False)


def handleCopyItem(event):
    """
    When copying an item, finish adjusting the largeImage fileId reference to
    the copied file.
    """
    newItem = event.info
    if 'largeImage' in newItem:
        li = newItem['largeImage']
        files = list(Item().childFiles(item=newItem))
        for key in ('fileId', 'originalId'):
            pos = li.pop('_index_' + key, None)
            if pos is not None and 0 <= pos < len(files):
                li[key] = files[pos]['_id']
        Item().save(newItem, triggerEvents=False)


def handleRemoveFile(event):
    """
    When a file is removed, check if it is a largeImage fileId.  If so, delete
    the largeImage record.
    """
    fileObj = event.info
    if fileObj.get('itemId'):
        item = Item().load(fileObj['itemId'], force=True, exc=False)
        if item and 'largeImage' in item and item['largeImage'].get('fileId') == fileObj['_id']:
            ImageItem().delete(item, [fileObj['_id']])


def handleFileSave(event):
    """
    When a file is first saved, mark its mime type based on its extension if we
    would otherwise just mark it as generic application/octet-stream.
    """
    fileObj = event.info
    if fileObj.get('mimeType', None) in {None, ''} or (
            '_id' not in fileObj and
            fileObj.get('mimeType', None) in {'application/octet-stream'}):
        global mimetypes

        if not mimetypes:
            import mimetypes

            if not mimetypes.inited:
                mimetypes.init()
            # Augment the standard mimetypes with some additional values
            for mimeType, ext, std in [
                ('text/yaml', '.yaml', True),
                ('text/yaml', '.yml', True),
            ]:
                if ext not in mimetypes.types_map:
                    mimetypes.add_type(mimeType, ext, std)

        alt = mimetypes.guess_type(fileObj.get('name', ''))[0]
        if alt is not None:
            fileObj['mimeType'] = alt


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
        raise RestException('The search query must be a string.')
    # If we have the beginning of the field specifier, don't do a search
    if re.match(r'^(k|ke|key|key:)$', query.strip()):
        return {k: [] for k in types}
    phrases = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', query)
    fields = set(phrase.split('key:', 1)[1] for phrase in phrases
                 if phrase.startswith('key:') and len(phrase.split('key:', 1)[1]))
    phrases = [phrase for phrase in phrases
               if not phrase.startswith('key:') or not len(phrase.split('key:', 1)[1])]
    if not len(fields):
        pipeline = [
            {'$project': {'arrayofkeyvalue': {'$objectToArray': '$$ROOT.%s' % metakey}}},
            {'$unwind': '$arrayofkeyvalue'},
            {'$group': {'_id': None, 'allkeys': {'$addToSet': '$arrayofkeyvalue.k'}}}
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
    logger.debug('Metadata search uses filter: %r' % filter)
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
                entry = resultModelInst.load(id=id, user=user, level=level, exc=False)
                if entry is not None and offset:
                    offset -= 1
                    continue
                elif entry is not None:
                    result[searchModels[model]['model']].append(resultModelInst.filter(entry, user))
                    if limit and len(result[searchModels[model]['model']]) == limit:
                        break
    return result


# Validators

@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
    constants.PluginSettings.LARGE_IMAGE_NOTIFICATION_STREAM_FALLBACK,
})
def validateBoolean(doc):
    val = doc['value']
    if str(val).lower() not in ('false', 'true', ''):
        raise ValidationException('%s must be a boolean.' % doc['key'], 'value')
    doc['value'] = (str(val).lower() != 'false')


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
    constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER
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
    constants.PluginSettings.LARGE_IMAGE_NOTIFICATION_STREAM_FALLBACK: True,
})


def unbindGirderEventsByHandlerName(handlerName):
    for eventName in events._mapping:
        events.unbind(eventName, handlerName)


class LargeImagePlugin(GirderPlugin):
    DISPLAY_NAME = 'Large Image'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        try:
            getPlugin('worker').load(info)
        except Exception:
            logger.debug('worker plugin is unavailable')

        unbindGirderEventsByHandlerName('large_image')

        ModelImporter.registerModel('image_item', ImageItem, 'large_image')
        large_image.config.setConfig('logger', girder.logger)
        large_image.config.setConfig('logprint', girder.logprint)
        # Load girder's large_image config
        curConfig = config.getConfig().get('large_image')
        for key, value in (curConfig or {}).items():
            large_image.config.setConfig(key, value)
        addSystemEndpoints(info['apiRoot'])

        girder_tilesource.loadGirderTileSources()
        TilesItemResource(info['apiRoot'])
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
        events.bind('model.item.remove', 'large_image.removeThumbnails', removeThumbnails)
        events.bind('server_fuse.unmount', 'large_image', large_image.cache_util.cachesClear)
        events.bind('model.file.remove', 'large_image', handleRemoveFile)
        events.bind('model.file.save', 'large_image', handleFileSave)

        search._allowedSearchMode.pop('li_metadata', None)
        search.addSearchMode('li_metadata', metadataSearchHandler)
