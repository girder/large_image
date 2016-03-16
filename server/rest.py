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


class TilesItemResource(Item):

    def __init__(self, apiRoot):
        # Don't call the parent (Item) constructor, to avoid redefining routes,
        # but do call the grandparent (Resource) constructor
        super(Item, self).__init__()

        self.resourceName = 'item'
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)

        apiRoot.item.route('DELETE', (':itemId', 'tiles'), self.deleteTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTile)

    @describeRoute(
        Description('Create a large image for this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param('fileId', 'The ID of the source file containing the image or '
               '"test".')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    @filtermodel(model='job', plugin='jobs')
    def createTiles(self, item, params):
        largeImageFileId = params.get('fileId')
        if not largeImageFileId:
            raise RestException('Missing "fileId" parameter.')

        if largeImageFileId == 'test':
            item['largeImage'] = 'test'
            return None
        else:
            largeImageFile = self.model('file').load(
                largeImageFileId, force=True, exc=True)
            user = self.getCurrentUser()
            token = self.getCurrentToken()
            return self.model('image_item', 'large_image').createImageItem(
                item, largeImageFile, user, token)

    @staticmethod
    def _parseTestParams(params):
        tileSourceArgs = {}
        for paramName, paramType in [
            ('minLevel', int),
            ('maxLevel', int),
            ('tileWidth', int),
            ('tileHeight', int),
            ('sizeX', int),
            ('sizeY', int),
            ('fractal', lambda val: val == 'true'),
            ('encoding', str),
        ]:
            try:
                if paramName in params:
                    tileSourceArgs[paramName] = \
                        paramType(params[paramName])
            except ValueError:
                raise RestException(
                    '"%s" parameter is an incorrect type.' % paramName)
        return tileSourceArgs

    @describeRoute(
        Description('Get large image metadata.')
        .param('itemId', 'The ID of the item or "test".', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403)
    )
    @access.public
    def getTilesInfo(self, itemId, params):
        if itemId == 'test':
            item = 'test'
            imageArgs = self._parseTestParams(params)
        else:
            item = self.model('item').load(
                id=itemId, level=AccessType.READ,
                user=self.getCurrentUser(), exc=True)
            imageArgs = params

        return self.model('image_item', 'large_image').getMetadata(
            item, **imageArgs)

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
        if x < 0 or y < 0 or z < 0:
            raise RestException('x, y, and z must be positive integers',
                                code=400)

        if itemId == 'test':
            item = 'test'
            imageArgs = self._parseTestParams(params)
        else:
            # TODO: cache the user / item loading too
            item = self.model('item').load(
                id=itemId, level=AccessType.READ,
                user=self.getCurrentUser(), exc=True)
            imageArgs = params

        tileData, tileMime = self.model('image_item', 'large_image').getTile(
            item, x, y, z, **imageArgs)
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
