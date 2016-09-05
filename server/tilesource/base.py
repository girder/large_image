#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import abc
import math
from six import BytesIO

from ..cache_util import tileCache, tileLock, strhash, cached

try:
    import girder
    from girder import logger
    from girder.models.model_base import ValidationException
    from girder.utility import assetstore_utilities
    from girder.utility.model_importer import ModelImporter
    from ..models.base import TileGeneralException
    from girder.models.model_base import AccessType
except ImportError:
    import logging as logger

    girder = None

    class TileGeneralException(Exception):
        pass

# Not having PIL disables thumbnail creation, but isn't fatal
try:
    import PIL

    if int(PIL.PILLOW_VERSION.split('.')[0]) < 3:
        logger.warning('Error: Pillow v3.0 or later is required')
        PIL = None
except ImportError:
    logger.warning('Error: Could not import PIL')
    PIL = None


class TileSourceException(TileGeneralException):
    pass


class TileSourceAssetstoreException(TileSourceException):
    pass


class TileSource(object):
    outputMimeTypes = {
        'JPEG': 'image/jpeg',
        'PNG': 'image/png'
    }
    name = None

    cache = tileCache
    cache_lock = tileLock

    def __init__(self, *args, **kwargs):
        self.tileWidth = None
        self.tileHeight = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None

        self.getThumbnail = cached(
            self.cache, key=self.wrapKey, lock=self.cache_lock)(
                self.getThumbnail)
        self.getTile = cached(
            self.cache, key=self.wrapKey, lock=self.cache_lock)(self.getTile)

    def wrapKey(self, *args, **kwargs):
        return strhash(self.getState()) + strhash(*args, **kwargs)

    @abc.abstractmethod
    def getState(self):
        return None

    def _calculateWidthHeight(self, width, height, regionWidth, regionHeight):
        """
        Given a source width and height and a maximum destination width and/or
        height, calculate a destination width and height that preserves the
        aspect ratio of the source.

        :param width: the destination width.  None to only use height.
        :param height: the destination height.  None to only use width.
        :param regionWidth: the width of the source data.
        :param regionHeight: the height of the source data.
        :returns: the width and height that is no larger than that specified
                  and preserves aspect ratio.
        """
        if regionWidth == 0 or regionHeight == 0:
            return 0, 0
        # Constrain the maximum size if both width and height weren't
        # specified, in case the image is very short or very narrow.
        if height and not width:
            width = height * 16
        if width and not height:
            height = width * 16
        if width * regionHeight > height * regionWidth:
            width = max(1, int(regionWidth * height / regionHeight))
        else:
            height = max(1, int(regionHeight * width / regionWidth))
        return width, height

    def _encodeImage(self, image, encoding='JPEG', jpegQuality=95,
                     jpegSubsampling=0, **kwargs):
        """
        Convert a PIL image into the raw output bytes and a mime type.

        :param image: a PIL image.
        :param encoding: a valid PIL encoding (typically 'PNG' or 'JPEG').
                         Must also be in the outputMimeTypes map.
        :param jpegQuality: the quality to use when encoding a JPEG.
        :param jpegSubsampling: the subsampling level to use when encoding a
                                JPEG.
        """
        if encoding not in self.outputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        if image.width == 0 or image.height == 0:
            tileData = b''
        else:
            output = BytesIO()
            image.save(output, encoding, quality=jpegQuality,
                       subsampling=jpegSubsampling)
            tileData = output.getvalue()
        return tileData, self.outputMimeTypes[encoding]

    def _getRegionBounds(self, metadata, **kwargs):
        """
        Given a set of arguments that can include left, right, top, bottom,
        regionWidth, regionHeight, and units, generate actual pixel values for
        left, top, right, and bottom.

        :param metadata: the metadata associated with this source.
        :param **kwargs: optional parameters.  See above.
        :returns: left, top, right, bottom bounds in pixels.
        """
        if kwargs.get('units') not in (None, 'pixel', 'pixels', 'fraction'):
            raise ValueError('Invalid units "%s"' % kwargs['units'])
        # Copy kwargs so we don't alter an input dictionary
        kwargs = kwargs.copy()
        # Convert fraction units to pixels
        if kwargs.get('units') == 'fraction':
            for key in ('left', 'right', 'regionWidth'):
                if key in kwargs:
                    kwargs[key] = kwargs[key] * metadata['sizeX']
            for key in ('top', 'bottom', 'regionHeight'):
                if key in kwargs:
                    kwargs[key] = kwargs[key] * metadata['sizeY']
        # convert negative references to right or bottom offsets
        for key in ('left', 'right', 'top', 'bottom'):
            if key in kwargs and kwargs.get(key) < 0:
                kwargs[key] += metadata[
                    'sizeX' if key in ('left', 'right') else 'sizeY']
        # Calculate the region we need to fetch
        left = kwargs.get(
            'left',
            (kwargs.get('right') - kwargs.get('regionWidth'))
            if ('right' in kwargs and 'regionWidth' in kwargs) else 0)
        right = kwargs.get(
            'right',
            (left + kwargs.get('regionWidth'))
            if ('regionWidth' in kwargs) else metadata['sizeX'])
        top = kwargs.get(
            'top', kwargs.get('bottom') - kwargs.get('regionHeight')
            if 'bottom' in kwargs and 'regionHeight' in kwargs else 0)
        bottom = kwargs.get(
            'bottom', top + kwargs.get('regionHeight')
            if 'regionHeight' in kwargs else metadata['sizeY'])
        # Crop the bounds to integer pixels within the actual source data
        left = min(metadata['sizeX'], max(0, int(round(left))))
        right = min(metadata['sizeX'], max(left, int(round(right))))
        top = min(metadata['sizeY'], max(0, int(round(top))))
        bottom = min(metadata['sizeY'], max(top, int(round(bottom))))

        return left, top, right, bottom

    @classmethod
    def canRead(cls, *args, **kwargs):
        """
        Check if we can read the input.  This takes the same parameters as
        __init__.

        :returns: True if this class can read the input.  False if it cannot.
        """
        return False

    def getMetadata(self):
        return {
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
        }

    def getTile(self, x, y, z, pilImageAllowed=False, sparseFallback=False):
        raise NotImplementedError()

    def getTileMimeType(self):
        return 'image/jpeg'

    def getThumbnail(self, width=None, height=None, levelZero=False, **kwargs):
        """
        Get a basic thumbnail from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, a default value is
        used.  If both are given, the thumbnail will be no larger than either
        size.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param levelZero: if true, always use the level zero tile.  Otherwise,
            the thumbnail is generated so that it is never upsampled.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, and jpegSubsampling.
        :returns: thumbData, thumbMime: the image data and the mime type.
        """
        if ((width is not None and width < 2) or
                (height is not None and height < 2)):
            raise ValueError('Invalid width or height.  Minimum value is 2.')
        if width is None and height is None:
            width = height = 256
        # There are two code paths for generating thumbnails.  If
        # alwaysUseLevelZero is True, then the the thumbnail is generated more
        # swiftly, but may look poor.  We may want to add a parameter for this
        # option, or only use the high-quality results.
        if not levelZero:
            params = dict(kwargs)
            for key in ('left', 'top', 'right', 'bottom', 'regionWidth',
                        'regionHeight'):
                params.pop(key, None)
            return self.getRegion(width, height, **params)
        metadata = self.getMetadata()
        tileData = self.getTile(0, 0, 0)
        image = PIL.Image.open(BytesIO(tileData))
        imageWidth = int(math.floor(
            metadata['sizeX'] * 2 ** -(metadata['levels'] - 1)))
        imageHeight = int(math.floor(
            metadata['sizeY'] * 2 ** -(metadata['levels'] - 1)))
        image = image.crop((0, 0, imageWidth, imageHeight))

        if width or height:
            width, height = self._calculateWidthHeight(
                width, height, imageWidth, imageHeight)

            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > imageWidth else PIL.Image.LANCZOS)
        return self._encodeImage(image, **kwargs)

    def getPreferredLevel(self, level):
        """
        Given a desired level (0 is minimum resolution, self.levels - 1 is max
        resolution), return the level that contains actual data that is no
        lower resolution.

        :param level: desired level
        :returns level: a level with actual data that is no lower resolution.
        """
        metadata = self.getMetadata()
        if metadata['levels'] is None:
            return level
        return max(0, min(level, metadata['levels'] - 1))

    def getRegion(self, width=None, height=None, **kwargs):
        """
        Get a rectangular region from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, the original size of
        the highest resolution level is used.  If both are given, the returned
        image will be no larger than either size.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, top, left, right, bottom,
            regionWidth, regionHeight, units ('pixels' or 'fraction').
        :returns: regionData, regionMime: the image data and the mime type.
        """
        if ((width is not None and width < 0) or
                (height is not None and height < 0)):
            raise ValueError('Invalid width or height.  Minimum value is 0.')
        metadata = self.getMetadata()
        left, top, right, bottom = self._getRegionBounds(metadata, **kwargs)

        # If we are asked for a specific output size, determine the scaling
        regionWidth = right - left
        regionHeight = bottom - top

        if width is None and height is None:
            width, height = regionWidth, regionHeight
        width, height = self._calculateWidthHeight(
            width, height, regionWidth, regionHeight)
        if regionWidth == 0 or regionHeight == 0 or width == 0 or height == 0:
            image = PIL.Image.new('RGB', (0, 0))
            return self._encodeImage(image, **kwargs)

        preferredLevel = metadata['levels'] - 1
        # If we are scaling the result, pick the tile level that is at least
        # the resolution we need and is preferred by the tile source.
        if width != regionWidth or height != regionHeight:
            newLevel = self.getPreferredLevel(preferredLevel + int(
                math.ceil(math.log(max(float(width) / regionWidth,
                                       float(height) / regionHeight)) /
                          math.log(2))))
            if newLevel < preferredLevel:
                # scale the bounds to the level we will use
                factor = 2 ** (preferredLevel - newLevel)
                left = int(left / factor)
                right = int(right / factor)
                regionWidth = right - left
                top = int(top / factor)
                bottom = int(bottom / factor)
                regionHeight = bottom - top
                preferredLevel = newLevel

        xmin = int(left / metadata['tileWidth'])
        xmax = int(math.ceil(float(right) / metadata['tileWidth']))
        ymin = int(top / metadata['tileHeight'])
        ymax = int(math.ceil(float(bottom) / metadata['tileHeight']))
        logger.info(
            'Fetching region of an image with a source size of %d x %d; '
            'getting %d tiles',
            regionWidth, regionHeight, (xmax - xmin) * (ymax - ymin))
        # Use RGB mode.  If we need to support alpha on some encodings, this
        # can changed to RGBA.
        mode = 'RGBA' if kwargs.get('encoding') in ('PNG',) else 'RGB'

        # We can construct an image using PIL.Image.new:
        #   image = PIL.Image.new('RGB', (regionWidth, regionHeight))
        # but, for large images (larger than 4 Megapixels), PIL allocates one
        # memory region per line.  Although it frees this, the memory manager
        # often fails to reuse these smallish pieces.  By allocating the data
        # memory ourselves in one block, the memory manager does a better job.
        # Furthermode, if the source buffer isn't in RGBA format, the memory is
        # still often inaccessible.
        image = PIL.Image.frombuffer(
            mode, (regionWidth, regionHeight),
            # PIL will reallocate buffers that aren't in 'raw', RGBA, 0, 1.
            # See PIL documentation and code for more details.
            b'\x00' * (regionWidth * regionHeight * 4), 'raw', 'RGBA', 0, 1)
        for x in range(xmin, xmax):
            for y in range(ymin, ymax):
                tileData = self.getTile(
                    x, y, preferredLevel, pilImageAllowed=True,
                    sparseFallback=True)
                if not isinstance(tileData, PIL.Image.Image):
                    tileData = PIL.Image.open(BytesIO(tileData))
                posX = x * metadata['tileWidth'] - left
                posY = y * metadata['tileHeight'] - top
                # Add each tile to the image.  PIL crops these if they are off
                # the edge.
                image.paste(tileData, (posX, posY),
                            tileData if mode == 'RGBA' and
                            tileData.mode == 'RGBA' else None)

        # Scale if we need to
        if width != regionWidth or height != regionHeight:
            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > regionWidth else
                PIL.Image.LANCZOS)
        return self._encodeImage(image, **kwargs)


