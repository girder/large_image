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

import cherrypy

from girder.api import access
from girder.api.v1.item import Item
from girder.api.describe import describeRoute, Description
from girder.api.rest import loadmodel, RestException
from girder.models.model_base import AccessType

from .tilesource import TestTileSource, TiffGirderTileSource, \
    TileSourceException


class TilesItemResource(Item):

    def __init__(self, apiRoot):
        # Don't call the parent (Item) constructor, to avoid redefining routes,
        # but do call the grandparent (Resource) constructor
        super(Item, self).__init__()

        self.resourceName = 'item'
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('DELETE', (':itemId', 'tiles'), self.deleteTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTile)

    def _loadTileSource(self, itemId, params):
        try:
            if itemId == 'test':
                tileSourceArgs = {}
                for paramName, paramType in [
                    ('minLevel', int),
                    ('maxLevel', int),
                    ('tileWidth', int),
                    ('tileHeight', int),
                    ('sizeX', int),
                    ('sizeY', int),
                    ('fractal', lambda val: val == 'true'),
                ]:
                    try:
                        if paramName in params:
                            tileSourceArgs[paramName] = \
                                paramType(params[paramName])
                    except ValueError:
                        raise RestException(
                            '"%s" parameter is an incorrect type.' % paramName)
                tileSource = TestTileSource(**tileSourceArgs)
            else:
                # TODO: cache the user / item loading too
                item = self.model('item').load(
                    id=itemId, level=AccessType.READ,
                    user=self.getCurrentUser(), exc=True)
                tileSource = TiffGirderTileSource(item)
            return tileSource
        except TileSourceException as e:
            # TODO: sometimes this could be 400
            raise RestException(e.message, code=500)

    @describeRoute(
        Description('Get large image metadata.')
        .param('itemId', 'The ID of the item or "test".', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public
    def getTilesInfo(self, itemId, params):
        tileSource = self._loadTileSource(itemId, params)
        return tileSource.getMetadata()

    @describeRoute(
        Description('Create a large image for this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('fileId', 'The ID of the source file containing the image or '
               '"test".')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def createTiles(self, item, params):
        largeImageFileId = params.get('fileId')
        if not largeImageFileId:
            raise RestException('Missing "fileId" parameter.')

        if largeImageFileId == 'test':
            item['largeImage'] = 'test'

        else:
            largeImageFile = self.model('file').load(largeImageFileId,
                                                     force=True, exc=True)
            if largeImageFile['itemId'] != item['_id']:
                raise RestException('"fileId" must be a file on the same item'
                                    'as "itemId".')

            if largeImageFile['mimeType'] == 'image/tiff':
                # TODO: we should ensure that it is a multiresolution tiled TIFF
                item['largeImage'] = largeImageFile['_id']

            else:
                # TODO: implement a job that will create a multiresolution tiled
                # TIFF and save it to this Girder item
                newLargeImageFile = createLargeImageJob(
                    item=item,
                    originalFile=largeImageFile
                )
                item['largeImage'] = newLargeImageFile['_id']

        self.model('item').save(item)

        # TODO: a better response
        return {
            'created': True
        }

    @describeRoute(
        Description('Remove a large image from this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def deleteTiles(self, item, params):
        deleted = False
        if 'largeImage' in item:
            # TODO: if this file was created by the worker job, then delete it,
            # but if it was the originally uploaded file, leave it
            del item['largeImage']
            self.model('item').save(item)
            deleted = True
        # TODO: a better response
        return {
            'deleted': deleted
        }

    @describeRoute(
        Description('Get a large image tile.')
        .param('itemId', 'The ID of the item or "test".', paramType='path')
        .param('z', 'The layer number of the tile (0 is the most zoomed-out '
               'layer).', paramType='path')
        .param('x', 'The X coordinate of the tile (0 is the left side).',
               paramType='path')
        .param('y', 'The Y coordinate of the tile (0 is the top).',
               paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.cookie
    @access.public
    def getTile(self, itemId, z, x, y, params):
        try:
            x, y, z = int(x), int(y), int(z)
        except ValueError:
            raise RestException('x, y, and z must be integers', code=400)

        tileSource = self._loadTileSource(itemId, params)
        try:
            tileData = tileSource.getTile(x, y, z)
        except TileSourceException as e:
            raise RestException(e.message, code=404)

        cherrypy.response.headers['Content-Type'] = tileSource.getTileMimeType()
        return lambda: tileData
