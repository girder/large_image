#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################

from girder import events, plugin
from girder.constants import AccessType
from girder.utility.model_importer import ModelImporter

from . import constants
from .loadmodelcache import invalidateLoadModelCache


def _postUpload(event):
    """
    Called when a file is uploaded. We check the parent item to see if it is
    expecting a large image upload, and if so we register this file as the
    result image.
    """
    fileObj = event.info['file']
    if 'itemId' not in fileObj:
        return

    Item = ModelImporter.model('item')
    item = Item.load(fileObj['itemId'], force=True, exc=True)

    if item.get('largeImage', {}).get('expected') and (
            fileObj['name'].endswith('.tiff') or
            fileObj.get('mimeType') == 'image/tiff'):
        if fileObj.get('mimeType') != 'image/tiff':
            fileObj['mimeType'] = 'image/tiff'
            ModelImporter.model('file').save(fileObj)
        del item['largeImage']['expected']
        item['largeImage']['fileId'] = fileObj['_id']
        item['largeImage']['sourceName'] = 'tiff'
        Item.save(item)


def validateSettings(event):
    key, val = event.info['key'], event.info['value']

    if key in (constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
               constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER):
        if str(val).lower() not in ('false', 'true', ''):
            return
        val = (str(val).lower() != 'false')
    elif key == constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER:
        val = str(val).strip()
    else:
        return
    event.info['value'] = val
    event.preventDefault().stopPropagation()


@plugin.config(
    name='Large image',
    description='Create, serve, and display large multiresolution images.',
    version='0.2.0',
    dependencies={'worker'},
)
def load(info):
    from .rest import TilesItemResource, AnnotationResource

    TilesItemResource(info['apiRoot'])
    info['apiRoot'].annotation = AnnotationResource()

    ModelImporter.model('item').exposeFields(
        level=AccessType.READ, fields='largeImage')
    # Ask for the annotation model to make sure it is initialized.
    ModelImporter.model('annotation', plugin='large_image')

    events.bind('data.process', 'large_image', _postUpload)
    events.bind('model.setting.validate', 'large_image', validateSettings)
    events.bind('model.folder.save.after', 'large_image',
                invalidateLoadModelCache)
    events.bind('model.group.save.after', 'large_image',
                invalidateLoadModelCache)
    events.bind('model.item.remove', 'large_image', invalidateLoadModelCache)