class FileTileSource(TileSource):
    def __init__(self, path, *args, **kwargs):
        super(FileTileSource, self).__init__(path, *args, **kwargs)

        self.largeImagePath = path

    def getState(self):
        return self._getLargeImagePath()

    def _getLargeImagePath(self):
        return self.largeImagePath

    @classmethod
    def canRead(cls, path, *args, **kwargs):
        """
        Check if we can read the input.  This takes the same parameters as
        __init__.

        :returns: True if this class can read the input.  False if it
                  cannot.
        """
        try:
            cls(path, *args, **kwargs)
            return True
        except TileSourceException:
            return False


# Girder specific classes

if girder:

    class GirderTileSource(FileTileSource):
        girderSource = True

        def __init__(self, item, *args, **kwargs):
            super(GirderTileSource, self).__init__(item, *args, **kwargs)
            self.item = item

        def getState(self):
            return str(self.item['largeImage']['fileId']) + ',' + str(
                self.item['updated'])

        def _getLargeImagePath(self):
            try:
                largeImageFileId = self.item['largeImage']['fileId']
                # Access control checking should already have been done on
                # item, so don't repeat.
                # TODO: is it possible that the file is on a different item, so
                # do we want to repeat the access check?
                largeImageFile = ModelImporter.model('file').load(
                    largeImageFileId, force=True)

                # TODO: can we move some of this logic into Girder core?
                assetstore = ModelImporter.model('assetstore').load(
                    largeImageFile['assetstoreId'])
                adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

                if not isinstance(
                        adapter,
                        assetstore_utilities.FilesystemAssetstoreAdapter):
                    raise TileSourceAssetstoreException(
                        'Non-filesystem assetstores are not supported')

                largeImagePath = adapter.fullPath(largeImageFile)
                return largeImagePath

            except TileSourceAssetstoreException:
                raise
            except (KeyError, ValidationException, TileSourceException) as e:
                raise TileSourceException(
                    'No large image file in this item: %s' % e.message)


