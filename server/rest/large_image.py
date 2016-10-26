#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
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
##############################################################################

import json
import time

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource, RestException
from girder.plugins.jobs.constants import JobStatus
from girder.utility.model_importer import ModelImporter

from .. import constants


def createThumbnailsJob(job):
    """
    Create thumbnails for all of the large image items.

    :param spec: an array, each entry of which is the parameter dictionary for
        the model getThumbnail function.
    """
    jobModel = ModelImporter.model('job', 'jobs')
    job = jobModel.updateJob(
        job, log='Started creating large image thumbnails\n',
        status=JobStatus.RUNNING)
    checkedOrCreated = 0
    try:
        spec = job['kwargs']['spec']
        logInterval = float(job['kwargs'].get('logInterval', 10))
        itemModel = ModelImporter.model('item')
        imageItemModel = ModelImporter.model('image_item', 'large_image')
        for entry in spec:
            job = jobModel.updateJob(
                job, log='Creating thumbnails for %r\n' % entry)
            lastLogTime = time.time()
            items = itemModel.find({'largeImage.fileId': {'$exists': True}})
            for item in items:
                imageItemModel.getThumbnail(item, **entry)
                checkedOrCreated += 1
                # Periodically, log the state of the job and check if it was
                # deleted or canceled.
                if time.time() - lastLogTime > logInterval:
                    job = jobModel.updateJob(
                        job, log='Checked or created %d thumbnail file%s\n' % (
                            checkedOrCreated,
                            's' if checkedOrCreated != 1 else ''))
                    lastLogTime = time.time()
                    # Check if the job was deleted or canceled; if so, quit
                    job = jobModel.load(id=job['_id'], force=True)
                    if not job or job['status'] == JobStatus.CANCELED:
                        logger.info('Large image thumbnails job %s' % (
                            'deleted' if not job else 'canceled'))
                        return
    except Exception:
        logger.exception('Error with large image create thumbnails job')
        job = jobModel.updateJob(
            job, log='Error creating large image thumbnails\n',
            status=JobStatus.ERROR)
        return
    msg = 'Finished creating large image thumbnails (%d checked or created)' % (
        checkedOrCreated)
    logger.info(msg)
    job = jobModel.updateJob(job, log=msg + '\n', status=JobStatus.SUCCESS)


class LargeImageResource(Resource):

    def __init__(self):
        super(LargeImageResource, self).__init__()

        self.resourceName = 'large_image'
        self.route('GET', ('settings',), self.getPublicSettings)
        self.route('GET', ('thumbnails',), self.countThumbnails)
        self.route('PUT', ('thumbnails',), self.createThumbnails)
        self.route('DELETE', ('thumbnails',), self.deleteThumbnails)

    @describeRoute(
        Description('Get public settings for large image display.')
    )
    @access.public
    def getPublicSettings(self, params):
        keys = [
            constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
            constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
            constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER,
            constants.PluginSettings.LARGE_IMAGE_AUTO_SET,
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES,
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE,
        ]
        return {k: self.model('setting').get(k) for k in keys}

    @describeRoute(
        Description('Count the number of cached thumbnail files for '
                    'large_image items.')
        .param('spec', 'A JSON list of thumbnail specifications to count.  '
               'If empty, all cached thumbnails are counted.  The '
               'specifications typically include width, height, encoding, and '
               'encoding options.', required=False)
    )
    @access.admin
    def countThumbnails(self, params):
        spec = params.get('spec')
        if spec is not None:
            try:
                spec = json.loads(spec)
                if not isinstance(spec, list):
                    raise ValueError()
            except ValueError:
                raise RestException('The spec parameter must be a JSON list.')
            spec = [json.dumps(entry, sort_keys=True, separators=(',', ':'))
                    for entry in spec]
        else:
            spec = [None]
        count = 0
        for entry in spec:
            query = {'isLargeImageThumbnail': True, 'attachedToType': 'item'}
            if entry is not None:
                query['thumbnailKey'] = entry
            count += self.model('file').find(query).count()
        return count

    @describeRoute(
        Description('Create cached thumbnail files from large_image items.')
        .notes('This creates a local job that processes all large_image items.')
        .param('spec', 'A JSON list of thumbnail specifications to create.  '
               'The specifications typically include width, height, encoding, '
               'and encoding options.')
        .param('logInterval', 'The number of seconds between log messages.  '
               'This also determines how often the creation job is checked if '
               'it has been canceled or deleted.  A value of 0 will log after '
               'each thumbnail is checked or created.', required=False,
               dataType='float')
    )
    @access.admin
    def createThumbnails(self, params):
        self.requireParams(['spec'], params)
        try:
            spec = json.loads(params['spec'])
            if not isinstance(spec, list):
                raise ValueError()
        except ValueError:
            raise RestException('The spec parameter must be a JSON list.')
        maxThumbnailFiles = int(self.model('setting').get(
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES))
        if maxThumbnailFiles <= 0:
            raise RestException('Thumbnail files are not enabled.')
        jobModel = self.model('job', 'jobs')
        jobKwargs = {'spec': spec}
        if params.get('logInterval') is not None:
            jobKwargs['logInterval'] = float(params['logInterval'])
        job = jobModel.createLocalJob(
            module='girder.plugins.large_image.rest.large_image',
            function='createThumbnailsJob',
            kwargs=jobKwargs,
            title='Create large image thumbnail files.',
            type='large_image_create_thumbnails',
            user=self.getCurrentUser(),
            public=True,
            async=True,
        )
        jobModel.scheduleJob(job)
        return job

    @describeRoute(
        Description('Delete cached thumbnail files from large_image items.')
        .param('spec', 'A JSON list of thumbnail specifications to delete.  '
               'If empty, all cached thumbnails are deleted.  The '
               'specifications typically include width, height, encoding, and '
               'encoding options.', required=False)
    )
    @access.admin
    def deleteThumbnails(self, params):
        spec = params.get('spec')
        if spec is not None:
            try:
                spec = json.loads(spec)
                if not isinstance(spec, list):
                    raise ValueError()
            except ValueError:
                raise RestException('The spec parameter must be a JSON list.')
            spec = [json.dumps(entry, sort_keys=True, separators=(',', ':'))
                    for entry in spec]
        else:
            spec = [None]
        removed = 0
        for entry in spec:
            query = {'isLargeImageThumbnail': True, 'attachedToType': 'item'}
            if entry is not None:
                query['thumbnailKey'] = entry
            for file in self.model('file').find(query):
                self.model('file').remove(file)
                removed += 1
        return removed
