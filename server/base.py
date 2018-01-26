#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from girder import events, plugin, logger
from girder.constants import AccessType, SettingDefault
from girder.exceptions import ValidationException
from girder.models.file import File
from girder.models.item import Item
from girder.models.notification import Notification
from girder.models.setting import Setting
from girder.utility import setting_utilities

from . import constants
from .models.annotation import Annotation
from .models.image_item import ImageItem
from .loadmodelcache import invalidateLoadModelCache


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
        Item().save(item)


def _updateJob(event):
    """
    Called when a job is saved, updated, or removed.  If this is a large image
    job and it is ended, clean up after it.
    """
    from girder.plugins.jobs.constants import JobStatus
    from girder.plugins.jobs.models.job import Job

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
    if mimeType in ('image/tiff', 'image/x-tiff', 'image/x-ptif'):
        possible = True
    exts = file.get('exts')
    if exts and exts[-1] in ('svs', 'ptif', 'tif', 'tiff', 'ndpi'):
        possible = True
    if not file.get('itemId') or not possible:
        return
    if not Setting().get(constants.PluginSettings.LARGE_IMAGE_AUTO_SET):
        return
    item = Item().load(file['itemId'], force=True, exc=False)
    if not item or item.get('largeImage'):
        return
    try:
        ImageItem().createImageItem(item, file, createJob=False)
    except Exception:
        # We couldn't automatically set this as a large image
        logger.info('Saved file %s cannot be automatically used as a '
                    'largeImage' % str(file['_id']))


def removeThumbnails(event):
    ImageItem().removeThumbnailFiles(event.info)


# Validators

@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
    constants.PluginSettings.LARGE_IMAGE_AUTO_SET,
})
def validateBoolean(doc):
    val = doc['value']
    if str(val).lower() not in ('false', 'true', ''):
        raise ValidationException('%s must be a boolean.' % doc['key'], 'value')
    doc['value'] = (str(val).lower() != 'false')


@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA,
    constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN,
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


# Defaults

# Defaults that have fixed values can just be added to the system defaults
# dictionary.
SettingDefault.defaults.update({
    constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS: True,
    constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER: True,
    constants.PluginSettings.LARGE_IMAGE_AUTO_SET: True,
    constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES: 10,
    constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE: 4096,
})


# Configuration and load

@plugin.config(
    name='Large image',
    description='Create, serve, and display large multiresolution images.',
    version='0.2.0',
    dependencies={'worker'},
)
def load(info):
    from .rest import TilesItemResource, LargeImageResource, AnnotationResource

    TilesItemResource(info['apiRoot'])
    info['apiRoot'].large_image = LargeImageResource()
    info['apiRoot'].annotation = AnnotationResource()

    Item().exposeFields(level=AccessType.READ, fields='largeImage')
    # Ask for the annotation model to make sure it is initialized.
    Annotation()

    events.bind('data.process', 'large_image', _postUpload)
    events.bind('jobs.job.update.after', 'large_image', _updateJob)
    events.bind('model.job.save', 'large_image', _updateJob)
    events.bind('model.job.remove', 'large_image', _updateJob)
    events.bind('model.folder.save.after', 'large_image',
                invalidateLoadModelCache)
    events.bind('model.group.save.after', 'large_image',
                invalidateLoadModelCache)
    events.bind('model.item.remove', 'large_image', invalidateLoadModelCache)
    events.bind('model.item.save.after', 'large_image',
                invalidateLoadModelCache)
    events.bind('model.file.save.after', 'large_image',
                checkForLargeImageFiles)
    events.bind('model.item.remove', 'large_image', removeThumbnails)
