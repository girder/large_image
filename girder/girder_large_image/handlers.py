import contextlib
import logging
import os
import re
import time

from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

import girder
import large_image
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item
from girder.models.setting import Setting
from girder.notification import Notification

from . import constants, girder_tilesource
from .girder_tilesource import getGirderTileSource  # noqa
from .models.image_item import ImageItem

logger = logging.getLogger(__name__)
mimetypes = None


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
        # If the job looks finished, update it once more to force notifications
        if 'jobId' in item['largeImage'] and item['largeImage'].get('notify'):
            job = Job().load(item['largeImage']['jobId'], force=True)
            if job and job['status'] == JobStatus.SUCCESS:
                Job().save(job)
    else:
        if 's3FinalizeRequest' in fileObj and 'itemId' in fileObj:
            logger.info(f'Checking if S3 upload of {fileObj["name"]} is a large image')

            localPath = File().getLocalFilePath(fileObj)
            for _ in range(300):
                size = os.path.getsize(localPath)
                if size == fileObj['size'] and len(
                        open(localPath, 'rb').read(500)) == min(size, 500):
                    break
                logger.info(
                    f'S3 upload not fully present ({size}/{fileObj["size"]} bytes reported)')
                time.sleep(0.1)
            checkForLargeImageFiles(girder.events.Event(event.name, fileObj))


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
        Notification(
            type='large_image.finished_image_item',
            data={
                'job_id': job['_id'],
                'item_id': item['_id'],
                'success': status == JobStatus.SUCCESS,
                'status': status,
            },
            user={'_id': job.get('userId')},
        ).flush()


def checkForMergeDicom(item):
    item = ImageItem().load(item['_id'], force=True)
    if item['largeImage']['sourceName'] not in {'dicom', 'openslide'}:
        return
    if len(list(Item().childFiles(item=item, limit=2))) != 1:
        return
    intMetadata = ImageItem().getInternalMetadata(item)
    try:
        seriesUID = (
            intMetadata['openslide']['dicom.SeriesInstanceUID']
            if 'openslide' in intMetadata else
            intMetadata['dicom']['SeriesInstanceUID'])
        studyUID = (
            intMetadata['openslide']['dicom.StudyInstanceUID']
            if 'openslide' in intMetadata else
            intMetadata['dicom']['StudyInstanceUID'])
    except Exception:
        return
    base = list(Item().find({
        'folderId': item['folderId'],
        'largeImage.dicomSeriesUID': seriesUID,
        'largeImage.dicomStudyUID': studyUID}, limit=2))
    if len(base) > 1:
        return
    if len(base) == 0:
        item['largeImage']['dicomSeriesUID'] = seriesUID
        item['largeImage']['dicomStudyUID'] = studyUID
        ImageItem().save(item)
        return
    file = File().load(item['largeImage']['fileId'], force=True)
    girder.logger.info(f'Merging dicom file {str(file["_id"])} to item {str(base[0]["_id"])}')
    file['itemId'] = base[0]['_id']
    File().save(file)
    Item().remove(item)


def checkForLargeImageFiles(event):  # noqa
    girder_tilesource.loadGirderTileSources()

    file = event.info
    if 'file.save' in event.name and 's3FinalizeRequest' in file:
        return
    logger.info('Handling file %s (%s)', file['_id'], file['name'])
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
        if Setting().get(constants.PluginSettings.LARGE_IMAGE_MERGE_DICOM):
            try:
                checkForMergeDicom(item)
            except Exception:
                girder.logger.exception('Failed to check for DICOM')
        return
    except Exception:
        pass
    # Check for files that are from folder/image style images.  This is custom
    # per folder/image format
    imageFolderRecords = {
        'mrxs': {
            'match': r'^Slidedat.ini$',
            'up': 1,
            'folder': r'^(.*)$',
            'image': '\\1.mrxs',
        },
        'vsi': {
            'match': r'^.*\.ets$',
            'up': 2,
            'folder': r'^_(\.*)_$',
            'image': '\\1.vsi',
        },
    }
    for check in imageFolderRecords.values():
        if re.match(check['match'], file['name']):
            try:
                folderId = item['folderId']
                folder = None
                for _ in range(check['up']):
                    folder = Folder().load(folderId, force=True)
                    if not folder:
                        break
                    folderId = folder['parentId']
                if not folder or not re.match(check['folder'], folder['name']):
                    continue
                imageName = re.sub(check['folder'], check['image'], folder['name'])
                parentItem = Item().findOne({'folderId': folder['parentId'], 'name': imageName})
                if not parentItem:
                    continue
                files = list(Item().childFiles(item=parentItem, limit=2))
                if len(files) == 1:
                    parentFile = files[0]
                    ImageItem().createImageItem(parentItem, parentFile, createJob=False)
                    return
            except Exception:
                pass
    # We couldn't automatically set this as a large image
    logger.info(
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
                ('application/yaml', '.yaml', True),
                ('application/yaml', '.yml', True),
                ('application/vnd.geo+json', '.geojson', True),
            ]:
                if ext not in mimetypes.types_map:
                    mimetypes.add_type(mimeType, ext, std)

        alt = mimetypes.guess_type(fileObj.get('name', ''))[0]
        if alt is not None:
            fileObj['mimeType'] = alt


def handleSettingSave(event):
    """
    When certain settings are changed, clear the caches.
    """
    if event.info.get('key') == constants.PluginSettings.LARGE_IMAGE_ICC_CORRECTION:
        if event.info['value'] == Setting().get(
                constants.PluginSettings.LARGE_IMAGE_ICC_CORRECTION):
            return
        import gc

        from girder.api.rest import setResponseHeader

        large_image.config.setConfig('icc_correction', event.info['value'])
        large_image.cache_util.cachesClear()
        gc.collect()
        with contextlib.suppress(Exception):
            # ask the browser to clear the cache; it probably won't be honored
            setResponseHeader('Clear-Site-Data', '"cache"')
