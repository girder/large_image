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

import concurrent.futures
import datetime
import json
import psutil
import sys
import time

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource
from girder.exceptions import RestException
from girder.models.setting import Setting
from girder.models.file import File
from girder.models.item import Item
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from large_image.exceptions import TileGeneralException
from large_image import cache_util

from .. import constants
from .. import girder_tilesource
from ..models.image_item import ImageItem


def createThumbnailsJobTask(item, spec):
    """
    For an individual item, check or create all of the appropriate thumbnails.

    :param item: the image item.
    :param spec: a list of thumbnail specifications.
    :returns: a dictionary with the total status of the thumbnail job.
    """
    status = {'checked': 0, 'created': 0, 'failed': 0}
    for entry in spec:
        try:
            if entry.get('imageKey'):
                result = ImageItem().getAssociatedImage(item, checkAndCreate=True, **entry)
            else:
                result = ImageItem().getThumbnail(item, checkAndCreate=True, **entry)
            status['checked' if result is True else 'created'] += 1
        except TileGeneralException as exc:
            status['failed'] += 1
            status['lastFailed'] = str(item['_id'])
            logger.info('Failed to get thumbnail for item %s: %r' % (item['_id'], exc))
        except AttributeError:
            raise
        except Exception:
            status['failed'] += 1
            status['lastFailed'] = str(item['_id'])
            logger.exception(
                'Unexpected exception when trying to create a thumbnail for item %s' %
                item['_id'])
    return status


def createThumbnailsJobLog(job, info, prefix='', status=None):
    """
    Log information aboyt the create thumbnails job.

    :param job: the job object.
    :param info: a dictionary with the number of thumbnails checked, created,
        and failed.
    :param prefix: a string to place in front of the log message.
    :param status: if not None, a new status for the job.
    """
    msg = prefix + 'Checked %d, created %d thumbnail files' % (
        info['checked'], info['created'])
    if prefix == '' and info.get('items', 0) * info.get('specs', 0):
        done = info['checked'] + info['created'] + info['failed']
        if done < info['items'] * info['specs']:
            msg += ' (estimated %4.2f%% done)' % (
                100.0 * done / (info['items'] * info['specs']))
    msg += '\n'
    if info['failed']:
        msg += 'Failed on %d thumbnail file%s (last failure on item %s)\n' % (
            info['failed'],
            's' if info['failed'] != 1 else '', info['lastFailed'])
    job = Job().updateJob(job, log=msg, status=status)
    return job, msg


def cursorNextOrNone(cursor):
    """
    Given a Mongo cursor, return the next value if there is one.  If not,
    return None.

    :param cursor: a cursor to get a value from.
    :returns: the next value or None.
    """
    try:
        return cursor.next()  # noqa - B305
    except StopIteration:
        return None


