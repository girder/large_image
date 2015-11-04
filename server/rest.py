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
from girder.api.describe import Description
from girder.api.rest import loadmodel, RestException
from girder.models.model_base import AccessType

from .tilesource import TestTileSource, GirderTiffTileSource, TileSourceException


class TilesItemResource(Item):

    def __init__(self, apiRoot):
        self.resourceName = 'item'
        apiRoot.item.route('GET', (':itemId', 'tiles'), self.getTilesInfo)
        apiRoot.item.route('POST', (':itemId', 'tiles'), self.createTiles)
        apiRoot.item.route('GET', (':itemId', 'tiles', 'zxy', ':z', ':x', ':y'),
                           self.getTile)

    def _loadTileSource(self, itemId):
        if itemId == 'test':
            tileSource = TestTileSource(256)
        else:
            item = self.model('item').load(id=itemId, level=AccessType.READ,
                                           user=self.getCurrentUser(), exc=True)
            tileSource = GirderTiffTileSource(item)
        return tileSource

    @access.public
    def getTilesInfo(self, itemId, params):
        tileSource = self._loadTileSource(itemId)
        return tileSource.getMetadata()

    getTilesInfo.description = (
        Description(''))


    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def createTiles(self, item, params):
        return
    createTiles.description = (
        Description(''))


    @access.public
    def getTile(self, itemId, z, x, y, params):
        try:
            x, y, z = int(x), int(y), int(z)
        except ValueError:
            raise RestException('x, y, and z must be integers', code=400)

        tileSource = self._loadTileSource(itemId)
        try:
            tileData = tileSource.getTile(x, y, z)
        except TileSourceException as e:
            raise RestException(e.message, code=404)

        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        return lambda: tileData

    getTile.description = (
        Description(''))
