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

import math
from six import BytesIO

from ..cache_util import tileCache, tileLock, strhash, methodcache

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
    logger.getLogger().setLevel(logger.INFO)
    girder = None

    class TileGeneralException(Exception):
        pass

# Not having PIL disables thumbnail creation, but isn't fatal
try:
    import PIL

    if int(PIL.PILLOW_VERSION.split('.')[0]) < 3:
        logger.warning('Error: Pillow v3.0 or later is required')
        PIL = None
    import PIL.Image
    import PIL.ImageColor
    import PIL.ImageDraw
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
    # JFIF forces conversion to JPEG through PIL to ensure the image is in a
    # common colorspace.  JPEG colorspace is complex: see
    #   https://docs.oracle.com/javase/8/docs/api/javax/imageio/metadata/
    #                           doc-files/jpeg_metadata.html
    'JFIF': 'image/jpeg',
    'JPEG': 'image/jpeg',
    'PNG': 'image/png'
}
TileOutputPILFormat = {
    'JFIF': 'JPEG'
}
TileInputUnits = {
    None: 'base_pixels',
    'base_pixel': 'base_pixels',
    'base_pixels': 'base_pixels',
    'pixel': 'mag_pixels',
    'pixels': 'mag_pixels',
    'mag_pixel': 'mag_pixels',
    'mag_pixels': 'mag_pixels',
    'magnification_pixel': 'mag_pixels',
    'magnification_pixels': 'mag_pixels',
    'mm': 'mm',
    'millimeter': 'mm',
    'millimeters': 'mm',
    'fraction': 'fraction',
}


class TileSourceException(TileGeneralException):
    pass


class TileSourceAssetstoreException(TileSourceException):
    pass


def _encodeImage(image, encoding='JPEG', jpegQuality=95, jpegSubsampling=0,
                 format=(TILE_FORMAT_IMAGE, ), **kwargs):
    """
    Convert a PIL image into the raw output bytes and a mime type.

    :param image: a PIL image.
    :param encoding: a valid PIL encoding (typically 'PNG' or 'JPEG').  Must
        also be in the TileOutputMimeTypes map.
    :param jpegQuality: the quality to use when encoding a JPEG.
    :param jpegSubsampling: the subsampling level to use when encoding a JPEG.
    :param format: the desired format or a tuple of allowed formats.  Formats
        are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY, TILE_FORMAT_IMAGE).
    :returns:
        imageData: the image data in the specified format and encoding.
        imageFormatOrMimeType: the image mime type if the format is
            TILE_FORMAT_IMAGE, or the format of the image data if it is
            anything else.
    """
    if not isinstance(format, tuple):
        format = (format, )
    imageData = image
    imageFormatOrMimeType = TILE_FORMAT_PIL
    if TILE_FORMAT_PIL in format:
        # already in an acceptable format
        pass
    elif TILE_FORMAT_NUMPY in format:
        imageData = numpy.asarray(image)
        imageFormatOrMimeType = TILE_FORMAT_NUMPY
    elif TILE_FORMAT_IMAGE in format:
        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        imageFormatOrMimeType = TileOutputMimeTypes[encoding]
        if image.width == 0 or image.height == 0:
            imageData = b''
        else:
            output = BytesIO()
            image.save(output, TileOutputPILFormat.get(encoding, encoding),
                       quality=jpegQuality, subsampling=jpegSubsampling)
            imageData = output.getvalue()
    return imageData, imageFormatOrMimeType