def createThumbnailsJob(job):
    """
    Create thumbnails for all of the large image items.

    The job object contains::

      - spec: an array, each entry of which is the parameter dictionary
        for the model getThumbnail function.
      - logInterval: the time in seconds between log messages.  This
        also controls the granularity of cancelling the job.
      - concurrent: the number of threads to use.  0 for the number of
        cpus.

    :param job: the job object including kwargs.
    """
    job = Job().updateJob(
        job, log='Started creating large image thumbnails\n',
        status=JobStatus.RUNNING)
    concurrency = int(job['kwargs'].get('concurrent', 0))
    concurrency = psutil.cpu_count(logical=True) if concurrency < 1 else concurrency
    status = {
        'checked': 0,
        'created': 0,
        'failed': 0,
    }

    spec = job['kwargs']['spec']
    logInterval = float(job['kwargs'].get('logInterval', 10))
    job = Job().updateJob(job, log='Creating thumbnails (%d concurrent)\n' % concurrency)
    nextLogTime = time.time() + logInterval
    tasks = []
    # This could be switched from ThreadPoolExecutor to ProcessPoolExecutor
    # without any other changes.  Doing so would probably improve parallel
    # performance, but may not work reliably under Python 2.x.
    pool = concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)
    try:
        # Get a cursor with the list of images
        items = Item().find({'largeImage.fileId': {'$exists': True}})
        if hasattr(items, 'count'):
            status['items'] = items.count()
        status['specs'] = len(spec)
        nextitem = cursorNextOrNone(items)
        while len(tasks) or nextitem is not None:
            # Create more tasks than we strictly need so if one finishes before
            # we check another will be ready.  This is balanced with not
            # creating too many to avoid excessive memory use.  As such, we
            # can't do a simple iteration over the database cursor, as it will
            # be exhausted before we are done.
            while len(tasks) < concurrency * 4 and nextitem is not None:
                tasks.append(pool.submit(createThumbnailsJobTask, nextitem, spec))
                nextitem = cursorNextOrNone(items)
            # Wait a short time or until the oldest task is complete
            try:
                tasks[0].result(0.1)
            except concurrent.futures.TimeoutError:
                pass
            # Remove completed tasks from our list, adding their results to the
            # status.
            for pos in range(len(tasks) - 1, -1, -1):
                if tasks[pos].done():
                    r = tasks[pos].result()
                    status['created'] += r['created']
                    status['checked'] += r['checked']
                    status['failed'] += r['failed']
                    status['lastFailed'] = r.get('lastFailed', status.get('lastFailed'))
                    tasks[pos:pos + 1] = []
            # Periodically, log the state of the job and check if it was
            # deleted or canceled.
            if time.time() > nextLogTime:
                job, msg = createThumbnailsJobLog(job, status)
                # Check if the job was deleted or canceled; if so, quit
                job = Job().load(id=job['_id'], force=True)
                if not job or job['status'] in (JobStatus.CANCELED, JobStatus.ERROR):
                    cause = {
                        None: 'deleted',
                        JobStatus.CANCELED: 'canceled',
                        JobStatus.ERROR: 'stopped due to error',
                    }[None if not job else job.get('status')]
                    msg = 'Large image thumbnails job %s' % cause
                    logger.info(msg)
                    # Cancel any outstanding tasks.  If they haven't started,
                    # they are discarded.  Those that have started will still
                    # run, though.
                    for task in tasks:
                        task.cancel()
                    return
                nextLogTime = time.time() + logInterval
    except Exception:
        logger.exception('Error with large image create thumbnails job')
        Job().updateJob(
            job, log='Error creating large image thumbnails\n',
            status=JobStatus.ERROR)
        return
    finally:
        # Clean up the task pool asynchronously
        pool.shutdown(False)
    job, msg = createThumbnailsJobLog(job, status, 'Finished: ', JobStatus.SUCCESS)
    logger.info(msg)


