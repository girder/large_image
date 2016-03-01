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
from girder.models.model_base import AccessType, ValidationException
from girder.plugins.worker import utils as workerUtils
from girder.plugins.jobs.constants import JobStatus

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
                    ('encoding', str),
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
    @filtermodel(model='job', plugin='jobs')
    def createTiles(self, item, params):
        largeImageFileId = params.get('fileId')
        if not largeImageFileId:
            raise RestException('Missing "fileId" parameter.')

        if 'largeImage' in item:
            # TODO: automatically delete the existing large file
            raise RestException('Item already has a largeFile set.')

        job = None

        if item.get('expectedLargeImage'):
            del item['expectedLargeImage']
        if largeImageFileId == 'test':
            item['largeImage'] = 'test'
        else:
            largeImageFile = self.model('file').load(largeImageFileId,
                                                     force=True, exc=True)
            if largeImageFile['itemId'] != item['_id']:
                # TODO once we get rid of the "test" parameter, we should be
                # able to remove the itemId parameter altogether and just take
                # a file ID.
                raise RestException('"fileId" must be a file on the same item '
                                    'as "itemId".')
            try:
                item['largeImage'] = largeImageFile['_id']
                TiffGirderTileSource(item)
            except TileSourceException:
                del item['largeImage']
                job = self._createLargeImageJob(largeImageFile, item)
                item['expectedLargeImage'] = True
                item['largeImageOriginalId'] = largeImageFileId
                item['largeImageJobId'] = job['_id']

        self.model('item').save(item)

        return job

    def _createLargeImageJob(self, fileObj, item):
        user = self.getCurrentUser()
        token = self.getCurrentToken()

        path = os.path.join(os.path.dirname(__file__), 'create_tiff.py')
        with open(path, 'r') as f:
            script = f.read()

        title = 'TIFF conversion: %s' % fileObj['name']
        Job = self.model('job', 'jobs')
        job = Job.createJob(
            title=title, type='large_image_tiff', handler='worker_handler',
            user=user)
        jobToken = Job.createJobToken(job)

        task = {
            'mode': 'python',
            'script': script,
            'name': title,
            'inputs': [{
                'id': 'in_path',
                'target': 'filepath',
                'type': 'string',
                'format': 'text'
            }, {
                'id': 'out_filename',
                'type': 'string',
                'format': 'text'
            }, {
                'id': 'tile_size',
                'type': 'number',
                'format': 'number'
            }, {
                'id': 'quality',
                'type': 'number',
                'format': 'number'
            }],
            'outputs': [{
                'id': 'out_path',
                'target': 'filepath',
                'type': 'string',
                'format': 'text'
            }]
        }

        inputs = {
            'in_path': workerUtils.girderInputSpec(
                item, resourceType='item', token=token),
            'quality': {
                'mode': 'inline',
                'type': 'number',
                'format': 'number',
                'data': 90
            },
            'tile_size': {
                'mode': 'inline',
                'type': 'number',
                'format': 'number',
                'data': 256
            },
            'out_filename': {
                'mode': 'inline',
                'type': 'string',
                'format': 'text',
                'data': os.path.splitext(fileObj['name'])[0] + '.tiff'
            }
        }

        outputs = {
            'out_path': workerUtils.girderOutputSpec(
                parent=item, token=token, parentType='item')
        }

        # TODO: Give the job an owner
        job['kwargs'] = {
            'task': task,
            'inputs': inputs,
            'outputs': outputs,
            'jobInfo': workerUtils.jobInfoSpec(job, jobToken),
            'auto_convert': False,
            'validate': False
        }

        job = Job.save(job)
        Job.scheduleJob(job)

        return job

    @describeRoute(
        Description('Remove a large image from this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
    )
    @access.user
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def deleteTiles(self, item, params):
        deleted = False
        if 'largeImage' in item or 'largeImageJobId' in item:
            job = None
            if 'largeImageJobId' in item:
                Job = self.model('job', 'jobs')
                try:
                    job = Job.load(item['largeImageJobId'], force=True,
                                   exc=True)
                except ValidationException:
                    # The job has been deleted, but we still need to clean up
                    # the rest of the tile information
                    pass
            if (item.get('expectedLargeImage') and job and
                    job.get('status') in (
                    JobStatus.QUEUED, JobStatus.RUNNING)):
                # cannot cleanly remove the large image, since a conversion
                # job is currently in progress
                # TODO: cancel the job
                # TODO: return a failure error code
                return {
                    'deleted': False
                }

            # If this file was created by the worker job, delete it
            if 'largeImageJobId' in item:
                if job:
                    # TODO: does this eliminate all traces of the job?
                    # TODO: do we want to remove the original job?
                    Job.remove(job)
                del item['largeImageJobId']

            if 'largeImageOriginalId' in item:
                # The large image file should not be the original file
                assert item['largeImageOriginalId'] != item.get('largeImage')

                if 'largeImage' in item:
                    self.model('file').remove(self.model('file').load(
                        id=item['largeImage'], force=True))
                del item['largeImageOriginalId']

            if 'largeImage' in item:
                del item['largeImage']

            item['expectedLargeImage'] = True

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
        if x < 0 or y < 0 or z < 0:
            raise RestException('x, y, and z must be positive integers',
                                code=400)

        tileSource = self._loadTileSource(itemId, params)
        try:
            tileData = tileSource.getTile(x, y, z)
        except TileSourceException as e:
            raise RestException(e.message, code=404)

        cherrypy.response.headers['Content-Type'] = tileSource.getTileMimeType()
        return lambda: tileData
