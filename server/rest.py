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
import os

from girder.api import access
from girder.api.v1.item import Item
from girder.api.describe import describeRoute, Description
from girder.api.rest import filtermodel, loadmodel, RestException
from girder.models.model_base import AccessType
from girder.plugins.romanesco import utils

from .tilesource import TestTileSource, TiffGirderTileSource, TileSourceException


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


    def _loadTileSource(self, itemId):
        try:
            if itemId == 'test':
                tileSource = TestTileSource(256)
            else:
                # TODO: cache the user / item loading too
                item = self.model('item').load(id=itemId, level=AccessType.READ,
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
        tileSource = self._loadTileSource(itemId)
        return tileSource.getMetadata()

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

        job = None

        if largeImageFileId == 'test':
            item['largeImage'] = 'test'
        else:
            largeImageFile = self.model('file').load(largeImageFileId,
                                                     force=True, exc=True)
            if largeImageFile['itemId'] != item['_id']:
                # TODO once we get rid of the "test" parameter, we should be
                # able to remove the itemId parameter altogether and just take
                # a file ID.
                raise RestException('"fileId" must be a file on the same item'
                                    'as "itemId".')

            if largeImageFile['mimeType'] == 'image/tiff':
                # TODO: we should ensure that it is a multiresolution tiled TIFF
                item['largeImage'] = largeImageFile['_id']

            else:
                job = self._createLargeImageJob(largeImageFile, item)
                # item['largeImage'] = newLargeImageFile['_id']
                # TODO figure out a way to set the largeImage field...

        self.model('item').save(item)

        return job

    def _createLargeImageJob(self, file, item):
        user = self.getCurrentUser()
        token = self.getCurrentToken()

        path = os.path.join(os.path.dirname(__file__), 'create_tiff.py')
        with open(path, 'r') as f:
            script = f.read()

        title = 'TIFF conversion: %s' % file['name']
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title=title, type='large_image_tiff', handler='romanesco_handler',
            user=user)
        jobToken = jobModel.createJobToken(job)

        task = {
            'mode': 'python',
            'script': script,
            'name': title,
            'inputs': [{
                'id': 'in_path',
                'target': 'filepath'
            }, {
                'id': 'out_filename',
            }],
            'outputs': [{
                'id': 'out_path',
                'target': 'filepath'
            }]
        }

        inputs = {
            'in_path': utils.girderInputSpec(
                item, resourceType='item', token=token),
            'out_filename': {
                'mode': 'inline',
                'data': os.path.splitext(file['name'])[0] + '.tiff'
            }
        }

        outputs = {
            'out_path': utils.girderOutputSpec(
                parent=item, token=token, parentType='item')
        }

        job['kwargs'] = {
            'task': task,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': utils.jobInfoSpec(job, jobToken),
            'auto_convert': False,
            'validate': False,
            'cleanup': False
        }

        job = jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

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
        .param('z', 'The layer number of the tile (0 is the most zoomed-out layer).', paramType='path')
        .param('x', 'The X coordinate of the tile (0 is the left side).', paramType='path')
        .param('y', 'The Y coordinate of the tile (0 is the top).', paramType='path')
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

        tileSource = self._loadTileSource(itemId)
        try:
            tileData = tileSource.getTile(x, y, z)
        except TileSourceException as e:
            raise RestException(e.message, code=404)

        cherrypy.response.headers['Content-Type'] = 'image/jpeg'
        return lambda: tileData