class LargeImageResource(Resource):

    def __init__(self):
        super().__init__()

        self.resourceName = 'large_image'
        self.route('GET', ('cache', ), self.cacheInfo)
        self.route('PUT', ('cache', 'clear'), self.cacheClear)
        self.route('GET', ('settings',), self.getPublicSettings)
        self.route('GET', ('sources',), self.listSources)
        self.route('GET', ('thumbnails',), self.countThumbnails)
        self.route('PUT', ('thumbnails',), self.createThumbnails)
        self.route('DELETE', ('thumbnails',), self.deleteThumbnails)
        self.route('GET', ('associated_images',), self.countAssociatedImages)
        self.route('DELETE', ('associated_images',), self.deleteAssociatedImages)
        self.route('GET', ('histograms',), self.countHistograms)
        self.route('DELETE', ('histograms',), self.deleteHistograms)
        self.route('DELETE', ('tiles', 'incomplete'), self.deleteIncompleteTiles)

    @describeRoute(
        Description('Clear tile source caches to release resources and file handles.')
    )
    @access.admin
    def cacheClear(self, params):
        before = cache_util.cachesInfo()
        cache_util.cachesClear()
        after = cache_util.cachesInfo()
        return {'cacheCleared': datetime.datetime.utcnow(), 'before': before, 'after': after}

    @describeRoute(
        Description('Get information on caches.')
    )
    @access.admin
    def cacheInfo(self, params):
        return cache_util.cachesInfo()

    @describeRoute(
        Description('Get public settings for large image display.')
    )
    @access.public
    def getPublicSettings(self, params):
        keys = [getattr(constants.PluginSettings, key)
                for key in dir(constants.PluginSettings)
                if key.startswith('LARGE_IMAGE_')]
        return {k: Setting().get(k) for k in keys}

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
        return self._countCachedImages(params.get('spec'))

    @describeRoute(
        Description('Count the number of cached associated image files for '
                    'large_image items.')
    )
    @access.admin
    def countAssociatedImages(self, params):
        return self._countCachedImages(None, associatedImages=True)

    def _countCachedImages(self, spec, associatedImages=False):
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
            elif associatedImages:
                query['thumbnailKey'] = {'$regex': '"imageKey":'}
            count += File().find(query).count()
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
        .param('concurrent', 'The number of concurrent threads to use when '
               'making thumbnails.  0 or unspecified to base this on the '
               'number of reported cpus.', required=False, dataType='int')
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
        maxThumbnailFiles = int(Setting().get(
            constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES))
        if maxThumbnailFiles <= 0:
            raise RestException('Thumbnail files are not enabled.')
        jobKwargs = {'spec': spec}
        if params.get('logInterval') is not None:
            jobKwargs['logInterval'] = float(params['logInterval'])
        if params.get('concurrent') is not None:
            jobKwargs['concurrent'] = float(params['concurrent'])
        job = Job().createLocalJob(
            module='girder_large_image.rest.large_image_resource',
            function='createThumbnailsJob',
            kwargs=jobKwargs,
            title='Create large image thumbnail files.',
            type='large_image_create_thumbnails',
            user=self.getCurrentUser(),
            public=True,
            asynchronous=True,
        )
        Job().scheduleJob(job)
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
        return self._deleteCachedImages(params.get('spec'))

    @describeRoute(
        Description('Delete cached associated image files from large_image items.')
    )
    @access.admin
    def deleteAssociatedImages(self, params):
        return self._deleteCachedImages(None, associatedImages=True)

    def _deleteCachedImages(self, spec, associatedImages=False):
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
            elif associatedImages:
                query['thumbnailKey'] = {'$regex': '"imageKey":'}
            for file in File().find(query):
                File().remove(file)
                removed += 1
        return removed

    @describeRoute(
        Description('Remove large images from items where the large image job '
                    'incomplete.')
        .notes('This is used to clean up all large image conversion jobs that '
               'have failed to complete.  If a job is in progress, it will be '
               'cancelled.  The return value is the number of items that were '
               'adjusted.')
    )
    @access.admin
    def deleteIncompleteTiles(self, params):
        result = {'removed': 0}
        while True:
            item = Item().findOne({'largeImage.expected': True})
            if not item:
                break
            job = Job().load(item['largeImage']['jobId'], force=True)
            if job and job.get('status') in (
                    JobStatus.QUEUED, JobStatus.RUNNING):
                job = Job().cancelJob(job)
            if job and job.get('status') in (
                    JobStatus.QUEUED, JobStatus.RUNNING):
                result['message'] = ('The job for item %s could not be '
                                     'canceled' % (str(item['_id'])))
                break
            ImageItem().delete(item)
            result['removed'] += 1
        return result

    @describeRoute(
        Description('List all Girder tile sources with associated extensions, '
                    'mime types, and versions.  Lower values indicate a '
                    'higher priority for an extension of mime type with that '
                    'source.')
    )
    @access.public
    def listSources(self, params):
        results = {}
        for key, source in girder_tilesource.AvailableGirderTileSources.items():
            results[key] = {
                'extensions': {
                    k or 'default': v for k, v in source.extensions.items()},
                'mimeTypes': {
                    k or 'default': v for k, v in source.mimeTypes.items()},
            }
            for cls in source.__mro__:
                try:
                    if sys.modules[cls.__module__].__version__:
                        results[key]['version'] = sys.modules[cls.__module__].__version__
                        break
                except Exception:
                    pass
        return results

    @describeRoute(
        Description('Count the number of cached histograms for large_image items.')
    )
    @access.admin
    def countHistograms(self, params):
        query = {
            'isLargeImageData': True,
            'attachedToType': 'item',
            'thumbnailKey': {'$regex': '"imageKey":"histogram"'},
        }
        count = File().find(query).count()
        return count

    @describeRoute(
        Description('Delete cached histograms from large_image items.')
    )
    @access.admin
    def deleteHistograms(self, params):
        query = {
            'isLargeImageData': True,
            'attachedToType': 'item',
            'thumbnailKey': {'$regex': '"imageKey":"histogram"'},
        }
        removed = 0
        for file in File().find(query):
            File().remove(file)
            removed += 1
        return removed
