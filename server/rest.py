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
from girder.api.rest import filtermodel, loadmodel, RestException
from girder.models.model_base import AccessType

from .models import TileGeneralException


class TilesItemResource(Item):

    def __init__(self, apiRoot):
        # Don't call the parent (Item) constructor, to avoid redefining routes,
        # but do call the grandparent (Resource) constructor
        super(Item, self).__init__()

        self.resourceName = 'item'
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)
        apiRoot.item.route('DELETE', (':itemId', 'tiles'), self.deleteTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'thumbnail'),
                           self.getTilesThumbnail)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTile)
        apiRoot.item.route('GET', ('test', 'tiles'), self.getTestTilesInfo)
        apiRoot.item.route('GET', ('test', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTestTile)

    @describeRoute(
        Description('Create a large image for this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('fileId', 'The ID of the source file containing the image. '
                         'Required if there is more than one file in the item.',
               required=False)
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    @filtermodel(model='job', plugin='jobs')
    def createTiles(self, item, params):
        largeImageFileId = params.get('fileId')
        if largeImageFileId is None:
            files = list(self.model('item').childFiles(
                item=item, limit=2))
            if len(files) == 1:
                largeImageFileId = str(files[0]['_id'])
        if not largeImageFileId:
            raise RestException('Missing "fileId" parameter.')
        largeImageFile = self.model('file').load(
            largeImageFileId, force=True, exc=True)
        user = self.getCurrentUser()
        token = self.getCurrentToken()
        try:
            return self.model(
                'image_item', 'large_image').createImageItem(
                    item, largeImageFile, user, token)
        except TileGeneralException as e:
            raise RestException(e.message)

    @classmethod
    def _parseTestParams(cls, params):
        return cls._parseParams(params, False, [
            ('minLevel', int),
            ('maxLevel', int),
            ('tileWidth', int),
            ('tileHeight', int),
            ('sizeX', int),
            ('sizeY', int),
            ('fractal', lambda val: val == 'true'),
            ('encoding', str),
        ])

    @classmethod
    def _parseParams(cls, params, keepUnknownParams, typeList):
        results = {}
        if keepUnknownParams:
            results = dict(params)
        for paramName, paramType in typeList:
            try:
                if paramName in params:
                    results[paramName] = paramType(params[paramName])
            except ValueError:
                raise RestException(
                    '"%s" parameter is an incorrect type.' % paramName)
        return results

    @describeRoute(
        Description('Get large image metadata.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesInfo(self, item, params):
        # TODO: parse imageArgs?
        imageArgs = params
        try:
            return self.model('image_item', 'large_image').getMetadata(
                item, **imageArgs)
        except TileGeneralException as e:
            raise RestException(e.message, code=400)

    @describeRoute(
        Description('Get test large image metadata.')
    )
    @access.public
    def getTestTilesInfo(self, params):
        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        try:
            return self.model('image_item', 'large_image').getMetadata(
                item, **imageArgs)
        except TileGeneralException as e:
            raise RestException(e.message, code=400)

    @describeRoute(
        Description('Get a large image tile.')
        .param('itemId', 'The ID of the item.', paramType='path')
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
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTile(self, item, z, x, y, params):
        # TODO: cache the user / item loading in the 'loadmodel' decorator
        try:
            x, y, z = int(x), int(y), int(z)
        except ValueError:
            raise RestException('x, y, and z must be integers', code=400)
        if x < 0 or y < 0 or z < 0:
            raise RestException('x, y, and z must be positive integers',
                                code=400)

        # TODO: parse imageArgs?
        imageArgs = params
        try:
            tileData, tileMime = self.model(
                'image_item', 'large_image').getTile(
                    item, x, y, z, **imageArgs)
        except TileGeneralException as e:
            raise RestException(e.message, code=404)
        cherrypy.response.headers['Content-Type'] = tileMime
        return lambda: tileData

    @describeRoute(
        Description('Get a test large image tile.')
        .param('z', 'The layer number of the tile (0 is the most zoomed-out '
               'layer).', paramType='path')
        .param('x', 'The X coordinate of the tile (0 is the left side).',
               paramType='path')
        .param('y', 'The Y coordinate of the tile (0 is the top).',
               paramType='path')
    )
    @access.cookie
    @access.public
    def getTestTile(self, z, x, y, params):
        try:
            x, y, z = int(x), int(y), int(z)
        except ValueError:
            raise RestException('x, y, and z must be integers', code=400)
        if x < 0 or y < 0 or z < 0:
            raise RestException('x, y, and z must be positive integers',
                                code=400)

        item = {'largeImage': {'sourceName': 'test'}}
        imageArgs = self._parseTestParams(params)
        try:
            tileData, tileMime = self.model(
                'image_item', 'large_image').getTile(
                    item, x, y, z, **imageArgs)
        except TileGeneralException as e:
            raise RestException(e.message, code=404)
        cherrypy.response.headers['Content-Type'] = tileMime
        return lambda: tileData

    @describeRoute(
        Description('Remove a large image from this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def deleteTiles(self, item, params):
        deleted = self.model('image_item', 'large_image').delete(item)
        # TODO: a better response
        return {
            'deleted': deleted
        }

    @describeRoute(
        Description('Get a thumbnail of a large image item.')
        .notes('Aspect ratio is always preserved.  If both width and height '
               'are specified, the resulting thumbnail may be smaller in one '
               'of the two dimensions.  If neither width nor height is given, '
               'a default size will be returned.  '
               'This creates a thumbnail from the lowest level of the source '
               'image, which means that asking for a large thumbnail will not '
               'be a high-quality image.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('width', 'The maximum width of the thumbnail in pixels.',
               required=False, dataType='int')
        .param('height', 'The maximum height of the thumbnail in pixels.',
               required=False, dataType='int')
        .param('encoding', 'Thumbnail output encoding', required=False,
               enum=['JPEG', 'PNG'], default='JPEG')
    )
    @access.cookie
    @access.public
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getTilesThumbnail(self, item, params):
        params = self._parseParams(params, True, [
            ('width', int),
            ('height', int),
            ('jpegQuality', int),
            ('jpegSubsampling', int),
            ('encoding', str),
        ])
        try:
            thumbData, thumbMime = self.model(
                'image_item', 'large_image').getThumbnail(item, **params)
        except TileGeneralException as e:
            raise RestException(e.message)
        except ValueError as e:
            raise RestException('Value Error: %s' % e.message)
        cherrypy.response.headers['Content-Type'] = thumbMime
        return lambda: thumbData