def getTileSourceFromDict(availableSources, pathOrUri, user=None, *args,
                          **kwargs):
    """
    Get a tile source based on an ordered dictionary of known sources and a
    path name or URI.  Additional parameters are passed to the tile source
    and can be used for properties such as encoding.

    :param availableSources: an ordered dictionary of sources to try.
    :param pathOrUri: either a file path, a girder item in the form
        girder_item://(item id), large_image://test, or large_image://dummy.
    :param user: user used for access for girder items.  Ignored otherwise.
    :returns: a tile source instance or and error.
    """
    sourceObj = pathOrUri
    uriWithoutProtocol = pathOrUri.split('://', 1)[-1]
    isGirder = pathOrUri.startswith('girder_item://')
    if isGirder and girder:
        sourceObj = ModelImporter.model('item').load(
            uriWithoutProtocol, user=user, level=AccessType.READ)
    isLargeImageUri = pathOrUri.startswith('large_image://')
    for sourceName in availableSources:
        useSource = False
        girderSource = getattr(availableSources[sourceName], 'girderSource',
                               False)
        if isGirder:
            if girderSource:
                useSource = availableSources[sourceName].canRead(sourceObj)
        elif isLargeImageUri:
            if sourceName == uriWithoutProtocol:
                useSource = True
        elif not girderSource:
            useSource = availableSources[sourceName].canRead(sourceObj)
        if useSource:
            return availableSources[sourceName](sourceObj, *args, **kwargs)
    raise TileSourceException('No available tilesource for %s' % pathOrUri)
