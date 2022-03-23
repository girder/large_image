#############################################################################
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
#############################################################################

import io
import json
import pickle

import pymongo
from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from girder import logger
from girder.constants import SortDir
from girder.exceptions import FilePathException, GirderException, ValidationException
from girder.models.assetstore import Assetstore
from girder.models.file import File
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.upload import Upload
from large_image.cache_util import getTileCache, strhash
from large_image.constants import TileOutputMimeTypes
from large_image.exceptions import TileGeneralError, TileSourceError

from .. import constants, girder_tilesource


class ImageItem(Item):
    # We try these sources in this order.  The first entry is the fallback for
    # items that antedate there being multiple options.
    def initialize(self):
        super().initialize()
        self.ensureIndices(['largeImage.fileId'])
        File().ensureIndices([
            ([
                ('isLargeImageThumbnail', pymongo.ASCENDING),
                ('attachedToType', pymongo.ASCENDING),
                ('attachedToId', pymongo.ASCENDING),
            ], {}),
            ([
                ('isLargeImageData', pymongo.ASCENDING),
                ('attachedToType', pymongo.ASCENDING),
                ('attachedToId', pymongo.ASCENDING),
            ], {}),
        ])

    def createImageItem(self, item, fileObj, user=None, token=None,
                        createJob=True, notify=False, **kwargs):
        # Using setdefault ensures that 'largeImage' is in the item
        if 'fileId' in item.setdefault('largeImage', {}):
            raise TileGeneralError('Item already has largeImage set.')
        if fileObj['itemId'] != item['_id']:
            raise TileGeneralError(
                'The provided file must be in the provided item.')
        if (item['largeImage'].get('expected') is True and
                'jobId' in item['largeImage']):
            raise TileGeneralError(
                'Item is scheduled to generate a largeImage.')

        item['largeImage'].pop('expected', None)
        item['largeImage'].pop('sourceName', None)

        item['largeImage']['fileId'] = fileObj['_id']
        job = None
        sourceName = girder_tilesource.getGirderTileSourceName(item, fileObj)
        if sourceName:
            item['largeImage']['sourceName'] = sourceName
        if not sourceName or createJob == 'always':
            if not createJob:
                raise TileGeneralError(
                    'A job must be used to generate a largeImage.')
            # No source was successful
            del item['largeImage']['fileId']
            job = self._createLargeImageJob(item, fileObj, user, token, **kwargs)
            item['largeImage']['expected'] = True
            item['largeImage']['notify'] = notify
            item['largeImage']['originalId'] = fileObj['_id']
            item['largeImage']['jobId'] = job['_id']
        self.save(item)
        return job

    def _createLargeImageJob(self, item, fileObj, user, token, **kwargs):
        import large_image_tasks.tasks
        from girder_worker_utils.transforms.common import TemporaryDirectory
        from girder_worker_utils.transforms.contrib.girder_io import GirderFileIdAllowDirect
        from girder_worker_utils.transforms.girder_io import GirderUploadToItem

        try:
            localPath = File().getLocalFilePath(fileObj)
        except (FilePathException, AttributeError):
            localPath = None
        job = large_image_tasks.tasks.create_tiff.apply_async(kwargs=dict(
            girder_job_title='TIFF Conversion: %s' % fileObj['name'],
            girder_job_other_fields={'meta': {
                'creator': 'large_image',
                'itemId': str(item['_id']),
                'task': 'createImageItem',
            }},
            inputFile=GirderFileIdAllowDirect(str(fileObj['_id']), fileObj['name'], localPath),
            inputName=fileObj['name'],
            outputDir=TemporaryDirectory(),
            girder_result_hooks=[
                GirderUploadToItem(str(item['_id']), False),
            ],
            **kwargs,
        ), countdown=int(kwargs['countdown']) if kwargs.get('countdown') else None)
        return job.job

    def convertImage(self, item, fileObj, user=None, token=None, localJob=True, **kwargs):
        if fileObj['itemId'] != item['_id']:
            raise TileGeneralError(
                'The provided file must be in the provided item.')
        if not localJob:
            return self._convertImageViaWorker(item, fileObj, user, token, **kwargs)
        # local job
        job = Job().createLocalJob(
            module='large_image_tasks.tasks',
            function='convert_image_job',
            kwargs={
                'itemId': str(item['_id']),
                'fileId': str(fileObj['_id']),
                'userId': str(user['_id']) if user else None,
                **kwargs,
            },
            title='Convert a file to a large image file.',
            type='large_image_convert_image',
            user=user,
            public=True,
            asynchronous=True,
        )
        Job().scheduleJob(job)
        return job

    def _convertImageViaWorker(
            self, item, fileObj, user=None, token=None, folderId=None,
            name=None, **kwargs):
        import large_image_tasks.tasks
        from girder_worker_utils.transforms.common import TemporaryDirectory
        from girder_worker_utils.transforms.contrib.girder_io import GirderFileIdAllowDirect
        from girder_worker_utils.transforms.girder_io import GirderUploadToFolder

        try:
            localPath = File().getLocalFilePath(fileObj)
        except (FilePathException, AttributeError):
            localPath = None
        job = large_image_tasks.tasks.create_tiff.apply_async(kwargs=dict(
            girder_job_title='TIFF Conversion: %s' % fileObj['name'],
            girder_job_other_fields={'meta': {
                'creator': 'large_image',
                'itemId': str(item['_id']),
                'task': 'convertImage',
            }},
            inputFile=GirderFileIdAllowDirect(str(fileObj['_id']), fileObj['name'], localPath),
            inputName=fileObj['name'],
            outputDir=TemporaryDirectory(),
            girder_result_hooks=[
                GirderUploadToFolder(
                    str(folderId or item['folderId']),
                    upload_kwargs=dict(filename=name),
                ),
            ],
            **kwargs,
        ), countdown=int(kwargs['countdown']) if kwargs.get('countdown') else None)
        return job.job

    @classmethod
    def _tileFromHash(cls, item, x, y, z, mayRedirect=False, **kwargs):
        tileCache, tileCacheLock = getTileCache()
        if tileCache is None:
            return None
        if 'largeImage' not in item:
            return None
        if item['largeImage'].get('expected'):
            return None
        sourceName = item['largeImage']['sourceName']
        try:
            sourceClass = girder_tilesource.AvailableGirderTileSources[sourceName]
        except TileSourceError:
            return None
        classHash = sourceClass.getLRUHash(item, **kwargs)
        tileHash = sourceClass.__name__ + ' ' + classHash + ' ' + strhash(
            classHash) + strhash(*(x, y, z), mayRedirect=mayRedirect, **kwargs)
        try:
            if tileCacheLock is None:
                tileData = tileCache[tileHash]
            else:
                # Checking this outside the lock is sufficient for the cache
                # miss condition and faster
                if tileHash not in tileCache:
                    return None
                with tileCacheLock:
                    tileData = tileCache[tileHash]
            tileMime = TileOutputMimeTypes.get(kwargs.get('encoding'), 'image/jpeg')
            return tileData, tileMime
        except (KeyError, ValueError):
            return None

    @classmethod
    def _loadTileSource(cls, item, **kwargs):
        if 'largeImage' not in item:
            raise TileSourceError('No large image file in this item.')
        if item['largeImage'].get('expected'):
            raise TileSourceError('The large image file for this item is '
                                  'still pending creation.')

        sourceName = item['largeImage']['sourceName']
        try:
            # First try to use the tilesource we recorded as the preferred one.
            # This is faster than trying to find the best source each time.
            tileSource = girder_tilesource.AvailableGirderTileSources[sourceName](item, **kwargs)
        except TileSourceError as exc:
            # We could try any source
            # tileSource = girder_tilesource.getGirderTileSource(item, **kwargs)
            # but, instead, log that the original source no longer works are
            # reraise the exception
            logger.warning('The original tile source for item %s is not working' % item['_id'])
            try:
                file = File().load(item['largeImage']['fileId'], force=True)
                localPath = File().getLocalFilePath(file)
                open(localPath, 'rb').read(1)
            except IOError:
                logger.warning(
                    'Is the original data reachable and readable (it fails via %r)?', localPath)
                raise IOError(localPath) from None
            except Exception:
                pass
            raise exc
        return tileSource

    def getMetadata(self, item, **kwargs):
        tileSource = self._loadTileSource(item, **kwargs)
        return tileSource.getMetadata()

    def getInternalMetadata(self, item, **kwargs):
        tileSource = self._loadTileSource(item, **kwargs)
        result = tileSource.getInternalMetadata() or {}
        result['tilesource'] = tileSource.name
        return result

    def getTile(self, item, x, y, z, mayRedirect=False, **kwargs):
        tileSource = self._loadTileSource(item, **kwargs)
        imageParams = {}
        if 'frame' in kwargs:
            imageParams['frame'] = int(kwargs['frame'])
        tileData = tileSource.getTile(x, y, z, mayRedirect=mayRedirect, **imageParams)
        tileMimeType = tileSource.getTileMimeType()
        return tileData, tileMimeType

    def delete(self, item, skipFileIds=None):
        deleted = False
        if 'largeImage' in item:
            job = None
            if 'jobId' in item['largeImage']:
                try:
                    job = Job().load(item['largeImage']['jobId'], force=True, exc=True)
                except ValidationException:
                    # The job has been deleted, but we still need to clean up
                    # the rest of the tile information
                    pass
            if (item['largeImage'].get('expected') and job and
                    job.get('status') in (
                    JobStatus.QUEUED, JobStatus.RUNNING)):
                # cannot cleanly remove the large image, since a conversion
                # job is currently in progress
                # TODO: cancel the job
                # TODO: return a failure error code
                return False

            # If this file was created by the worker job, delete it
            if 'jobId' in item['largeImage']:
                # To eliminate all traces of the job, add
                # if job:
                #     Job().remove(job)
                del item['largeImage']['jobId']

            if 'originalId' in item['largeImage']:
                # The large image file should not be the original file
                assert item['largeImage']['originalId'] != \
                    item['largeImage'].get('fileId')

                if ('fileId' in item['largeImage'] and (
                        not skipFileIds or
                        item['largeImage']['fileId'] not in skipFileIds)):
                    file = File().load(id=item['largeImage']['fileId'], force=True)
                    if file:
                        File().remove(file)
                del item['largeImage']['originalId']

            del item['largeImage']

            item = self.save(item)
            deleted = True
        self.removeThumbnailFiles(item)
        return deleted

    def getThumbnail(self, item, checkAndCreate=False, width=None, height=None, **kwargs):
        """
        Using a tile source, get a basic thumbnail.  Aspect ratio is
        preserved.  If neither width nor height is given, a default value is
        used.  If both are given, the thumbnail will be no larger than either
        size.

        :param item: the item with the tile source.
        :param checkAndCreate: if the thumbnail is already cached, just return
            True.  If it does not, create, cache, and return it.  If 'nosave',
            return values from the cache, but do not store new results in the
            cache.
        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, tiffCompression, fill.  This is also
            passed to the tile source.
        :returns: thumbData, thumbMime: the image data and the mime type OR
            a generator which will yield a file.
        """
        # check if a thumbnail file exists with a particular key
        keydict = dict(kwargs, width=width, height=height)
        return self._getAndCacheImageOrData(
            item, 'getThumbnail', checkAndCreate, keydict, width=width, height=height, **kwargs)

    def _getAndCacheImageOrData(
            self, item, imageFunc, checkAndCreate, keydict, pickleCache=False, **kwargs):
        """
        Get a file associated with an image that can be generated by a
        function.

        :param item: the idem to process.
        :param imageFunc: the function to call to generate a file.
        :param checkAndCreate: False to return the data, creating and caching
            it if needed.  True to return True if the data is already in cache,
            or to create the data, cache, and return it if not.  'nosave' to
            return data from the cache if present, or generate the data but do
            not return it if not in the cache.  'check' to just return True or
            False to report if it is in the cache.
        :param keydict: a dictionary of values to use for the cache key.
        :param pickleCache: if True, the results of the function are pickled to
            preserver them.  If Fales, the results can be saved as a file
            directly.
        :params **kwargs: passed to the tile source and to the imageFunc.  May
            contain contentDisposition to determine how results are returned.
        :returns:
        """
        if 'fill' in keydict and (keydict['fill']).lower() == 'none':
            del keydict['fill']
        keydict = {k: v for k, v in keydict.items() if v is not None and not k.startswith('_')}
        key = json.dumps(keydict, sort_keys=True, separators=(',', ':'))
        existing = File().findOne({
            'attachedToType': 'item',
            'attachedToId': item['_id'],
            'isLargeImageThumbnail' if not pickleCache else 'isLargeImageData': True,
            'thumbnailKey': key,
        })
        if existing:
            if checkAndCreate and checkAndCreate != 'nosave':
                return True
            if kwargs.get('contentDisposition') != 'attachment':
                contentDisposition = 'inline'
            else:
                contentDisposition = kwargs['contentDisposition']
            if pickleCache:
                data = File().open(existing).read()
                return pickle.loads(data), 'application/octet-stream'
            return File().download(existing, contentDisposition=contentDisposition)
        if checkAndCreate == 'check':
            return False
        tileSource = self._loadTileSource(item, **kwargs)
        result = getattr(tileSource, imageFunc)(**kwargs)
        if result is None:
            imageData, imageMime = b'', 'application/octet-stream'
        elif pickleCache:
            imageData, imageMime = result, 'application/octet-stream'
        else:
            imageData, imageMime = result
        saveFile = True
        if not pickleCache:
            # The logic on which files to save could be more sophisticated.
            maxThumbnailFiles = int(Setting().get(
                constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES))
            saveFile = maxThumbnailFiles > 0
            # Make sure we don't exceed the desired number of thumbnails
            self.removeThumbnailFiles(
                item, maxThumbnailFiles - 1, imageKey=keydict.get('imageKey') or 'none')
        if (saveFile and checkAndCreate != 'nosave' and (
                pickleCache or isinstance(imageData, bytes))):
            dataStored = imageData if not pickleCache else pickle.dumps(imageData, protocol=4)
            # Save the data as a file
            try:
                datafile = Upload().uploadFromFile(
                    io.BytesIO(dataStored), size=len(dataStored),
                    name='_largeImageThumbnail', parentType='item', parent=item,
                    user=None, mimeType=imageMime, attachParent=True)
                if not len(dataStored) and 'received' in datafile:
                    datafile = Upload().finalizeUpload(
                        datafile, Assetstore().load(datafile['assetstoreId']))
                datafile.update({
                    'isLargeImageThumbnail' if not pickleCache else 'isLargeImageData': True,
                    'thumbnailKey': key,
                })
                # Ideally, we would check that the file is still wanted before
                # we save it.  This is probably impossible without true
                # transactions in Mongo.
                File().save(datafile)
            except (GirderException, PermissionError):
                logger.warning('Could not cache data for large image')
        return imageData, imageMime

    def removeThumbnailFiles(self, item, keep=0, sort=None, imageKey=None, **kwargs):
        """
        Remove all large image thumbnails from an item.

        :param item: the item that owns the thumbnails.
        :param keep: keep this many entries.
        :param sort: the sort method used.  The first (keep) records in this
            sort order are kept.
        :param imageKey: None for the basic thumbnail, otherwise an associated
            imageKey.
        :param kwargs: additional parameters to determine which files to
            remove.
        :returns: a tuple of (the number of files before removal, the number of
            files removed).
        """
        keys = ['isLargeImageThumbnail']
        if not keep:
            keys.append('isLargeImageData')
        if not sort:
            sort = [('_id', SortDir.DESCENDING)]
        for key in keys:
            query = {
                'attachedToType': 'item',
                'attachedToId': item['_id'],
                key: True,
            }
            if imageKey and key == 'isLargeImageThumbnail':
                if imageKey == 'none':
                    query['thumbnailKey'] = {'not': {'$regex': '"imageKey":'}}
                else:
                    query['thumbnailKey'] = {'$regex': '"imageKey":"%s"' % imageKey}
            query.update(kwargs)
            present = 0
            removed = 0
            for file in File().find(query, sort=sort):
                present += 1
                if keep > 0:
                    keep -= 1
                    continue
                File().remove(file)
                removed += 1
        return (present, removed)

    def getRegion(self, item, **kwargs):
        """
        Using a tile source, get an arbitrary region of the image, optionally
        scaling the results.  Aspect ratio is preserved.

        :param item: the item with the tile source.
        :param kwargs: optional arguments.  Some options are left, top,
            right, bottom, regionWidth, regionHeight, units, width, height,
            encoding, jpegQuality, jpegSubsampling, and tiffCompression.  This
            is also passed to the tile source.
        :returns: regionData, regionMime: the image data and the mime type.
        """
        tileSource = self._loadTileSource(item, **kwargs)
        regionData, regionMime = tileSource.getRegion(**kwargs)
        return regionData, regionMime

    def tileFrames(self, item, checkAndCreate='nosave', **kwargs):
        """
        Given the parameters for getRegion, plus a list of frames and the
        number of frames across, make a larger image composed of a region from
        each listed frame composited together.

        :param item: the item with the tile source.
        :param checkAndCreate: if False, use the cache.  If True and the result
            is already cached, just return True.  If it does not, create,
            cache, and return it.  If 'nosave', return values from the cache,
            but do not store new results in the cache.
        :param kwargs: optional arguments.  Some options are left, top,
            right, bottom, regionWidth, regionHeight, units, width, height,
            encoding, jpegQuality, jpegSubsampling, and tiffCompression.  This
            is also passed to the tile source.  These also include frameList
            and framesAcross.
        :returns: regionData, regionMime: the image data and the mime type.
        """
        imageKey = 'tileFrames'
        return self._getAndCacheImageOrData(
            item, 'tileFrames', checkAndCreate,
            dict(kwargs, imageKey=imageKey), **kwargs)

    def getPixel(self, item, **kwargs):
        """
        Using a tile source, get a single pixel from the image.

        :param item: the item with the tile source.
        :param kwargs: optional arguments.  Some options are left, top.
        :returns: a dictionary of the color channel values, possibly with
            additional information
        """
        tileSource = self._loadTileSource(item, **kwargs)
        return tileSource.getPixel(**kwargs)

    def histogram(self, item, **kwargs):
        """
        Using a tile source, get a histogram of the image.

        :param item: the item with the tile source.
        :param kwargs: optional arguments.  See the tilesource histogram
            method.
        :returns: histogram object.
        """
        if kwargs.get('range') is not None:
            tileSource = self._loadTileSource(item, **kwargs)
            result = tileSource.histogram(**kwargs)
        else:
            imageKey = 'histogram'
            result = self._getAndCacheImageOrData(
                item, 'histogram', False, dict(kwargs, imageKey=imageKey),
                pickleCache=True, **kwargs)[0]
        return result

    def getBandInformation(self, item, statistics=True, **kwargs):
        """
        Using a tile source, get band information of the image.

        :param item: the item with the tile source.
        :param kwargs: optional arguments.  See the tilesource
            getBandInformation method.
        :returns: band information.
        """
        tileSource = self._loadTileSource(item, **kwargs)
        result = tileSource.getBandInformation(statistics=statistics, **kwargs)
        return result

    def tileSource(self, item, **kwargs):
        """
        Get a tile source for an item.

        :param item: the item with the tile source.
        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        return self._loadTileSource(item, **kwargs)

    def getAssociatedImagesList(self, item, **kwargs):
        """
        Return a list of associated images.

        :param item: the item with the tile source.
        :return: a list of keys of associated images.
        """
        tileSource = self._loadTileSource(item, **kwargs)
        return tileSource.getAssociatedImagesList()

    def getAssociatedImage(self, item, imageKey, checkAndCreate=False, *args, **kwargs):
        """
        Return an associated image.

        :param item: the item with the tile source.
        :param imageKey: the key of the associated image to retrieve.
        :param kwargs: optional arguments.  Some options are width, height,
            encoding, jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: imageData, imageMime: the image data and the mime type, or
            None if the associated image doesn't exist.
        """
        keydict = dict(kwargs, imageKey=imageKey)
        return self._getAndCacheImageOrData(
            item, 'getAssociatedImage', checkAndCreate, keydict, imageKey=imageKey, **kwargs)

    def _scheduleTileFrames(self, item, tileFramesList, user):
        """
        Schedule generating tile frames in a local job.

        :param item: the item.
        :param tileFramesList: a list of dictionary of parameters to pass to
            the tileFrames method.
        :param user: the user owning the job.
        """
        job = Job().createLocalJob(
            module='large_image_tasks.tasks',
            function='cache_tile_frames_job',
            kwargs={
                'itemId': str(item['_id']),
                'tileFramesList': tileFramesList,
            },
            title='Cache tileFrames',
            type='large_image_cache_tile_frames',
            user=user,
            public=True,
            asynchronous=True,
        )
        Job().scheduleJob(job)
        return job
