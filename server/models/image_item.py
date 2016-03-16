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

import collections
import os

from girder.api.rest import RestException
from girder.models.model_base import ValidationException
from girder.models.item import Item
from girder.plugins.worker import utils as workerUtils
from girder.plugins.jobs.constants import JobStatus

from ..tilesource import TestTileSource, TiffGirderTileSource, \
    SVSGirderTileSource, TileSourceException, TileSourceAssetstoreException


class ImageItem(Item):
    # We try these sources in this order.  The first entry is the fallback for
    # items that antedate there being multiple options.
    AvailableSources = collections.OrderedDict([
        ('tiff', TiffGirderTileSource),
        ('svs', SVSGirderTileSource),
    ])

    def initialize(self):
        super(ImageItem, self).initialize()

    def createImageItem(self, item, fileObj, user=None, token=None):
        if 'largeImage' in item:
            # TODO: automatically delete the existing large file
            # TODO: this should raise a GirderException, but still return 400
            raise RestException('Item already has a largeImage set.')
        if fileObj['itemId'] != item['_id']:
            raise RestException('The provided file must be in the provided '
                                'item.')

        if item.get('expectedLargeImage'):
            del item['expectedLargeImage']
        if item.get('largeImageSourceName'):
            del item['largeImageSourceName']

        item['largeImage'] = fileObj['_id']
        job = None
        for sourceName in self.AvailableSources:
            try:
                self.AvailableSources[sourceName](item)
                item['largeImageSourceName'] = sourceName
                break
            except TileSourceAssetstoreException:
                raise
            except TileSourceException:
                continue  # We want to try the next source
        else:
            # No source was successful
            del item['largeImage']
            job = self._createLargeImageJob(item, fileObj, user, token)
            item['expectedLargeImage'] = True
            item['largeImageOriginalId'] = fileObj['_id']
            item['largeImageJobId'] = job['_id']

        self.save(item)
        return job

    def _createLargeImageJob(self, item, fileObj, user, token):
        path = os.path.join(os.path.dirname(__file__), '..', 'create_tiff.py')
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

    @classmethod
    def _loadTileSource(cls, item, **kwargs):
        try:
            if item == 'test':
                tileSource = TestTileSource(**kwargs)
            else:
                sourceName = item.get(
                    'largeImageSourceName',
                    next(iter(cls.AvailableSources.items()))[0])
                tileSource = cls.AvailableSources[sourceName](item, **kwargs)
            return tileSource
        except TileSourceException as e:
            # TODO: sometimes this could be 400
            raise RestException(e.message, code=500)

    def getMetadata(self, item, **kwargs):
        tileSource = self._loadTileSource(item, **kwargs)
        return tileSource.getMetadata()

    def getTile(self, item, x, y, z, **kwargs):
        tileSource = self._loadTileSource(item, **kwargs)
        try:
            tileData = tileSource.getTile(x, y, z)
        except TileSourceException as e:
            raise RestException(e.message, code=404)
        tileMimeType = tileSource.getTileMimeType()
        return tileData, tileMimeType

    def delete(self, item):
        Job = self.model('job', 'jobs')
        deleted = False
        if 'largeImage' in item or 'largeImageJobId' in item:
            job = None
            if 'largeImageJobId' in item:
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
                return False

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

            if item.get('largeImageSourceName'):
                del item['largeImageSourceName']
            if 'largeImage' in item:
                del item['largeImage']

            item['expectedLargeImage'] = True

            self.save(item)
            deleted = True

        return deleted
