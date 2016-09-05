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
try:
    import numpy
except ImportError:
    logger.warning('Error: Could not import numpy')
    numpy = None


TILE_FORMAT_IMAGE = 'image'
TILE_FORMAT_PIL = 'PIL'
TILE_FORMAT_NUMPY = 'numpy'

TileOutputMimeTypes = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png'
}


class TileSourceException(TileGeneralException):
    pass


class TileSourceAssetstoreException(TileSourceException):
    pass


class TileSource(object):
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
                         Must also be in the TileOutputMimeTypes map.
        :param jpegQuality: the quality to use when encoding a JPEG.
        :param jpegSubsampling: the subsampling level to use when encoding a
                                JPEG.
        """
        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        if image.width == 0 or image.height == 0:
            tileData = b''
        else:
            output = BytesIO()
            image.save(output, encoding, quality=jpegQuality,
                       subsampling=jpegSubsampling)
            tileData = output.getvalue()
        return tileData, TileOutputMimeTypes[encoding]

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

    def _tileIteratorInfo(self, width, height, **kwargs):
        """
        Get information necessary to construct a tile iterator.
          If one of width or height is specified, the other is determined by
        preserving aspect ratio.  If both are specified, the result may not be
        that size, as aspect ratio is always preserved.  If neither are
        specified, magnfication, mm_x, and/or mm_y are used to determine the
        size.  If none of those are specified, the original maximum resolution
        is returned.
          left, top, right, bottom, regionWidth, and reionHeight are used to
        select part of the image to return in maximum resolution pixel
        coordinates.  By default, these are the entire image.  Any two of the
        three parameters per axis may be specified.  If all three are given,
        the width or height is ignored.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param left: the top of the region to output.
        :param top: the top of the region to output.
        :param right: the top of the region to output.
        :param bottom: the top of the region to output.
        :param regionWidth: the width of the region to output.
        :param regionHeight: the height of the region to output.
        :param units: either 'pixels' (default) or 'fraction'.  If pixels, the
            left, top, right, bottom, regionWidth, and regionHeight are in
            maximum resolution pixels.  If fraction, they are all on a scale of
            0 to 1.
        :param magnification: the magnification ratio.
        :param mm_x: the horizontal size of a pixel in millimeters.
        :param mm_y: the vertical size of a pixel in millimeters.
        :param exact: if True, only a level that matches exactly will be
            returned.  This is only applied if magnification, mm_x, or mm_y is
            used.
        :param upscale: if True, only allow upscale for non-exact matches.
            Otherwise, specificying magnification, mm_x, or mm_y will select
            the closest level to the requested resolution.
        :param format: a tuple of allowed formats.  Formats are members of
            TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
            Otherwis,e TILE_FORMAT_PIL is returned.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling.
        :returns: a dictionary of information needed for the tile iterator.
                This is None if no tiles will be returned.  Otherwise, this
                contains:
            regionWidth, regionHeight: the total output of the iterator in
                pixels.
            xmin, ymin, xmax, ymax: the tiles that will be included during the
                iteration: [xmin, xmax) and [ymin, ymax).
            mode: either 'RGB' or 'RGBA'.  This determines the color space used
                for tiles.
            level: the tile level used for iteration.
            metadata: tile source metadata (from getMetadata)
            left, top: the coordinates within the image of the region returned
                in the level pixel space.
            width, height: the requested output resolution in pixels.  If this
                is different that regionWidth and regionHeight, then the
                original request was asking for a different scale that is being
                delivered.
        """
        if ((width is not None and width < 0) or
                (height is not None and height < 0)):
            raise ValueError('Invalid width or height.  Minimum value is 0.')
        metadata = self.getMetadata()
        left, top, right, bottom = self._getRegionBounds(metadata, **kwargs)

        # If we are asked for a specific output size, determine the scaling
        regionWidth = right - left
        regionHeight = bottom - top

        magLevel = None
        if width is None and height is None:
            # If neither width nor height as specified, see if magnification,
            # mm_x, or mm_y are requested.
            magLevel = self.getLevelForMagnification(**kwargs)
            if magLevel is None and kwargs.get('exact'):
                return None
            mag = self.getMagnificationForLevel(magLevel)
            if mag.get('scale') in (1.0, None):
                width, height = regionWidth, regionHeight
            else:
                width = regionWidth / mag['scale']
                height = regionHeight / mag['scale']
        width, height = self._calculateWidthHeight(
            width, height, regionWidth, regionHeight)
        if regionWidth == 0 or regionHeight == 0 or width == 0 or height == 0:
            return None

        preferredLevel = metadata['levels'] - 1
        # If we are scaling the result, pick the tile level that is at least
        # the resolution we need and is preferred by the tile source.
        if width != regionWidth or height != regionHeight:
            newLevel = self.getPreferredLevel(preferredLevel + int(
                math.ceil(round(math.log(max(float(width) / regionWidth,
                                             float(height) / regionHeight)) /
                                math.log(2), 4))))
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
        # If an exact magnification was requested and this tile source doesn't
        # have tiles at the appropriate level, indicate that we won't return
        # anything.
        if (magLevel is not None and magLevel != preferredLevel and
                kwargs.get('exact')):
            return None

        xmin = int(left / metadata['tileWidth'])
        xmax = int(math.ceil(float(right) / metadata['tileWidth']))
        ymin = int(top / metadata['tileHeight'])
        ymax = int(math.ceil(float(bottom) / metadata['tileHeight']))

        # Use RGB for JPEG, RGBA for PNG
        mode = 'RGBA' if kwargs.get('encoding') in ('PNG',) else 'RGB'

        info = {
            'top': top,
            'left': left,
            'bottom': bottom,
            'right': right,
            'regionWidth': regionWidth,
            'regionHeight': regionHeight,
            'xmin': xmin,
            'ymin': ymin,
            'xmax': xmax,
            'ymax': ymax,
            'mode': mode,
            'level': preferredLevel,
            'metadata': metadata,
            'width': width,
            'height': height,
            'format': kwargs.get('format', (TILE_FORMAT_PIL, )),
            'encoding': kwargs.get('encoding'),
        }
        return info

    def _tileIterator(self, iterInfo):
        """
        Given tile iterator information, iterate through the tiles.
        Each tile is returned as part of a dictionary that includes
            x, y: (left, top) coordinate in current magnification pixels
            height, width: size of current tile in pixels
            tile: cropped tile image
            format: format of the tile.  Always TILE_FORMAT_PIL or
                TILE_FORMAT_IMAGE.  TILE_FORMAT_IMAGE is only returned if it
                was explicitly allowed and the tile is already in the correct
                image encoding.
            level: level of the current tile. None if not present
            level_x, level_y: the tile reference number within the level.
            magnification: magnification of the current tile
            mm_x, mm_y: size of the current tile pixel in millimeters.
            gx, gy - (left, top) coordinate in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum resolution
                pixels.
        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom egdes in any case.

        :param iterInfo: tile iterator information.  See _tileIteratorInfo.
        :yields: an iterator that returns a dictionary as listed above.
        """
        regionWidth = iterInfo['regionWidth']
        regionHeight = iterInfo['regionHeight']
        xmin = iterInfo['xmin']
        ymin = iterInfo['ymin']
        xmax = iterInfo['xmax']
        ymax = iterInfo['ymax']
        level = iterInfo['level']
        metadata = iterInfo['metadata']
        top = iterInfo['top']
        left = iterInfo['left']
        format = iterInfo['format']
        encoding = iterInfo['encoding']

        logger.info(
            'Fetching region of an image with a source size of %d x %d; '
            'getting %d tiles',
            regionWidth, regionHeight, (xmax - xmin) * (ymax - ymin))
        mag = self.getMagnificationForLevel(level)
        scale = mag.get('scale', 1.0)
        for x in range(xmin, xmax):
            for y in range(ymin, ymax):
                tileData = self.getTile(
                    x, y, level, pilImageAllowed=True, sparseFallback=True)
                tileFormat = TILE_FORMAT_PIL
                # If the tile isn't in PIL format, and it is not in an image
                # format that is the same as a desired output format and
                # encoding, convert it to PIL format.
                if not isinstance(tileData, PIL.Image.Image):
                    pilData = PIL.Image.open(BytesIO(tileData))
                    if (format and 'TILE_FORMAT_IMAGE' in format and
                            pilData.format == encoding):
                        tileFormat = TILE_FORMAT_IMAGE
                    else:
                        tileData = pilData
                posX = x * metadata['tileWidth'] - left
                posY = y * metadata['tileHeight'] - top
                tileWidth = metadata['tileWidth']
                tileHeight = metadata['tileHeight']
                # crop as needed
                if (posX < 0 or posY < 0 or posX + tileWidth > regionWidth or
                        posY + tileHeight > regionHeight):
                    crop = (max(0, -posX),
                            max(0, -posY),
                            min(tileWidth, regionWidth - posX),
                            min(tileHeight, regionHeight - posY))
                    tileData = tileData.crop(crop)
                    posX += crop[0]
                    posY += crop[1]
                    tileWidth = crop[2] - crop[0]
                    tileHeight = crop[3] - crop[1]
                tile = {
                    'x': posX + left,
                    'y': posY + top,
                    'width': tileWidth,
                    'height': tileHeight,
                    'tile': tileData,
                    'format': tileFormat,
                    'level': level,
                    'level_x': x,
                    'level_y': y,
                    'magnification': mag['magnification'],
                    'mm_x': mag['mm_x'],
                    'mm_y': mag['mm_y'],
                }
                tile['gx'] = tile['x'] * scale
                tile['gy'] = tile['y'] * scale
                tile['gwidth'] = tile['width'] * scale
                tile['gheight'] = tile['height'] * scale
                yield tile

    @classmethod
    def canRead(cls, *args, **kwargs):
        """
        Check if we can read the input.  This takes the same parameters as
        __init__.

        :returns: True if this class can read the input.  False if it cannot.
        """
        return False

    def getMetadata(self):
        mag = self.getMagnification()
        return {
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'magnification': mag['magnification'],
            'pixelWidthInMillimeters': mag['mm_x'],
            'pixelHeightInMillimeters': mag['mm_y'],
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
            regionWidth, regionHeight, units ('pixels' or 'fraction'),
            magnification, mm_x, mm_y, exact, upscale.  See _tileIteratorInfo.
        :returns: regionData, regionMime: the image data and the mime type.
        """
        iterInfo = self._tileIteratorInfo(width, height, **kwargs)
        if iterInfo is None:
            image = PIL.Image.new('RGB', (0, 0))
            return self._encodeImage(image, **kwargs)
        regionWidth = iterInfo['regionWidth']
        regionHeight = iterInfo['regionHeight']
        mode = iterInfo['mode']
        top = iterInfo['top']
        left = iterInfo['left']
        width = iterInfo['width']
        height = iterInfo['height']
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
        for tile in self._tileIterator(iterInfo):
            # Add each tile to the image.  PIL crops these if they are off the
            # edge.
            image.paste(tile['tile'], (tile['x'] - left, tile['y'] - top),
                        tile['tile'] if mode == 'RGBA' and
                        tile['tile'].mode == 'RGBA' else None)
        # Scale if we need to
        width = int(math.floor(width))
        height = int(math.floor(height))
        if width != regionWidth or height != regionHeight:
            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > regionWidth else
                PIL.Image.LANCZOS)
        return self._encodeImage(image, **kwargs)

    def getMagnification(self):
        """
        Get the magnification for the highest-resolution level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        return {
            'magnification': None,
            'mm_x': None,
            'mm_y': None
        }

    def getMagnificationForLevel(self, level=None):
        """
        Get the magnification at a particular level.

        :param level: None to use the maximum level, otherwise the level to get
            the magification factor of.
        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mag = self.getMagnification()

        if level is not None and self.levels and level != self.levels - 1:
            mag['scale'] = 2.0 ** (self.levels - 1 - level)
            if mag['magnification']:
                mag['magnification'] /= mag['scale']
            if mag['mm_x'] and mag['mm_y']:
                mag['mm_x'] *= mag['scale']
                mag['mm_y'] *= mag['scale']
        if self.levels:
            mag['level'] = level if level is not None else self.levels - 1
        return mag

    def getLevelForMagnification(self, magnification=None, exact=False,
                                 mm_x=None, mm_y=None, upscale=False,
                                 **kwargs):
        """
        Get the level for a specific magnifcation or pixel size.  If the
        magnification is unknown or no level is sufficient resolution, and an
        exact match is not requested, the highest level will be returned.  If
        an exact match is not found, the closest level is returned, unless
        upscale=False, in which case it will always be the higher level.
          At least one of magnification, mm_x, and mm_y must be specified.  If
        more than one of these values is given, an average of those given will
        be used (exact will require all of them to match).

        :param magnification: the magnification ratio.
        :param exact: if True, only a level that matches exactly will be
            returned.
        :param mm_x: the horizontal size of a pixel in millimeters.
        :param mm_y: the vertical size of a pixel in millimeters.
        :param upscale: if True, only allow upscale for non-exact matches.
        :returns: the selected level or None for no match.
        """
        mag = self.getMagnificationForLevel()
        ratios = []
        if magnification and mag['magnification']:
            ratios.append(float(magnification) / mag['magnification'])
        if mm_x and mag['mm_x']:
            ratios.append(mag['mm_x'] / mm_x)
        if mm_y and mag['mm_y']:
            ratios.append(mag['mm_y'] / mm_y)
        ratios = [math.log(ratio) / math.log(2) for ratio in ratios]
        # Perform some slight rounding to handle numerical precision issues
        ratios = [round(ratio, 4) for ratio in ratios]
        if not len(ratios):
            return None if exact else mag['level']
        if exact:
            if any(int(ratio) != ratio or ratio != ratios[0]
                   for ratio in ratios):
                return None
        ratio = sum(ratios) / len(ratios)
        level = mag['level'] + ratio
        level = int(math.ceil(level) if upscale else round(level))
        if (exact and (level > mag['level'] or level < 0) or
                (upscale and level > mag['level'])):
            return None
        level = max(0, min(mag['level'], level))
        return level

    def tileIterator(self, format=(TILE_FORMAT_PIL, ), **kwargs):
        """
        Iterate on all tiles in the specifed region at the specified scale.
        Each tile is returned as part of a dictionary that includes
            x, y: (left, top) coordinate in current magnification pixels
            height, width: size of current tile in pixels
            tile: cropped tile image
            format: format of the tile
            level: level of the current tile. None if not present
            level_x, level_y: the tile reference number within the level.
            magnification: magnification of the current tile
            mm_x, mm_y: size of the current tile pixel in millimeters.
            gx, gy - (left, top) coordinate in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum resolution
                pixels.
        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom egdes in any case.  If an exact
        magnification or scale is requested, no tiles will be returned unless
        allowInterpolation is true.

        :param format: the desired format or a tuple of allowed formats.
            Formats are members of TILE_FORMAT_*.
        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param left: the top of the region to output.
        :param top: the top of the region to output.
        :param right: the top of the region to output.
        :param bottom: the top of the region to output.
        :param regionWidth: the width of the region to output.
        :param regionHeight: the height of the region to output.
        :param units: either 'pixels' (default) or 'fraction'.  If pixels, the
            left, top, right, bottom, regionWidth, and regionHeight are in
            maximum resolution pixels.  If fraction, they are all on a scale of
            0 to 1.
        :param magnification: the magnification ratio.
        :param mm_x: the horizontal size of a pixel in millimeters.
        :param mm_y: the vertical size of a pixel in millimeters.
        :param exact: if True, only a level that matches exactly will be
            returned.  This is only applied if magnification, mm_x, or mm_y is
            used.
        :param upscale: if True, only allow upscale for non-exact matches.
            Otherwise, specificying magnification, mm_x, or mm_y will select
            the closest level to the requested resolution.
        :param encoding: if format includes TILE_FORMAT_IMAGE, a valid PIL
            encoding (typically 'PNG' or 'JPEG').  Must also be in the
            TileOutputMimeTypes map.
        :param jpegQuality: the quality to use when encoding a JPEG.
        :param jpegSubsampling: the subsampling level to use when encoding a
                                JPEG.
        :param **kwargs: optional arguments.
        :yields: an iterator that returns a dictionary as listed above.
        """
        if not isinstance(format, tuple):
            format = (format, )
        if TILE_FORMAT_IMAGE in format:
            encoding = kwargs.get('encoding')
            if encoding not in TileOutputMimeTypes:
                raise ValueError('Invalid encoding "%s"' % encoding)
        iterInfo = self._tileIteratorInfo(format=format, **kwargs)
        if not iterInfo:
            return
        for tile in self._tileIterator(iterInfo):
            if tile['format'] in format:
                # already in an acceptable format
                pass
            elif TILE_FORMAT_NUMPY in format and numpy:
                tile['tile'] = numpy.asarray(tile['tile'])
                tile['format'] = format
            elif TILE_FORMAT_IMAGE in format:
                output = BytesIO()
                tile['tile'].save(
                    output, encoding, quality=kwargs.get('jpegQuality'),
                    subsampling=kwargs.get('jpegSubsampling'))
                tile['tile'] = output.getvalue()
                tile['format'] = format
            if tile['format'] not in format:
                raise TileSourceException(
                    'Cannot yield tiles in desired format %r' % (format, ))

            yield tile


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
