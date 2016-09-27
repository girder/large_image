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
    jobModel.updateJob(
        job, log='Started creating large image thumbnails\n',
        status=JobStatus.RUNNING)
    checkedOrCreated = 0
    try:
        spec = job['kwargs']['spec']
        itemModel = ModelImporter.model('item')
        imageItemModel = ModelImporter.model('image_item', 'large_image')
        for entry in spec:
            jobModel.updateJob(
                job, log='Creating thumbnails for %r\n' % entry)
            lastLogTime = time.time()
            items = itemModel.find({'largeImage.fileId': {'$exists': True}})
            for item in items:
                imageItemModel.getThumbnail(item, **entry)
                checkedOrCreated += 1
                if time.time() - lastLogTime > 15:
                    jobModel.updateJob(
                        job, log='Checked or created %d thumbnail file%s\n' % (
                            checkedOrCreated,
                            's' if checkedOrCreated != 1 else ''))
                    lastLogTime = time.time()
    except Exception:
        logger.exception('Error with large image create thumbnails job')
        jobModel.updateJob(
            job, log='Error creating large image thumbnails\n',
            status=JobStatus.ERROR)
        return
    msg = 'Finished creating large image thumbnails (%d checked or created)' % (
        checkedOrCreated)
    logger.info(msg)
    jobModel.updateJob(job, log=msg + '\n', status=JobStatus.SUCCESS)


class LargeImageResource(Resource):

    def __init__(self):
        super(LargeImageResource, self).__init__()

        self.resourceName = 'large_image'
        self.route('PUT', ('thumbnails',), self.createThumbnails)
        self.route('DELETE', ('thumbnails',), self.deleteThumbnails)

    @describeRoute(
        Description('Create cached thumbnail files from large_image items.')
        .notes('This creates a local job that processes all large_image items.')
        .param('spec', 'A JSON list of thumbnail specifications to create.  '
               'The specifications typically include width, height, encoding, '
               'and encoding options.')
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
        job = jobModel.createLocalJob(
            module='girder.plugins.large_image.rest.large_image',
            function='createThumbnailsJob',
            kwargs={'spec': spec},
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