class LazyTileDict(dict):
    """
    Tiles returned from the tile iterator and dictioaries of information with
    actual image data in the 'tile' key and the format in the 'format' key.
    Since some applications need information about the tile but don't need the
    image data, these two values are lazily computed.  The LazyTileDict can be
    treated like a regular dictionary, except that when either of those two
    keys are first accessed, they will cause the image to be loaded and
    possibly converted to a PIL image and cropped.

    Unless setFormat is called on the tile, tile images may always be returned
    as PIL images.
    """
    def __init__(self, tileInfo, *args, **kwargs):
        """
        Create a LazyTileDict dictionary where there is enough information to
        load the tile image.  ang and kwargs are as for the dict() class.

        :param tileInfo: a dictionary of x, y, level, format, encoding, crop,
            and source, used for fetching the tile image.
        """
        self.x = tileInfo['x']
        self.y = tileInfo['y']
        self.level = tileInfo['level']
        self.format = tileInfo['format']
        self.encoding = tileInfo['encoding']
        self.crop = tileInfo['crop']
        self.source = tileInfo['source']
        self.resample = tileInfo.get('resample', False)
        self.requestedScale = tileInfo.get('requestedScale')
        self.metadata = tileInfo.get('metadata')
        self.retile = tileInfo.get('retile') and self.metadata

        self.deferredKeys = ('tile', 'format')
        self.alwaysAllowPIL = True
        self.imageKwargs = {}
        self.loaded = False
        result = super(LazyTileDict, self).__init__(*args, **kwargs)
        # We set this initially so that they are listed in known keys using the
        # native dictionary methods
        self['tile'] = None
        self['format'] = None
        return result

    def setFormat(self, format, resample=False, imageKwargs=None):
        """
        Set a more restrictuve output format for a tile, possibly also resizing
        it via resampling.  If this is not called, the tile may either as one
        of the specified formats or as a PIL image.

        :param format: a tuple or list of allowed formats.  Formats are members
            of TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
        :param resample: if true, allow resampling.  Once turned on, this
            cannot be turned off on the tile.
        :param imageKwargs: additional parameters taht should be passed to
            _encodeImage.
        """
        # If any parameters are changed, mark the tile as not loaded, so that
        # referring to a deferredKey will reload the image.
        self.alwaysAllowPIL = False
        if format is not None and format != self.format:
            self.format = format
            self.loaded = False
        if (resample and not self.resample and self.requestedScale and
                round(self.requestedScale, 2) != 1.0):
            self.resample = resample
            self['scaled'] = 1.0 / self.requestedScale
            self['tile_x'] = self.get('tile_x', self['x'])
            self['tile_y'] = self.get('tile_y', self['y'])
            self['tile_width'] = self.get('tile_width', self['width'])
            self['tile_height'] = self.get('tile_width', self['height'])
            self['x'] = float(self['tile_x']) / self.requestedScale
            self['y'] = float(self['tile_y']) / self.requestedScale
            # If we can resample the tile, many parameters may change
            # once the image is loaded.
            self.deferredKeys = ('tile', 'format', 'width', 'height')
            self.loaded = False
        if imageKwargs is not None:
            self.imageKwargs = imageKwargs
            self.loaded = False

    def _retileTile(self):
        """
        Given the tile information, create a PIL image and merge multiple tiles
        together to form a tile of a different size.
        """
        retile = None
        xmin = max(0, self['x'] // self.metadata['tileWidth'])
        xmax = (self['x'] + self['width'] - 1) // self.metadata['tileWidth'] + 1
        ymin = max(0, self['y'] // self.metadata['tileHeight'])
        ymax = (self['y'] + self['height'] - 1) // self.metadata['tileHeight'] + 1
        for x in range(xmin, xmax):
            for y in range(ymin, ymax):
                tileData = self.source.getTile(
                    x, y, self.level,
                    pilImageAllowed=True, sparseFallback=True)
                if not isinstance(tileData, PIL.Image.Image):
                    tileData = PIL.Image.open(BytesIO(tileData))
                if retile is None:
                    retile = PIL.Image.new(
                        tileData.mode, (self['width'], self['height']))
                retile.paste(tileData, (
                    x * self.metadata['tileWidth'] - self['x'],
                    y * self.metadata['tileHeight'] - self['y']))
        return retile

    def __getitem__(self, key, *args, **kwargs):
        """
        If this is the first time either the tile or format key is requested,
        load the tile image data.  Otherwise, just return the internal
        dictionary result.

        See the base dict class for function details.
        """
        if not self.loaded and key in self.deferredKeys:
            # Flag this immediately to avoid recursion if we refer to the
            # tile's own values.
            self.loaded = True

            if not self.retile:
                tileData = self.source.getTile(
                    self.x, self.y, self.level,
                    pilImageAllowed=True, sparseFallback=True)
            else:
                tileData = self._retileTile()
            tileFormat = TILE_FORMAT_PIL
            # If the tile isn't in PIL format, and it is not in an image format
            # that is the same as a desired output format and encoding, convert
            # it to PIL format.
            if not isinstance(tileData, PIL.Image.Image):
                pilData = PIL.Image.open(BytesIO(tileData))
                if (self.format and TILE_FORMAT_IMAGE in self.format and
                        pilData.format == self.encoding):
                    tileFormat = TILE_FORMAT_IMAGE
                else:
                    tileData = pilData
            else:
                pilData = tileData
            if self.crop and not self.retile:
                tileData = pilData.crop(self.crop)
                tileFormat = TILE_FORMAT_PIL

            # resample if needed
            if self.resample and self.requestedScale:
                self['width'] = max(1, int(
                    tileData.size[0] / self.requestedScale))
                self['height'] = max(1, int(
                    tileData.size[1] / self.requestedScale))
                tileData = tileData.resize(
                    (self['width'], self['height']), resample=self.resample)

            # Reformat the image if required
            if not self.alwaysAllowPIL:
                if tileFormat in self.format:
                    # already in an acceptable format
                    pass
                elif TILE_FORMAT_NUMPY in self.format and numpy:
                    tileData = numpy.asarray(tileData)
                    tileFormat = TILE_FORMAT_NUMPY
                elif TILE_FORMAT_IMAGE in self.format:
                    tileData, mimeType = _encodeImage(
                        tileData, **self.imageKwargs)
                    tileFormat = TILE_FORMAT_IMAGE
                if tileFormat not in self.format:
                    raise TileSourceException(
                        'Cannot yield tiles in desired format %r' % (
                            self.format, ))

            self['tile'] = tileData
            self['format'] = tileFormat
        return super(LazyTileDict, self).__getitem__(key, *args, **kwargs)


class TileSource(object):
    name = None

    cache = tileCache
    cache_lock = tileLock

    def __init__(self, jpegQuality=95, jpegSubsampling=0,
                 encoding='JPEG', edge=False, *args, **kwargs):
        """
        Initialize the tile class.

        :param jpegQuality: when serving jpegs, use this quality.
        :param jpegSubsampling: when serving jpegs, use this subsampling (0 is
                                full chroma, 1 is half, 2 is quarter).
        :param encoding: 'JPEG' or 'PNG'.
        :param edge: False to leave edge tiles whole, True or 'crop' to crop
            edge tiles, otherwise, an #rrggbb color to fill edges.
        """
        self.tileWidth = None
        self.tileHeight = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None

        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)

        self.encoding = encoding
        self.jpegQuality = int(jpegQuality)
        self.jpegSubsampling = int(jpegSubsampling)
        self.edge = edge

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            kwargs.get('encoding'), kwargs.get('jpegQuality'),
            kwargs.get('jpegSubsampling'), kwargs.get('edge'))

    def getState(self):
        return str(self.encoding) + ',' + str(self.jpegQuality) + ',' + str(
            self.jpegSubsampling) + ',' + str(self.edge)

    def wrapKey(self, *args, **kwargs):
        return strhash(self.getState()) + strhash(*args, **kwargs)

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
                  and preserves aspect ratio, and the scaling factor used for
                  the conversion.
        """
        if regionWidth == 0 or regionHeight == 0:
            return 0, 0, 1
        # Constrain the maximum size if both width and height weren't
        # specified, in case the image is very short or very narrow.
        if height and not width:
            width = height * 16
        if width and not height:
            height = width * 16
        if width * regionHeight > height * regionWidth:
            scale = float(height) / regionHeight
            width = max(1, int(regionWidth * height / regionHeight))
        else:
            scale = float(width) / regionWidth
            height = max(1, int(regionHeight * width / regionWidth))
        return width, height, scale

    def _getRegionBounds(self, metadata, left=None, top=None, right=None,
                         bottom=None, width=None, height=None,
                         units='base_pixels', desiredMagnification=None,
                         **kwargs):
        """
        Given a set of arguments that can include left, right, top, bottom,
        width, height, and units, generate actual pixel values for left, top,
        right, and bottom.  If left, top, right, or bottom are negative they
        are interpretted as an offset from the right or bottom edge of the
        image.

        :param metadata: the metadata associated with this source.
        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both
            left and right are specified.
        :param height: the height of the region to process.  Ignores if both
            top and bottom are specified.
        :param units: either 'base_pixels' (default), 'pixels', 'mm', or
            'fraction'.  base_pixels are in maximum resolution pixels.
            pixels is in the specified magnification pixels.  mm is in the
            specified magnification scale.  fraction is a scale of 0 to 1.
            pixels and mm are only available if the magnification and mm
            per pixel are defined for the image.
        :param desiredMagnification: the output from getMagnificationForLevel
            for the desired magnfication used to convert mag_pixels and mm.
        :param **kwargs: optional parameters.  See above.
        :returns: left, top, right, bottom bounds in pixels.
        """
        if units not in TileInputUnits:
            raise ValueError('Invalid units "%s"' % units)
        # Convert units to max-resolution pixels
        units = TileInputUnits[units]
        scaleX = scaleY = 1
        if units == 'fraction':
            scaleX = metadata['sizeX']
            scaleY = metadata['sizeY']
        elif units == 'mag_pixels':
            if not (desiredMagnification or {}).get('scale'):
                raise ValueError('No magnification to use for units')
            scaleX = scaleY = desiredMagnification['scale']
        elif units == 'mm':
            if (not (desiredMagnification or {}).get('scale') or
                    not (desiredMagnification or {}).get('mm_x') or
                    not (desiredMagnification or {}).get('mm_y')):
                raise ValueError('No mm_x or mm_y to use for units')
            scaleX = (desiredMagnification['scale'] /
                      desiredMagnification['mm_x'])
            scaleY = (desiredMagnification['scale'] /
                      desiredMagnification['mm_y'])
        region = {'left': left, 'top': top, 'right': right,
                  'bottom': bottom, 'width': width, 'height': height}
        region = {key: region[key] for key in region if region[key] is not None}
        for key in ('left', 'right', 'width'):
            if key in region and scaleX and scaleX != 1:
                region[key] = region[key] * scaleX
        for key in ('top', 'bottom', 'height'):
            if key in region and scaleY and scaleY != 1:
                region[key] = region[key] * scaleY
        # convert negative references to right or bottom offsets
        for key in ('left', 'right', 'top', 'bottom'):
            if key in region and region.get(key) < 0:
                region[key] += metadata[
                    'sizeX' if key in ('left', 'right') else 'sizeY']
        # Calculate the region we need to fetch
        left = region.get(
            'left',
            (region.get('right') - region.get('width'))
            if ('right' in region and 'width' in region) else 0)
        right = region.get(
            'right',
            (left + region.get('width'))
            if ('width' in region) else metadata['sizeX'])
        top = region.get(
            'top', region.get('bottom') - region.get('height')
            if 'bottom' in region and 'height' in region else 0)
        bottom = region.get(
            'bottom', top + region.get('height')
            if 'height' in region else metadata['sizeY'])
        # Crop the bounds to integer pixels within the actual source data
        left = min(metadata['sizeX'], max(0, int(round(left))))
        right = min(metadata['sizeX'], max(left, int(round(right))))
        top = min(metadata['sizeY'], max(0, int(round(top))))
        bottom = min(metadata['sizeY'], max(top, int(round(bottom))))

        return left, top, right, bottom

    def _tileIteratorInfo(self, **kwargs):
        """
        Get information necessary to construct a tile iterator.
          If one of width or height is specified, the other is determined by
        preserving aspect ratio.  If both are specified, the result may not be
        that size, as aspect ratio is always preserved.  If neither are
        specified, magnfication, mm_x, and/or mm_y are used to determine the
        size.  If none of those are specified, the original maximum resolution
        is returned.

        :param format: a tuple of allowed formats.  Formats are members of
            TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
            Otherwise, TILE_FORMAT_PIL is returned.
        :param region: a dictionary of optional values which specify the part
                of the image to process.
            left: the left edge (inclusive) of the region to process.
            top: the top edge (inclusive) of the region to process.
            right: the right edge (exclusive) of the region to process.
            bottom: the bottom edge (exclusive) of the region to process.
            width: the width of the region to process.
            height: the height of the region to process.
            units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.
        :param output: a dictionary of optional values which specify the size
                of the output.
            maxWidth: maximum width in pixels.
            maxHeight: maximum height in pixels.
        :param scale: a dictionary of optional values which specify the scale
                of the region and / or output.  This applies to region if
                pixels or mm are used for inits.  It applies to output if
                neither output maxWidth nor maxHeight is specified.  It
            magnification: the magnification ratio.
            mm_x: the horizontal size of a pixel in millimeters.
            mm_y: the vertical size of a pixel in millimeters.
            exact: if True, only a level that matches exactly will be returned.
                This is only applied if magnification, mm_x, or mm_y is used.
        :param tile_position: if present, either a number to only yield the
            (tile_position)th tile [0 to (xmax - min) * (ymax - ymin)) that the
            iterator would yield, or a dictionary of {region_x, region_y} to
            yield that tile, where 0, 0 is the first tile yielded, and
            xmax - xmin - 1, ymax - ymin - 1 is the last tile yielded, or a
            dictionary of {level_x, level_y} to yield that specific tile if it
            is in the region.
        :param tile_size: if present, retile the output to the specified tile
                size.  If only width or only height is specified, the resultant
                tiles will be square.  This is a dictionary containing at least
                one of:
            width: the desired tile width.
            height: the desired tile height.
        :param tile_overlap: if present, retile the output adding a symmetric
                overlap to the tiles.  If either x or y is not specified, it
                defaults to zero.  The overlap does not change the tile size,
                only the stride of the tiles.  This is a dictionary containing:
            x: the horizontal overlap in pixels.
            y: the vertical overlap in pixels.
            edges: if True, then the edge tiles will exclude the overlap
                distance.  If unset or False, the edge tiles are full size.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling.
        :returns: a dictionary of information needed for the tile iterator.
                This is None if no tiles will be returned.  Otherwise, this
                contains:
            region: a dictionary of the source region information:
                width, height: the total output of the iterator in pixels.
                    This may be larger than the requested resolution (given by
                    output width and output height) if there isn't an exact
                    match between the requested resolution and available native
                    tiles.
                left, top, right, bottom: the coordinates within the image of
                    the region returned in the level pixel space.
            xmin, ymin, xmax, ymax: the tiles that will be included during the
                iteration: [xmin, xmax) and [ymin, ymax).
            mode: either 'RGB' or 'RGBA'.  This determines the color space used
                for tiles.
            level: the tile level used for iteration.
            metadata: tile source metadata (from getMetadata)
            output: a dictionary of the output resolution information.
                width, height: the requested output resolution in pixels.  If
                    this is different that region width and regionH hight, then
                    the original request was asking for a different scale than
                    is being delivered.
            format: a tuple of allowed output formats.
            encoding: if the output format is TILE_FORMAT_IMAGE, the desired
                encoding.
            requestedScale: the scale needed to convert from the region width
                and height to the output width and height.
        """
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if ((maxWidth is not None and maxWidth < 0) or
                (maxHeight is not None and maxHeight < 0)):
            raise ValueError(
                'Invalid output width or height.  Minimum value is 0.')

        magLevel = None
        mag = None
        if maxWidth is None and maxHeight is None:
            # If neither width nor height as specified, see if magnification,
            # mm_x, or mm_y are requested.
            magArgs = (kwargs.get('scale') or {}).copy()
            magArgs['rounding'] = None
            magLevel = self.getLevelForMagnification(**magArgs)
            if magLevel is None and kwargs.get('scale', {}).get('exact'):
                return None
            mag = self.getMagnificationForLevel(magLevel)

        metadata = self.getMetadata()
        left, top, right, bottom = self._getRegionBounds(
            metadata, desiredMagnification=mag, **kwargs.get('region', {}))
        regionWidth = right - left
        regionHeight = bottom - top

        requestedScale = None
        if maxWidth is None and maxHeight is None:
            if mag.get('scale') in (1.0, None):
                maxWidth, maxHeight = regionWidth, regionHeight
                requestedScale = 1
            else:
                maxWidth = regionWidth / mag['scale']
                maxHeight = regionHeight / mag['scale']
                requestedScale = mag['scale']
        outWidth, outHeight, calcScale = self._calculateWidthHeight(
            maxWidth, maxHeight, regionWidth, regionHeight)
        if requestedScale is None:
            requestedScale = calcScale
        if (regionWidth == 0 or regionHeight == 0 or outWidth == 0 or
                outHeight == 0):
            return None

        preferredLevel = metadata['levels'] - 1
        # If we are scaling the result, pick the tile level that is at least
        # the resolution we need and is preferred by the tile source.
        if outWidth != regionWidth or outHeight != regionHeight:
            newLevel = self.getPreferredLevel(preferredLevel + int(
                math.ceil(round(math.log(max(float(outWidth) / regionWidth,
                                             float(outHeight) / regionHeight)) /
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
                requestedScale /= factor
        # If an exact magnification was requested and this tile source doesn't
        # have tiles at the appropriate level, indicate that we won't return
        # anything.
        if (magLevel is not None and magLevel != preferredLevel and
                kwargs.get('scale', {}).get('exact')):
            return None

        tile_size = {
            'width': metadata['tileWidth'],
            'height': metadata['tileHeight'],
        }
        tile_overlap = {
            'x': kwargs.get('tile_overlap', {}).get('x', 0) or 0,
            'y': kwargs.get('tile_overlap', {}).get('y', 0) or 0,
            'edges': kwargs.get('tile_overlap', {}).get('edges', False),
            'offset_x': 0,
            'offset_y': 0,
        }
        if not tile_overlap['edges']:
            # offset by half the overlap
            tile_overlap['offset_x'] = tile_overlap['x'] // 2
            tile_overlap['offset_y'] = tile_overlap['y'] // 2
        if 'tile_size' in kwargs:
            tile_size['width'] = kwargs['tile_size'].get(
                'width', kwargs['tile_size'].get('height', tile_size['width']))
            tile_size['height'] = kwargs['tile_size'].get(
                'height', kwargs['tile_size'].get('width', tile_size['height']))
        # Tile size includes the overlap
        tile_size['width'] -= tile_overlap['x']
        tile_size['height'] -= tile_overlap['y']
        if tile_size['width'] <= 0 or tile_size['height'] <= 0:
            raise ValueError('Invalid tile_size or tile_overlap.')

        # If the overlapped tiles don't run over the edge, then the functional
        # size of the region is reduced by the overlap.  This factor is stored
        # in the overlap offset_*.
        xmin = int(left / tile_size['width'])
        xmax = int(math.ceil((float(right) - tile_overlap['offset_x']) /
                             tile_size['width']))
        ymin = int(top / tile_size['height'])
        ymax = int(math.ceil((float(bottom) - tile_overlap['offset_y']) /
                             tile_size['height']))
        tile_overlap.update({'xmin': xmin, 'xmax': xmax,
                             'ymin': ymin, 'ymax': ymax})

        # Use RGB for JPEG, RGBA for PNG
        mode = 'RGBA' if kwargs.get('encoding') in ('PNG',) else 'RGB'

        info = {
            'region': {
                'top': top,
                'left': left,
                'bottom': bottom,
                'right': right,
                'width': regionWidth,
                'height': regionHeight,
            },
            'xmin': xmin,
            'ymin': ymin,
            'xmax': xmax,
            'ymax': ymax,
            'mode': mode,
            'level': preferredLevel,
            'metadata': metadata,
            'output': {
                'width': outWidth,
                'height': outHeight,
            },
            'format': kwargs.get('format', (TILE_FORMAT_PIL, )),
            'encoding': kwargs.get('encoding'),
            'requestedScale': requestedScale,
            'tile_overlap': tile_overlap,
            'tile_position': kwargs.get('tile_position'),
            'tile_size': tile_size,
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
            level: level of the current tile
            level_x, level_y: the tile reference number within the level.
            tile_position: a dictionary of the tile position within the
                    iterator, containing:
                level_x, level_y: the tile reference number within the level.
                region_x, region_y: 0, 0 is the first tile in the full
                    iteration (when not restrictioning the iteration to a
                    single tile).
                position: a 0-based value for the tile within the full
                    iteration.
            iterator_range: a dictionary of the output range of the iterator:
                level_x_min, level_y_min, level_x_max, level_y_max: the tiles
                    that are be included during the full iteration:
                    [layer_x_min, layer_x_max) and [layer_y_min, layer_y_max).
                region_x_max, region_y_max: the number of tiles included during
                    the full iteration.   This is layer_x_max - layer_x_min,
                    layer_y_max - layer_y_min.
                position: the total number of tiles included in the full
                    iteration.  This is region_x_max * region_y_max.
            magnification: magnification of the current tile
            mm_x, mm_y: size of the current tile pixel in millimeters.
            gx, gy - (left, top) coordinate in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum resolution
                pixels.
            tile_overlap: the amount of overlap with neighboring tiles (left,
                top, right, and bottom).  Overlap never extends outside of the
                requested region.
        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom egdes in any case.

        :param iterInfo: tile iterator information.  See _tileIteratorInfo.
        :yields: an iterator that returns a dictionary as listed above.
        """
        regionWidth = iterInfo['region']['width']
        regionHeight = iterInfo['region']['height']
        left = iterInfo['region']['left']
        top = iterInfo['region']['top']
        xmin = iterInfo['xmin']
        ymin = iterInfo['ymin']
        xmax = iterInfo['xmax']
        ymax = iterInfo['ymax']
        level = iterInfo['level']
        metadata = iterInfo['metadata']
        tileSize = iterInfo['tile_size']
        tileOverlap = iterInfo['tile_overlap']
        format = iterInfo['format']
        encoding = iterInfo['encoding']

        logger.debug(
            'Fetching region of an image with a source size of %d x %d; '
            'getting %d tiles',
            regionWidth, regionHeight, (xmax - xmin) * (ymax - ymin))

        # If tile is specified, return at most one tile
        if iterInfo.get('tile_position') is not None:
            tilePos = iterInfo.get('tile_position')
            if isinstance(tilePos, dict):
                if tilePos.get('position') is not None:
                    tilePos = tilePos['position']
                elif 'region_x' in tilePos and 'region_y' in tilePos:
                    tilePos = (tilePos['region_x'] +
                               tilePos['region_y'] * (xmax - xmin))
                elif 'level_x' in tilePos and 'level_y' in tilePos:
                    tilePos = ((tilePos['level_x'] - xmin) +
                               (tilePos['level_y'] - ymin) * (xmax - xmin))
            if tilePos < 0 or tilePos >= (ymax - ymin) * (xmax - xmin):
                xmax = xmin
            else:
                ymin += int(tilePos / (xmax - xmin))
                ymax = ymin + 1
                xmin += int(tilePos % (xmax - xmin))
                xmax = xmin + 1
        mag = self.getMagnificationForLevel(level)
        scale = mag.get('scale', 1.0)
        retile = (tileSize['width'] != metadata['tileWidth'] or
                  tileSize['height'] != metadata['tileHeight'] or
                  tileOverlap['x'] or tileOverlap['y'])
        for y in range(ymin, ymax):
            for x in range(xmin, xmax):
                crop = None
                posX = int(x * tileSize['width'] - tileOverlap['x'] // 2 +
                           tileOverlap['offset_x'] - left)
                posY = int(y * tileSize['height'] - tileOverlap['y'] // 2 +
                           tileOverlap['offset_y'] - top)
                tileWidth = tileSize['width'] + tileOverlap['x']
                tileHeight = tileSize['height'] + tileOverlap['y']
                # crop as needed
                if (posX < 0 or posY < 0 or posX + tileWidth > regionWidth or
                        posY + tileHeight > regionHeight):
                    crop = (max(0, -posX),
                            max(0, -posY),
                            int(min(tileWidth, regionWidth - posX)),
                            int(min(tileHeight, regionHeight - posY)))
                    posX += crop[0]
                    posY += crop[1]
                    tileWidth = crop[2] - crop[0]
                    tileHeight = crop[3] - crop[1]
                overlap = {
                    'left': max(0, x * tileSize['width'] + tileOverlap['offset_x'] - left - posX),
                    'top': max(0, y * tileSize['height'] + tileOverlap['offset_y'] - top - posY),
                }
                overlap['right'] = max(0, tileWidth - tileSize['width'] - overlap['left'])
                overlap['bottom'] = max(0, tileHeight - tileSize['height'] - overlap['top'])
                if tileOverlap['offset_x']:
                    overlap['left'] = 0 if x == tileOverlap['xmin'] else overlap['left']
                    overlap['right'] = 0 if x + 1 == tileOverlap['xmax'] else overlap['right']
                if tileOverlap['offset_y']:
                    overlap['top'] = 0 if y == tileOverlap['ymin'] else overlap['top']
                    overlap['bottom'] = 0 if y + 1 == tileOverlap['ymax'] else overlap['bottom']
                tile = LazyTileDict({
                    'x': x,
                    'y': y,
                    'level': level,
                    'format': format,
                    'encoding': encoding,
                    'crop': crop,
                    'requestedScale': iterInfo['requestedScale'],
                    'retile': retile,
                    'metadata': metadata,
                    'source': self,
                }, {
                    'x': posX + left,
                    'y': posY + top,
                    'width': tileWidth,
                    'height': tileHeight,
                    'level': level,
                    'level_x': x,
                    'level_y': y,
                    'magnification': mag['magnification'],
                    'mm_x': mag['mm_x'],
                    'mm_y': mag['mm_y'],
                    'tile_position': {
                        'level_x': x,
                        'level_y': y,
                        'region_x': x - iterInfo['xmin'],
                        'region_y': y - iterInfo['ymin'],
                        'position': ((x - iterInfo['xmin']) +
                                     (y - iterInfo['ymin']) *
                                     (iterInfo['xmax'] - iterInfo['xmin'])),
                    },
                    'iterator_range': {
                        'level_x_min': iterInfo['xmin'],
                        'level_y_min': iterInfo['ymin'],
                        'level_x_max': iterInfo['xmax'],
                        'level_y_max': iterInfo['ymax'],
                        'region_x_max': iterInfo['xmax'] - iterInfo['xmin'],
                        'region_y_max': iterInfo['ymax'] - iterInfo['ymin'],
                        'position': ((iterInfo['xmax'] - iterInfo['xmin']) *
                                     (iterInfo['ymax'] - iterInfo['ymin']))
                    },
                    'tile_overlap': overlap
                })
                tile['gx'] = tile['x'] * scale
                tile['gy'] = tile['y'] * scale
                tile['gwidth'] = tile['width'] * scale
                tile['gheight'] = tile['height'] * scale
                yield tile

    def _outputTile(self, tile, tileEncoding, x, y, z, pilImageAllowed=False,
                    **kwargs):
        """
        Convert a tile from a PIL image or image in memory to the desired
        encoding.

        :param tile: the tile to convert.
        :param tileEncoding: the current tile encoding.
        :param x: tile x value.  Used for cropping or edge adjustment.
        :param y: tile y value.  Used for cropping or edge adjustment.
        :param z: tile z (level) value.  Used for cropping or edge adjustment.
        :param pilImageAllowed: True if a PIL image may be returned.
        :returns: either a PIL image or a memory object with an image file.
        """
        isEdge = False
        if self.edge:
            sizeX = int(self.sizeX * 2 ** (z - (self.levels - 1)))
            sizeY = int(self.sizeY * 2 ** (z - (self.levels - 1)))
            maxX = (x + 1) * self.tileWidth
            maxY = (y + 1) * self.tileHeight
            isEdge = maxX > sizeX or maxY > sizeY
        if tileEncoding != TILE_FORMAT_PIL:
            if tileEncoding == self.encoding and not isEdge:
                return tile
            tile = PIL.Image.open(BytesIO(tile))
        if isEdge:
            contentWidth = min(self.tileWidth,
                               sizeX - (maxX - self.tileWidth))
            contentHeight = min(self.tileHeight,
                                sizeY - (maxY - self.tileHeight))
            if self.edge in (True, 'crop'):
                tile = tile.crop((0, 0, contentWidth, contentHeight))
            else:
                color = PIL.ImageColor.getcolor(self.edge, tile.mode)
                if contentWidth < self.tileWidth:
                    PIL.ImageDraw.Draw(tile).rectangle(
                        [(contentWidth, 0), (self.tileWidth, contentHeight)],
                        fill=color, outline=None)
                if contentHeight < self.tileHeight:
                    PIL.ImageDraw.Draw(tile).rectangle(
                        [(0, contentHeight), (self.tileWidth, self.tileHeight)],
                        fill=color, outline=None)
        if pilImageAllowed:
            return tile
        output = BytesIO()
        tile.save(
            output, TileOutputPILFormat.get(self.encoding, self.encoding),
            quality=self.jpegQuality, subsampling=self.jpegSubsampling)
        return output.getvalue()

    @classmethod
    def canRead(cls, *args, **kwargs):
        """
        Check if we can read the input.  This takes the same parameters as
        __init__.

        :returns: True if this class can read the input.  False if it cannot.
        """
        return False

    def getMetadata(self):
        mag = self.getNativeMagnification()
        return {
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'magnification': mag['magnification'],
            'mm_x': mag['mm_x'],
            'mm_y': mag['mm_y'],
        }

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, sparseFallback=False):
        raise NotImplementedError()

    def getTileMimeType(self):
        return TileOutputMimeTypes.get(self.encoding, 'image/jpeg')

    @methodcache()
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
            params['output'] = {'maxWidth': width, 'maxHeight': height}
            params.pop('region', None)
            return self.getRegion(**params)
        metadata = self.getMetadata()
        tileData = self.getTile(0, 0, 0)
        image = PIL.Image.open(BytesIO(tileData))
        imageWidth = int(math.floor(
            metadata['sizeX'] * 2 ** -(metadata['levels'] - 1)))
        imageHeight = int(math.floor(
            metadata['sizeY'] * 2 ** -(metadata['levels'] - 1)))
        image = image.crop((0, 0, imageWidth, imageHeight))

        if width or height:
            width, height, calcScale = self._calculateWidthHeight(
                width, height, imageWidth, imageHeight)

            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > imageWidth else PIL.Image.LANCZOS)
        return _encodeImage(image, **kwargs)

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

    def convertRegionScale(self, sourceRegion, sourceScale=None,
                           targetScale=None, targetUnits=None):
        """
        Convert a region from one scale to another.  If the source region's
        units are anything other than pixels, this does nothing.  Otherwise,
        sourceScale must be specified, an a new region is created in the
        targetScale's pixel coordinates.

        :param sourceRegion: a dictionary of optional values which specify the
                part of an image to process.
            left: the left edge (inclusive) of the region to process.
            top: the top edge (inclusive) of the region to process.
            right: the right edge (exclusive) of the region to process.
            bottom: the bottom edge (exclusive) of the region to process.
            width: the width of the region to process.
            height: the height of the region to process.
            units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.
        :param sourceScale: a dictionary of optional values which specify the
                scale of the source region.  Required if the sourceRegion is
                in "mag_pixels" units.
            magnification: the magnification ratio.
            mm_x: the horizontal size of a pixel in millimeters.
            mm_y: the vertical size of a pixel in millimeters.
        :param targetScale: a dictionary of optional values which specify the
                scale of the target region.  Required in targetUnits is in
                "mag_pixels" units.
            magnification: the magnification ratio.
            mm_x: the horizontal size of a pixel in millimeters.
            mm_y: the vertical size of a pixel in millimeters.
        :param targetUnits: if not None, convert the region to these units.
            Otherwise, the units are will either be the sourceRegion units if
            those are not "mag_pixels" or base_pixels.  If "mag_pixels", the
            targetScale must be specified.
        """
        units = sourceRegion.get('units')
        if units not in TileInputUnits:
            raise ValueError('Invalid units "%s"' % units)
        units = TileInputUnits[units]
        if targetUnits is not None:
            if targetUnits not in TileInputUnits:
                raise ValueError('Invalid units "%s"' % targetUnits)
            targetUnits = TileInputUnits[targetUnits]
        if (units != 'mag_pixels' and (
                targetUnits is None or targetUnits == units)):
            return sourceRegion
        magArgs = (sourceScale or {}).copy()
        magArgs['rounding'] = None
        magLevel = self.getLevelForMagnification(**magArgs)
        mag = self.getMagnificationForLevel(magLevel)
        metadata = self.getMetadata()
        # Get region in base pixels
        left, top, right, bottom = self._getRegionBounds(
            metadata, desiredMagnification=mag, **sourceRegion)
        # If requested, convert region to targetUnits
        magArgs = (targetScale or {}).copy()
        magArgs['rounding'] = None
        magLevel = self.getLevelForMagnification(**magArgs)
        desiredMagnification = self.getMagnificationForLevel(magLevel)

        scaleX = scaleY = 1
        if targetUnits == 'fraction':
            scaleX = metadata['sizeX']
            scaleY = metadata['sizeY']
        elif targetUnits == 'mag_pixels':
            if not (desiredMagnification or {}).get('scale'):
                raise ValueError('No magnification to use for units')
            scaleX = scaleY = desiredMagnification['scale']
        elif targetUnits == 'mm':
            if (not (desiredMagnification or {}).get('scale') or
                    not (desiredMagnification or {}).get('mm_x') or
                    not (desiredMagnification or {}).get('mm_y')):
                raise ValueError('No mm_x or mm_y to use for units')
            scaleX = (desiredMagnification['scale'] /
                      desiredMagnification['mm_x'])
            scaleY = (desiredMagnification['scale'] /
                      desiredMagnification['mm_y'])
        left = float(left) / scaleX
        right = float(right) / scaleX
        top = float(top) / scaleY
        bottom = float(bottom) / scaleY
        targetRegion = {
            'left': left,
            'top': top,
            'right': right,
            'bottom': bottom,
            'width': right - left,
            'height': bottom - top,
            'units': TileInputUnits[targetUnits],
        }
        # Reduce region information to match what was supplied
        for key in ('left', 'top', 'right', 'bottom', 'width', 'height'):
            if key not in sourceRegion:
                del targetRegion[key]
        return targetRegion

    def getRegion(self, format=(TILE_FORMAT_IMAGE, ), **kwargs):
        """
        Get a rectangular region from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, the original size of
        the highest resolution level is used.  If both are given, the returned
        image will be no larger than either size.

        :param format: the desired format or a tuple of allowed formats.
            Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
            TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding may be
            specified.
        :param **kwargs: optional arguments.  Some options are region, output,
            encoding, jpegQuality, jpegSubsampling.  See tileIterator.
        :returns: regionData, formatOrRegionMime: the image data and either the
            mime type, if the format is TILE_FORMAT_IMAGE, or the format.
        """
        if 'tile_position' in kwargs:
            kwargs = kwargs.copy()
            kwargs.pop('tile_position', None)
        iterInfo = self._tileIteratorInfo(**kwargs)
        if iterInfo is None:
            # In PIL 3.4.2, you can't directly create a 0 sized image.  It was
            # easier to do this before:
            #  image = PIL.Image.new('RGB', (0, 0))
            image = PIL.Image.new('RGB', (1, 1)).crop((0, 0, 0, 0))
            return _encodeImage(image, format=format, **kwargs)
        regionWidth = iterInfo['region']['width']
        regionHeight = iterInfo['region']['height']
        top = iterInfo['region']['top']
        left = iterInfo['region']['left']
        mode = iterInfo['mode']
        outWidth = iterInfo['output']['width']
        outHeight = iterInfo['output']['height']
        # We can construct an image using PIL.Image.new:
        #   image = PIL.Image.new('RGB', (regionWidth, regionHeight))
        # but, for large images (larger than 4 Megapixels), PIL allocates one
        # memory region per line.  Although it frees this, the memory manager
        # often fails to reuse these smallish pieces.  By allocating the data
        # memory ourselves in one block, the memory manager does a better job.
        # Furthermode, if the source buffer isn't in RGBA format, the memory is
        # still often inaccessible.
        try:
            image = PIL.Image.frombuffer(
                mode, (regionWidth, regionHeight),
                # PIL will reallocate buffers that aren't in 'raw', RGBA, 0, 1.
                # See PIL documentation and code for more details.
                b'\x00' * (regionWidth * regionHeight * 4), 'raw', 'RGBA', 0, 1)
        except MemoryError:
            raise TileSourceException(
                'Insufficient memory to get region of %d x %d pixels.' % (
                    regionWidth, regionHeight))
        for tile in self._tileIterator(iterInfo):
            # Add each tile to the image.  PIL crops these if they are off the
            # edge.
            image.paste(tile['tile'], (tile['x'] - left, tile['y'] - top))
        # Scale if we need to
        outWidth = int(math.floor(outWidth))
        outHeight = int(math.floor(outHeight))
        if outWidth != regionWidth or outHeight != regionHeight:
            image = image.resize(
                (outWidth, outHeight),
                PIL.Image.BICUBIC if outWidth > regionWidth else
                PIL.Image.LANCZOS)
        return _encodeImage(image, format=format, **kwargs)

    def getRegionAtAnotherScale(self, sourceRegion, sourceScale=None,
                                targetScale=None, targetUnits=None, **kwargs):
        """
        This takes the same parameters and returns the same results as
        getRegion, except instead of region and scale, it takes sourceRegion,
        sourceScale, targetScale, and targetUnits.  These parameters are the
        same as convertRegionScale.  See those two functions for parameter
        definitions.
        """
        for key in ('region', 'scale'):
            if key in kwargs:
                raise TypeError('getRegionAtAnotherScale() got an unexpected '
                                'keyword argument of \'%s\'' % key)
        region = self.convertRegionScale(sourceRegion, sourceScale,
                                         targetScale, targetUnits)
        return self.getRegion(region=region, scale=targetScale, **kwargs)

    def getNativeMagnification(self):
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
        mag = self.getNativeMagnification()

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
                                 mm_x=None, mm_y=None, rounding='round',
                                 **kwargs):
        """
        Get the level for a specific magnifcation or pixel size.  If the
        magnification is unknown or no level is sufficient resolution, and an
        exact match is not requested, the highest level will be returned.
          If none of magnification, mm_x, and mm_y are specified, the maximum
        level is returned.  If more than one of these values is given, an
        average of those given will be used (exact will require all of them to
        match).

        :param magnification: the magnification ratio.
        :param exact: if True, only a level that matches exactly will be
            returned.
        :param mm_x: the horizontal size of a pixel in millimeters.
        :param mm_y: the vertical size of a pixel in millimeters.
        :param rounding: if False, a fractional level may be returned.  If
            'ceil' or 'round', that function is used to convert the level to an
            integer (the exact flag still applies).  If None, the level is not
            cropped to the actual image's level range.
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
            return mag['level']
        if exact:
            if any(int(ratio) != ratio or ratio != ratios[0]
                   for ratio in ratios):
                return None
        ratio = round(sum(ratios) / len(ratios), 4)
        level = mag['level'] + ratio
        if rounding:
            level = int(math.ceil(level) if rounding == 'ceil' else
                        round(level))
        if (exact and (level > mag['level'] or level < 0) or
                (rounding == 'ceil' and level > mag['level'])):
            return None
        if rounding is not None:
            level = max(0, min(mag['level'], level))
        return level

    def tileIterator(self, format=(TILE_FORMAT_PIL, ), resample=False,
                     **kwargs):
        """
        Iterate on all tiles in the specifed region at the specified scale.
        Each tile is returned as part of a dictionary that includes
            x, y: (left, top) coordinates in current magnification pixels
            width, height: size of current tile incurrent magnification pixels
            tile: cropped tile image
            format: format of the tile
            level: level of the current tile
            level_x, level_y: the tile reference number within the level.
            magnification: magnification of the current tile
            mm_x, mm_y: size of the current tile pixel in millimeters.
            gx, gy: (left, top) coordinate in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum resolution
                pixels.
        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom egdes in any case.  If an exact
        magnification or scale is requested, no tiles will be returned unless
        allowInterpolation is true.

        :param format: the desired format or a tuple of allowed formats.
            Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
            TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding must be
            specified.
        :param resample: If True or one of PIL.Image.NEAREST, LANCZOS,
            BILINEAR, or BICUBIC to resample tiles that are not the target
            output size.  Tiles that are resampled may have non-integer x, y,
            width, and height values, and will have an additional dictionary
            entries of:
                scaled: the scaling factor that was applied (less than 1 is
                    downsampled).
                tile_x, tile_y: (left, top) coordinates before scaling
                tile_width, tile_height: size of the current tile before
                    scaling.
            Note that scipy.misc.imresize uses PIL internally.
        :param region: a dictionary of optional values which specify the part
                of the image to process.
            left: the left edge (inclusive) of the region to process.
            top: the top edge (inclusive) of the region to process.
            right: the right edge (exclusive) of the region to process.
            bottom: the bottom edge (exclusive) of the region to process.
            width: the width of the region to process.
            height: the height of the region to process.
            units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.
        :param output: a dictionary of optional values which specify the size
                of the output.
            maxWidth: maximum width in pixels.  If either maxWidth or maxHeight
                is specified, magnfication, mm_x, and mm_y are ignored.
            maxHeight: maximum height in pixels.
        :param scale: a dictionary of optional values which specify the scale
                of the region and / or output.  This applies to region if
                pixels or mm are used for inits.  It applies to output if
                neither output maxWidth nor maxHeight is specified.  It
            magnification: the magnification ratio.  Only used is maxWidth and
                maxHeight are not specified or None.
            mm_x: the horizontal size of a pixel in millimeters.
            mm_y: the vertical size of a pixel in millimeters.
            exact: if True, only a level that matches exactly will be returned.
                This is only applied if magnification, mm_x, or mm_y is used.
        :param tile_position: if present, either a number to only yield the
            (tile_position)th tile [0 to (xmax - min) * (ymax - ymin)) that the
            iterator would yield, or a dictionary of {region_x, region_y} to
            yield that tile, where 0, 0 is the first tile yielded, and
            xmax - xmin - 1, ymax - ymin - 1 is the last tile yielded, or a
            dictionary of {level_x, level_y} to yield that specific tile if it
            is in the region.
        :param tile_size: if present, retile the output to the specified tile
                size.  If only width or only height is specified, the resultant
                tiles will be square.  This is a dictionary containing at least
                one of:
            width: the desired tile width.
            height: the desired tile height.
        :param tile_overlap: if present, retile the output adding a symmetric
                overlap to the tiles.  If either x or y is not specified, it
                defaults to zero.  The overlap does not change the tile size,
                only the stride of the tiles.  This is a dictionary containing:
            x: the horizontal overlap in pixels.
            y: the vertical overlap in pixels.
            edges: if True, then the edge tiles will exclude the overlap
                distance.  If unset or False, the edge tiles are full size.
                    The overlap is conceptually split between the two sides of
                the tile.  This is only relevant to where overlap is reported
                or if edges is True
                    As an example, suppose an image that is 8 pixels across
                (01234567) and a tile size of 5 is requested with an overlap of
                4.  If the edges option is False (the default), the following
                tiles are returned: 01234, 12345, 23456, 34567.  Each tile
                reports its overlap, and the non-overlapped area of each tile
                is 012, 3, 4, 567.  If the edges option is True, the tiles
                returned are: 012, 0123, 01234, 12345, 23456, 34567, 4567, 567,
                with the non-overlapped area of each as 0, 1, 2, 3, 4, 5, 6, 7.
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
        iterFormat = format if resample in (False, None) else (
            TILE_FORMAT_PIL, )
        iterInfo = self._tileIteratorInfo(format=iterFormat, **kwargs)
        if not iterInfo:
            return
        # check if the desired scale is different from the actual scale and
        # resampling is needed.  Ignore small scale differences.
        if (resample in (False, None) or
                round(iterInfo['requestedScale'], 2) == 1.0):
            resample = None
        for tile in self._tileIterator(iterInfo):
            tile.setFormat(format, resample, kwargs)
            yield tile

    def tileIteratorAtAnotherScale(self, sourceRegion, sourceScale=None,
                                   targetScale=None, targetUnits=None,
                                   **kwargs):
        """
        This takes the same parameters and returns the same results as
        tileIterator, except instead of region and scale, it takes
        sourceRegion, sourceScale, targetScale, and targetUnits.  These
        parameters are the same as convertRegionScale.  See those two functions
        for parameter definitions.
        """
        for key in ('region', 'scale'):
            if key in kwargs:
                raise TypeError('getRegionAtAnotherScale() got an unexpected '
                                'keyword argument of \'%s\'' % key)
        region = self.convertRegionScale(sourceRegion, sourceScale,
                                         targetScale, targetUnits)
        return self.tileIterator(region=region, scale=targetScale, **kwargs)

    def getSingleTile(self, *args, **kwargs):
        """
        Return any single tile from an iterator.  This takes exactly the same
        parameters as tileIterator.  Use tile_position to get a specific tile,
        otherwise the first tile is returned.

        :return: a tile dictionary or None.
        """
        return next(self.tileIterator(*args, **kwargs), None)

    def getSingleTileAtAnotherScale(self, *args, **kwargs):
        """
        Return any single tile from a rescaled iterator.  This takes exactly
        the same parameters as tileIteratorAtAnotherScale.  Use tile_position
        to get a specific tile, otherwise the first tile is returned.

        :return: a tile dictionary or None.
        """
        return next(self.tileIteratorAtAnotherScale(*args, **kwargs), None)


class FileTileSource(TileSource):

    def __init__(self, path, *args, **kwargs):
        super(FileTileSource, self).__init__(*args, **kwargs)
        self.largeImagePath = path

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            args[0], kwargs.get('encoding'), kwargs.get('jpegQuality'),
            kwargs.get('jpegSubsampling'), kwargs.get('edge'))

    def getState(self):
        return self._getLargeImagePath() + ',' + str(
            self.encoding) + ',' + str(self.jpegQuality) + ',' + str(
            self.jpegSubsampling) + ',' + str(self.edge)

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

        @staticmethod
        def getLRUHash(*args, **kwargs):
            return strhash(
                str(args[0]['largeImage']['fileId']), args[0]['updated'],
                kwargs.get('encoding'), kwargs.get('jpegQuality'),
                kwargs.get('jpegSubsampling'), kwargs.get('edge'))

        def getState(self):
            return str(self.item['largeImage']['fileId']) + ',' + str(
                self.item['updated']) + ',' + str(
                self.encoding) + ',' + str(self.jpegQuality) + ',' + str(
                self.jpegSubsampling) + ',' + str(self.edge)

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
