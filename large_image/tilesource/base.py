# -*- coding: utf-8 -*-

import json
import math
import numpy
import PIL
import PIL.Image
import PIL.ImageColor
import PIL.ImageDraw
import random
import six
import threading
from collections import defaultdict
from six import BytesIO

from ..cache_util import getTileCache, strhash, methodcache
from ..constants import SourcePriority, \
    TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL, \
    TileOutputMimeTypes, TileOutputPILFormat, TileInputUnits
from .. import config
from .. import exceptions


# Turn off decompression warning check
PIL.Image.MAX_IMAGE_PIXELS = None


def _encodeImage(image, encoding='JPEG', jpegQuality=95, jpegSubsampling=0,
                 format=(TILE_FORMAT_IMAGE, ), tiffCompression='raw',
                 **kwargs):
    """
    Convert a PIL or numpy image into raw output bytes and a mime type.

    :param image: a PIL image.
    :param encoding: a valid PIL encoding (typically 'PNG' or 'JPEG').  Must
        also be in the TileOutputMimeTypes map.
    :param jpegQuality: the quality to use when encoding a JPEG.
    :param jpegSubsampling: the subsampling level to use when encoding a JPEG.
    :param format: the desired format or a tuple of allowed formats.  Formats
        are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY, TILE_FORMAT_IMAGE).
    :param tiffCompression: the compression format to use when encoding a TIFF.
    :returns:
        imageData: the image data in the specified format and encoding.
        imageFormatOrMimeType: the image mime type if the format is
            TILE_FORMAT_IMAGE, or the format of the image data if it is
            anything else.
    """
    if not isinstance(format, (tuple, set, list)):
        format = (format, )
    imageData = image
    imageFormatOrMimeType = TILE_FORMAT_PIL
    if TILE_FORMAT_NUMPY in format:
        imageData, _ = _imageToNumpy(image)
        imageFormatOrMimeType = TILE_FORMAT_NUMPY
    elif TILE_FORMAT_PIL in format:
        imageData = _imageToPIL(image)
        imageFormatOrMimeType = TILE_FORMAT_PIL
    elif TILE_FORMAT_IMAGE in format:
        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        imageFormatOrMimeType = TileOutputMimeTypes[encoding]
        image = _imageToPIL(image)
        if image.width == 0 or image.height == 0:
            imageData = b''
        else:
            encoding = TileOutputPILFormat.get(encoding, encoding)
            output = BytesIO()
            params = {}
            if encoding == 'JPEG' and image.mode not in ('L', 'RGB'):
                image = image.convert('RGB' if image.mode != 'LA' else 'L')
            if encoding == 'JPEG':
                params['quality'] = jpegQuality
                params['subsampling'] = jpegSubsampling
            elif encoding == 'TIFF':
                params['compression'] = {
                    'none': 'raw',
                    'lzw': 'tiff_lzw',
                    'deflate': 'tiff_adobe_deflate',
                }.get(tiffCompression, tiffCompression)
            image.save(output, encoding, **params)
            imageData = output.getvalue()
    return imageData, imageFormatOrMimeType


def _imageToPIL(image, setMode=None):
    """
    Convert an image in PIL, numpy, or image file format to a PIL image.

    :param image: input image.
    :param setMode: if specified, the output image is converted to this mode.
    :returns: a PIL image.
    """
    if isinstance(image, numpy.ndarray):
        mode = 'L'
        if len(image.shape) == 3:
            # Fallback for hyperspectral data to just use the first three bands
            if image.shape[2] > 4:
                image = image[:, :, :3]
            mode = ['L', 'LA', 'RGB', 'RGBA'][image.shape[2] - 1]
        if len(image.shape) == 3 and image.shape[2] == 1:
            image = numpy.resize(image, image.shape[:2])
        if image.dtype == numpy.uint16:
            image = numpy.floor_divide(image, 256).astype(numpy.uint8)
        elif image.dtype != numpy.uint8:
            image = image.astype(numpy.uint8)
        image = PIL.Image.fromarray(image, mode)
    elif not isinstance(image, PIL.Image.Image):
        image = PIL.Image.open(BytesIO(image))
    if setMode is not None and image.mode != setMode:
        image = image.convert(setMode)
    return image


def _imageToNumpy(image):
    """
    Convert an image in PIL, numpy, or image file format to a numpy array.  The
    output numpy array always has three dimensions.

    :param image: input image.
    :returns: a numpy array and a target PIL image mode.
    """
    if not isinstance(image, numpy.ndarray):
        if not isinstance(image, PIL.Image.Image):
            image = PIL.Image.open(BytesIO(image))
        if image.mode not in ('L', 'LA', 'RGB', 'RGBA'):
            image.convert('RGBA')
        mode = image.mode
        image = numpy.asarray(image)
    else:
        if len(image.shape) == 3:
            mode = ['L', 'LA', 'RGB', 'RGBA'][(image.shape[2] - 1) if image.shape[2] <= 4 else 3]
        else:
            mode = 'L'
    if len(image.shape) == 2:
        image = numpy.resize(image, (image.shape[0], image.shape[1], 1))
    return image, mode


def _letterboxImage(image, width, height, fill):
    """
    Given a PIL image, width, height, and fill color, letterbox or pillarbox
    the image to make it the specified dimensions.  The image is never
    cropped.  The original image will be returned if no action is needed.

    :param image: the source image.
    :param width: the desired width in pixels.
    :param height: the desired height in pixels.
    :param fill: a fill color.
    """
    if ((image.width >= width and image.height >= height) or
            not fill or str(fill).lower() == 'none'):
        return image
    color = PIL.ImageColor.getcolor(fill, image.mode)
    width = max(width, image.width)
    height = max(height, image.height)
    result = PIL.Image.new(image.mode, (width, height), color)
    result.paste(image, (int((width - image.width) / 2), int((height - image.height) / 2)))
    return result


def etreeToDict(t):
    """
    Convert an xml etree to a nested dictionary without schema names in the
    keys.

    @param t: an etree.
    @returns: a python dictionary with the results.
    """
    # Remove schema
    tag = t.tag.split('}', 1)[1] if t.tag.startswith('{') else t.tag
    d = {tag: {}}
    children = list(t)
    if children:
        entries = defaultdict(list)
        for entry in map(etreeToDict, children):
            for k, v in six.iteritems(entry):
                entries[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v
                   for k, v in six.iteritems(entries)}}

    if t.attrib:
        d[tag].update({(k.split('}', 1)[1] if k.startswith('{') else k): v
                       for k, v in six.iteritems(t.attrib)})
    text = (t.text or '').strip()
    if text and len(d[tag]):
        d[tag]['text'] = text
    elif text:
        d[tag] = text
    return d


def nearPowerOfTwo(val1, val2, tolerance=0.02):
    """
    Check if two values are different by nearly a power of two.

    :param val1: the first value to check.
    :param val2: the second value to check.
    :param tolerance: the maximum difference in the log2 ratio's mantissa.
    :return: True if the valeus are nearly a power of two different from each
        other; false otherwise.
    """
    # If one or more of the values is zero or they have different signs, then
    # return False
    if val1 * val2 <= 0:
        return False
    log2ratio = math.log(float(val1) / float(val2)) / math.log(2)
    # Compare the mantissa of the ratio's log2 value.
    return abs(log2ratio - round(log2ratio)) < tolerance


class LazyTileDict(dict):
    """
    Tiles returned from the tile iterator and dictionaries of information with
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
        self.frame = tileInfo.get('frame')
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
        self.width = self['width']
        self.height = self['height']
        return result

    def setFormat(self, format, resample=False, imageKwargs=None):
        """
        Set a more restrictive output format for a tile, possibly also resizing
        it via resampling.  If this is not called, the tile may either be
        returned as one of the specified formats or as a PIL image.

        :param format: a tuple or list of allowed formats.  Formats are members
            of TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
        :param resample: if not False or None, allow resampling.  Once turned
            on, this cannot be turned off on the tile.
        :param imageKwargs: additional parameters that should be passed to
            _encodeImage.
        """
        # If any parameters are changed, mark the tile as not loaded, so that
        # referring to a deferredKey will reload the image.
        self.alwaysAllowPIL = False
        if format is not None and format != self.format:
            self.format = format
            self.loaded = False
        if (resample not in (False, None) and not self.resample and
                self.requestedScale and round(self.requestedScale, 2) != 1.0):
            self.resample = resample
            self['scaled'] = 1.0 / self.requestedScale
            self['tile_x'] = self.get('tile_x', self['x'])
            self['tile_y'] = self.get('tile_y', self['y'])
            self['tile_width'] = self.get('tile_width', self.width)
            self['tile_height'] = self.get('tile_width', self.height)
            if self.get('magnification', None):
                self['tile_magnification'] = self.get('tile_magnification', self['magnification'])
            self['tile_mm_x'] = self.get('mm_x')
            self['tile_mm_y'] = self.get('mm_y')
            self['x'] = float(self['tile_x'])
            self['y'] = float(self['tile_y'])
            # Add provisional width and height
            if self.resample not in (False, None) and self.requestedScale:
                self['width'] = max(1, int(
                    self['tile_width'] / self.requestedScale))
                self['height'] = max(1, int(
                    self['tile_height'] / self.requestedScale))
                if self.get('tile_magnification', None):
                    self['magnification'] = self['tile_magnification'] / self.requestedScale
                if self.get('tile_mm_x', None):
                    self['mm_x'] = self['tile_mm_x'] * self.requestedScale
                if self.get('tile_mm_y', None):
                    self['mm_y'] = self['tile_mm_y'] * self.requestedScale
            # If we can resample the tile, many parameters may change once the
            # image is loaded.  Don't include width and height in this list;
            # the provisional values are sufficient.
            self.deferredKeys = ('tile', 'format')
            self.loaded = False
        if imageKwargs is not None:
            self.imageKwargs = imageKwargs
            self.loaded = False

    def _retileTile(self):
        """
        Given the tile information, create a numpy array and merge multiple
        tiles together to form a tile of a different size.
        """
        retile = None
        xmin = int(max(0, self['x'] // self.metadata['tileWidth']))
        xmax = int((self['x'] + self.width - 1) // self.metadata['tileWidth'] + 1)
        ymin = int(max(0, self['y'] // self.metadata['tileHeight']))
        ymax = int((self['y'] + self.height - 1) // self.metadata['tileHeight'] + 1)
        for x in range(xmin, xmax):
            for y in range(ymin, ymax):
                tileData = self.source.getTile(
                    x, y, self.level,
                    numpyAllowed='always', sparseFallback=True, frame=self.frame)
                tileData, _ = _imageToNumpy(tileData)
                if retile is None:
                    retile = numpy.zeros(
                        (self.height, self.width) if len(tileData.shape) == 2 else
                        (self.height, self.width, tileData.shape[2]),
                        dtype=tileData.dtype)
                x0 = int(x * self.metadata['tileWidth'] - self['x'])
                y0 = int(y * self.metadata['tileHeight'] - self['y'])
                if x0 < 0:
                    tileData = tileData[:, -x0:]
                    x0 = 0
                if y0 < 0:
                    tileData = tileData[-y0:, :]
                    y0 = 0
                tileData = tileData[:min(tileData.shape[0], self.height - y0),
                                    :min(tileData.shape[1], self.width - x0)]
                retile[y0:y0 + tileData.shape[0], x0:x0 + tileData.shape[1]] = tileData
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
                    pilImageAllowed=True, numpyAllowed=True,
                    sparseFallback=True, frame=self.frame)
                if self.crop:
                    tileData, _ = _imageToNumpy(tileData)
                    tileData = tileData[self.crop[1]:self.crop[3], self.crop[0]:self.crop[2]]
            else:
                tileData = self._retileTile()

            pilData = _imageToPIL(tileData)

            # resample if needed
            if self.resample not in (False, None) and self.requestedScale:
                self['width'] = max(1, int(
                    pilData.size[0] / self.requestedScale))
                self['height'] = max(1, int(
                    pilData.size[1] / self.requestedScale))
                pilData = tileData = pilData.resize(
                    (self['width'], self['height']),
                    resample=PIL.Image.LANCZOS if self.resample is True else self.resample)

            tileFormat = (TILE_FORMAT_PIL if isinstance(tileData, PIL.Image.Image)
                          else (TILE_FORMAT_NUMPY if isinstance(tileData, numpy.ndarray)
                                else TILE_FORMAT_IMAGE))
            tileEncoding = None if tileFormat != TILE_FORMAT_IMAGE else (
                'JPEG' if tileData[:3] == b'\xff\xd8\xff' else
                'PNG' if tileData[:4] == b'\x89PNG' else
                'TIFF' if tileData[:4] == b'II\x2a\x00' else
                None)
            # Reformat the image if required
            if (not self.alwaysAllowPIL or
                    (TILE_FORMAT_NUMPY in self.format and isinstance(tileData, numpy.ndarray))):
                if (tileFormat in self.format and (tileFormat != TILE_FORMAT_IMAGE or (
                        tileEncoding and
                        tileEncoding == self.imageKwargs.get('encoding', self.encoding)))):
                    # already in an acceptable format
                    pass
                elif TILE_FORMAT_NUMPY in self.format:
                    tileData, _ = _imageToNumpy(tileData)
                    tileFormat = TILE_FORMAT_NUMPY
                elif TILE_FORMAT_PIL in self.format:
                    tileData = pilData
                    tileFormat = TILE_FORMAT_PIL
                elif TILE_FORMAT_IMAGE in self.format:
                    tileData, mimeType = _encodeImage(
                        tileData, **self.imageKwargs)
                    tileFormat = TILE_FORMAT_IMAGE
                if tileFormat not in self.format:
                    raise exceptions.TileSourceException(
                        'Cannot yield tiles in desired format %r' % (
                            self.format, ))
            else:
                tileData = pilData
                tileFormat = TILE_FORMAT_PIL

            self['tile'] = tileData
            self['format'] = tileFormat
        return super(LazyTileDict, self).__getitem__(key, *args, **kwargs)


class TileSource(object):
    name = None
    # extensions is a dictionary of known file extensions and the
    # SourcePriority given to each.  It must contain a None key with a priority
    # for the tile source when the extension does not match.
    extensions = {
        None: SourcePriority.FALLBACK
    }
    # mimeTypes are common mime-types handleds by the source.  They can be used
    # in place of or in additional to extensions
    mimeTypes = {
        None: SourcePriority.FALLBACK
    }

    def __init__(self, encoding='JPEG', jpegQuality=95, jpegSubsampling=0,
                 tiffCompression='raw', edge=False, style=None, *args,
                 **kwargs):
        """
        Initialize the tile class.

        :param jpegQuality: when serving jpegs, use this quality.
        :param jpegSubsampling: when serving jpegs, use this subsampling (0 is
            full chroma, 1 is half, 2 is quarter).
        :param encoding: 'JPEG', 'PNG', or 'TIFF'.
        :param edge: False to leave edge tiles whole, True or 'crop' to crop
            edge tiles, otherwise, an #rrggbb color to fill edges.
        :param tiffCompression: the compression format to use when encoding a
            TIFF.
        :param style: if None, use the default style for the file.  Otherwise,
            this is a string with a json-encoded dictionary.  The style can
            contain the following keys:
                band: if -1 or None, and if style is specified at all, the
                    greyscale value is used.  Otherwise, a 1-based numerical
                    index into the channels of the image or a string that
                    matches the interpretation of the band ('red', 'green',
                    'blue', 'gray', 'alpha').  Note that 'gray' on an RGB or
                    RGBA image will use the green band.
                min: the value to map to the first palette value.  Defaults to
                    0.  'auto' to use 0 if the reported minimum and maximum of
                    the band are between [0, 255] or use the reported minimum
                    otherwise.  'min' or 'max' to always uses the reported
                    minimum or maximum.
                max: the value to map to the last palette value.  Defaults to
                    255.  'auto' to use 0 if the reported minimum and maximum
                    of the band are between [0, 255] or use the reported
                    maximum otherwise.  'min' or 'max' to always uses the
                    reported minimum or maximum.
                palette: a list of two or more color strings, where color
                    strings are of the form #RRGGBB, #RRGGBBAA, #RGB, #RGBA.
                nodata: the value to use for missing data.  null or unset to
                    not use a nodata value.
                composite: either 'lighten' or 'multiply'.  Defaults to
                    'lighten' for all except the alpha band.
                clamp: either True to clamp values outside of the [min, max]
                    to the ends of the palette or False to make outside values
                    transparent.
            Alternately, the style object can contain a single key of 'bands',
            which has a value which is a list of style dictionaries as above,
            excepting that each must have a band that is not -1.  Bands are
            composited in the order listed.
        """
        self.cache, self.cache_lock = getTileCache()

        self.tileWidth = None
        self.tileHeight = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None
        self._styleLock = threading.RLock()
        self._bandRanges = {}

        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)

        self.encoding = encoding
        self.jpegQuality = int(jpegQuality)
        self.jpegSubsampling = int(jpegSubsampling)
        self.tiffCompression = tiffCompression
        self.edge = edge
        self._jsonstyle = style
        if style:
            try:
                self.style = json.loads(style)
                if not isinstance(self.style, dict):
                    raise TypeError
            except TypeError:
                raise exceptions.TileSourceException('Style is not a valid json object.')

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            kwargs.get('encoding', 'JPEG'), kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0), kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False), kwargs.get('style', None))

    def getState(self):
        return '%s,%s,%s,%s,%s,%s' % (
            self.encoding,
            self.jpegQuality,
            self.jpegSubsampling,
            self.tiffCompression,
            self.edge,
            self._jsonstyle)

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
            scale = float(regionHeight) / height
            width = max(1, int(regionWidth * height / regionHeight))
        else:
            scale = float(regionWidth) / width
            height = max(1, int(regionHeight * width / regionWidth))
        return width, height, scale

    def _scaleFromUnits(self, metadata, units, desiredMagnification, **kwargs):
        """
        Get scaling parameters based on the source metadata and specified
        units.

        :param metadata: the metadata associated with this source.
        :param units: the units used for the scale.
        :param desiredMagnification: the output from getMagnificationForLevel
            for the desired magnification used to convert mag_pixels and mm.
        :param **kwargs: optional parameters.
        :returns: (scaleX, scaleY) scaling parameters in the horizontal and
            vertical directions.
        """
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
                desiredMagnification = self.getNativeMagnification().copy()
                desiredMagnification['scale'] = 1.0
            if (not (desiredMagnification or {}).get('scale') or
                    not (desiredMagnification or {}).get('mm_x') or
                    not (desiredMagnification or {}).get('mm_y')):
                raise ValueError('No mm_x or mm_y to use for units')
            scaleX = (desiredMagnification['scale'] /
                      desiredMagnification['mm_x'])
            scaleY = (desiredMagnification['scale'] /
                      desiredMagnification['mm_y'])
        elif units in ('base_pixels', None):
            pass
        else:
            raise ValueError('Invalid units %r' % units)
        return scaleX, scaleY

    def _getRegionBounds(self, metadata, left=None, top=None, right=None,
                         bottom=None, width=None, height=None, units=None,
                         desiredMagnification=None, cropToImage=True,
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
            for the desired magnification used to convert mag_pixels and mm.
        :param cropToImage: if True, don't return region coordinates outside of
            the image.
        :param **kwargs: optional parameters.  These are passed to
            _scaleFromUnits and may include unitsWH.
        :returns: left, top, right, bottom bounds in pixels.
        """
        if units not in TileInputUnits:
            raise ValueError('Invalid units %r' % units)
        # Convert units to max-resolution pixels
        units = TileInputUnits[units]
        scaleX, scaleY = self._scaleFromUnits(metadata, units, desiredMagnification, **kwargs)
        if kwargs.get('unitsWH'):
            if kwargs['unitsWH'] not in TileInputUnits:
                raise ValueError('Invalid units %r' % kwargs['unitsWH'])
            scaleW, scaleH = self._scaleFromUnits(
                metadata, TileInputUnits[kwargs['unitsWH']], desiredMagnification, **kwargs)
            # if unitsWH is specified, prefer width and height to right and
            # bottom
            if left is not None and right is not None and width is not None:
                right = None
            if top is not None and bottom is not None and height is not None:
                bottom = None
        else:
            scaleW, scaleH = scaleX, scaleY
        region = {'left': left, 'top': top, 'right': right,
                  'bottom': bottom, 'width': width, 'height': height}
        region = {key: region[key] for key in region if region[key] is not None}
        for key, scale in (
                ('left', scaleX), ('right', scaleX), ('width', scaleW),
                ('top', scaleY), ('bottom', scaleY), ('height', scaleH)):
            if key in region and scale and scale != 1:
                region[key] = region[key] * scale
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
        if cropToImage:
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
        specified, magnification, mm_x, and/or mm_y are used to determine the
        size.  If none of those are specified, the original maximum resolution
        is returned.

        :param format: a tuple of allowed formats.  Formats are members of
            TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
            Otherwise, TILE_FORMAT_NUMPY is returned.
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
            unitsWH: if not specified, this is the same as `units`.  Otherwise,
                these units will be used for the width and height if specified.
        :param output: a dictionary of optional values which specify the size
                of the output.
            maxWidth: maximum width in pixels.
            maxHeight: maximum height in pixels.
        :param scale: a dictionary of optional values which specify the scale
                of the region and / or output.  This applies to region if
                pixels or mm are used for units.  It applies to output if
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
            jpegQuality, jpegSubsampling, tiffCompression, frame.
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
                    this is different that region width and region height, then
                    the original request was asking for a different scale than
                    is being delivered.
            frame: the frame value for the base image.
            format: a tuple of allowed output formats.
            encoding: if the output format is TILE_FORMAT_IMAGE, the desired
                encoding.
            requestedScale: the scale needed to convert from the region width
                and height to the output width and height.
        """
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if ((maxWidth is not None and
                (not isinstance(maxWidth, six.integer_types) or maxWidth < 0)) or
                (maxHeight is not None and
                 (not isinstance(maxHeight, six.integer_types) or maxHeight < 0))):
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
        requestedScale = calcScale if requestedScale is None else requestedScale
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
            'x': int(kwargs.get('tile_overlap', {}).get('x', 0) or 0),
            'y': int(kwargs.get('tile_overlap', {}).get('y', 0) or 0),
            'edges': kwargs.get('tile_overlap', {}).get('edges', False),
            'offset_x': 0,
            'offset_y': 0,
        }
        if not tile_overlap['edges']:
            # offset by half the overlap
            tile_overlap['offset_x'] = tile_overlap['x'] // 2
            tile_overlap['offset_y'] = tile_overlap['y'] // 2
        if 'tile_size' in kwargs:
            tile_size['width'] = int(kwargs['tile_size'].get(
                'width', kwargs['tile_size'].get('height', tile_size['width'])))
            tile_size['height'] = int(kwargs['tile_size'].get(
                'height', kwargs['tile_size'].get('width', tile_size['height'])))
        # Tile size includes the overlap
        tile_size['width'] -= tile_overlap['x']
        tile_size['height'] -= tile_overlap['y']
        if tile_size['width'] <= 0 or tile_size['height'] <= 0:
            raise ValueError('Invalid tile_size or tile_overlap.')

        resample = (
            False if round(requestedScale, 2) == 1.0 or
            kwargs.get('resample') in (None, False) else kwargs.get('resample'))
        # If we need to resample to make tiles at a non-native resolution,
        # adjust the tile size and tile overlap paramters appropriately.
        if resample is not False:
            tile_size['width'] = max(1, int(round(tile_size['width'] * requestedScale)))
            tile_size['height'] = max(1, int(round(tile_size['height'] * requestedScale)))
            tile_overlap['x'] = int(round(tile_overlap['x'] * requestedScale))
            tile_overlap['y'] = int(round(tile_overlap['y'] * requestedScale))

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
        mode = 'RGBA' if kwargs.get('encoding') in ('PNG', 'TIFF') else 'RGB'

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
            'frame': kwargs.get('frame'),
            'format': kwargs.get('format', (TILE_FORMAT_NUMPY, )),
            'encoding': kwargs.get('encoding'),
            'requestedScale': requestedScale,
            'resample': resample,
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
            width, height: size of current tile in current magnification pixels
            tile: cropped tile image
            format: format of the tile.  One of TILE_FORMAT_NUMPY,
                TILE_FORMAT_PIL, or TILE_FORMAT_IMAGE.  TILE_FORMAT_IMAGE is
                only returned if it was explicitly allowed and the tile is
                already in the correct image encoding.
            level: level of the current tile
            level_x, level_y: the tile reference number within the level.
                Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
                yielded may not be (0, 0) if a region is specified.
            tile_position: a dictionary of the tile position within the
                    iterator, containing:
                level_x, level_y: the tile reference number within the level.
                region_x, region_y: 0, 0 is the first tile in the full
                    iteration (when not restricting the iteration to a single
                    tile).
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
            gx, gy: (left, top) coordinates in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum-resolution
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

        config.getConfig('logger').debug(
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
                    'frame': iterInfo.get('frame'),
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

    def _pilFormatMatches(self, image, match=True, **kwargs):
        """
        Determine if the specified PIL image matches the format of the tile
        source with the specified arguments.

        :param image: the PIL image to check.
        :param match: if 'any', all image encodings are considered matching,
            if 'encoding', then a matching encoding matches regardless of
            quality options, otherwise, only match if the encoding and quality
            options match.
        :param **kwargs: additional parameters to use in determining format.
        """
        encoding = TileOutputPILFormat.get(self.encoding, self.encoding)
        if match == 'any' and encoding in ('PNG', 'JPEG'):
            return True
        if image.format != encoding:
            return False
        if encoding == 'PNG':
            return True
        if encoding == 'JPEG':
            if match == 'encoding':
                return True
            originalQuality = None
            try:
                if image.format == 'JPEG' and hasattr(image, 'quantization'):
                    if image.quantization[0][58] <= 100:
                        originalQuality = int(100 - image.quantization[0][58] / 2)
                    else:
                        originalQuality = int(5000.0 / 2.5 / image.quantization[0][15])
            except Exception:
                return False
            return abs(originalQuality - self.jpegQuality) <= 1
        # We fail for the TIFF file format; it is general enough that ensuring
        # compatibility could be an issue.
        return False

    def histogram(self, dtype=None, onlyMinMax=False, bins=256,
                  density=False, format=None, *args, **kwargs):
        """
        Get a histogram for a region.

        :param dtype: if specified, the tiles must be this numpy.dtype.
        :param onlyMinMax: if True, only return the minimum and maximum value
            of the region.
        :param bins: the number of bins in the histogram.  This is passed to
            numpy.histogram, but needs to produce the same set of edges for
            each tile.
        :param density: if True, scale the results based on the number of
            samples.
        :param format: ignored.  Used to override the format for the
            tileIterator.
        :param range: if None, use the computed min and (max + 1).  Otherwise,
            this is the range passed to numpy.histogram.  Note this is only
            accessible via kwargs as it otherwise overloads the range function.
        :param *args: parameters to pass to the tileIterator.
        :param **kwargs: parameters to pass to the tileIterator.
        """
        kwargs = kwargs.copy()
        histRange = kwargs.pop('range', None)
        results = None
        for tile in self.tileIterator(format=TILE_FORMAT_NUMPY, *args, **kwargs):
            tile = tile['tile']
            if dtype is not None and tile.dtype != dtype:
                if tile.dtype == numpy.uint8 and dtype == numpy.uint16:
                    tile = numpy.array(tile, dtype=numpy.uint16) * 257
                else:
                    continue
            tilemin = numpy.array([
                numpy.amin(tile[:, :, idx]) for idx in range(tile.shape[2])], tile.dtype)
            tilemax = numpy.array([
                numpy.amax(tile[:, :, idx]) for idx in range(tile.shape[2])], tile.dtype)
            if results is None:
                results = {'min': tilemin, 'max': tilemax}
            results['min'] = numpy.minimum(results['min'], tilemin)
            results['max'] = numpy.maximum(results['max'], tilemax)
        if results is None or onlyMinMax:
            return results
        results['histogram'] = [{
            'min': results['min'][idx],
            'max': results['max'][idx],
            'range': ((results['min'][idx], results['max'][idx] + 1)
                      if histRange is None else histRange),
            'hist': None,
            'bin_edges': None
        } for idx in range(len(results['min']))]
        for tile in self.tileIterator(format=TILE_FORMAT_NUMPY, *args, **kwargs):
            tile = tile['tile']
            if dtype is not None and tile.dtype != dtype:
                if tile.dtype == numpy.uint8 and dtype == numpy.uint16:
                    tile = numpy.array(tile, dtype=numpy.uint16) * 257
                else:
                    continue
            for idx in range(len(results['min'])):
                entry = results['histogram'][idx]
                hist, bin_edges = numpy.histogram(
                    tile[:, :, idx], bins, entry['range'], density=False)
                if entry['hist'] is None:
                    entry['hist'] = hist
                    entry['bin_edges'] = bin_edges
                else:
                    entry['hist'] += hist
        for idx in range(len(results['min'])):
            entry = results['histogram'][idx]
            if entry['hist'] is not None:
                entry['samples'] = numpy.sum(entry['hist'])
                if density:
                    entry['hist'] = entry['hist'].astype(numpy.float) / entry['samples']
        return results

    def _scanForMinMax(self, dtype, frame=None, analysisSize=1024, **kwargs):
        """
        Scan the image at a lower resolution to find the minimum and maximum
        values.

        :param dtype: the numpy dtype.  Used for guessing the range.
        :param frame: the frame to use for auto-ranging.
        :param analysisSize: the size of the image to use for analysis.
        """
        self._skipStyle = True
        # Divert the tile cache while querying unstyled tiles
        classkey = self._classkey
        self._classkey = 'nocache' + str(random.random())
        try:
            self._bandRanges[frame] = self.histogram(
                dtype=dtype,
                onlyMinMax=True,
                output={'maxWidth': min(self.sizeX, analysisSize),
                        'maxHeight': min(self.sizeY, analysisSize)},
                resample=False,
                frame=frame, **kwargs)
            if self._bandRanges[frame]:
                config.getConfig('logger').info('Style range is %r' % self._bandRanges[frame])
        finally:
            del self._skipStyle
            self._classkey = classkey

    def _getMinMax(self, minmax, value, dtype, bandidx=None, frame=None):
        """
        Get an appropriate minimum or maximum for a band.

        :param minmax: either 'min' or 'max'.
        :param value: the specified value, 'auto', 'min', or 'max'.  'auto'
            uses the parameter specified in 'minmax' or 0 or 255 if the
            band's minimum is in the range [0, 254] and maximum is in the range
            [2, 255].
        :param dtype: the numpy dtype.  Used for guessing the range.
        :param bandidx: the index of the channel that could be used for
            determining the min or max.
        :param frame: the frame to use for auto-ranging.
        """
        frame = frame or 0
        if value not in {'min', 'max', 'auto'}:
            try:
                value = float(value)
            except ValueError:
                config.getConfig('logger').warn(
                    'Style min/max value of %r is not valid; using "auto"', value)
                value = 'auto'
        if value in {'min', 'max', 'auto'} and frame not in self._bandRanges:
            self._scanForMinMax(dtype, frame)
        if value == 'auto':
            if (self._bandRanges.get(frame) and
                    numpy.all(self._bandRanges[frame]['min'] >= 0) and
                    numpy.all(self._bandRanges[frame]['min'] <= 254) and
                    numpy.all(self._bandRanges[frame]['max'] >= 2) and
                    numpy.all(self._bandRanges[frame]['max'] <= 255)):
                value = 0 if minmax == 'min' else 255
            else:
                value = minmax
        if value == 'min':
            if bandidx is not None and self._bandRanges.get(frame):
                value = self._bandRanges[frame]['min'][bandidx]
            else:
                value = 0
        elif value == 'max':
            if bandidx is not None and self._bandRanges.get(frame):
                value = self._bandRanges[frame]['max'][bandidx]
            elif dtype == numpy.uint16:
                value = 65535
            elif dtype == numpy.float:
                value = 1
            else:
                value = 255
        return float(value)

    def _applyStyle(self, image, style, frame=None):
        """
        Apply a style to a numpy image.

        :param image: the image to modify.
        :param style: a style object.
        :param frame: the frame to use for auto ranging.
        :returns: a styled image.
        """
        style = style['bands'] if 'bands' in style else [style]
        output = numpy.zeros((image.shape[0], image.shape[1], 4), numpy.float)
        for entry in style:
            bandidx = 0 if image.shape[2] <= 2 else 1
            band = None
            if (isinstance(entry.get('band'), six.integer_types) and
                    entry['band'] >= 1 and entry['band'] <= image.shape[2]):
                bandidx = entry['band'] - 1
            composite = entry.get('composite', 'lighten')
            if (hasattr(self, '_bandnames') and entry.get('band') and
                    str(entry['band']).lower() in self._bandnames and
                    image.shape[2] > self._bandnames[str(entry['band']).lower()]):
                bandidx = self._bandnames[str(entry['band']).lower()]
            if entry.get('band') == 'red' and image.shape[2] > 2:
                bandidx = 0
            elif entry.get('band') == 'blue' and image.shape[2] > 2:
                bandidx = 2
                band = image[:, :, 2]
            elif entry.get('band') == 'alpha':
                bandidx = image.shape[2] - 1 if image.shape[2] in (2, 4) else None
                band = (image[:, :, -1] if image.shape[2] in (2, 4) else
                        numpy.full(image.shape[:2], 255, numpy.uint8))
                composite = entry.get('composite', 'multiply')
            if band is None:
                band = image[:, :, bandidx]
            palette = numpy.array([
                PIL.ImageColor.getcolor(clr, 'RGBA') for clr in entry.get(
                    'palette', ['#000', '#FFF']
                    if entry.get('band') != 'alpha' else ['#FFF0', '#FFFF'])])
            palettebase = numpy.linspace(0, 1, len(palette), endpoint=True)
            nodata = entry.get('nodata')
            min = self._getMinMax('min', entry.get('min', 'auto'), image.dtype, bandidx, frame)
            max = self._getMinMax('max', entry.get('max', 'auto'), image.dtype, bandidx, frame)
            clamp = entry.get('clamp', True)
            delta = max - min if max != min else 1
            if nodata is not None:
                keep = band != nodata
            else:
                keep = numpy.full(image.shape[:2], True)
            band = (band - min) / delta
            if not clamp:
                keep = keep & (band >= 0) & (band <= 1)
            for channel in range(4):
                clrs = numpy.interp(band, palettebase, palette[:, channel])
                if composite == 'multiply':
                    output[:, :, channel] = numpy.multiply(
                        output[:, :, channel], numpy.where(keep, clrs / 255, 1))
                else:
                    output[:, :, channel] = numpy.maximum(
                        output[:, :, channel], numpy.where(keep, clrs, 0))
        return output

    def _outputTileNumpyStyle(self, tile, applyStyle, frame=None):
        """
        Convert a tile to a NUMPY array.  Optionally apply the style to a tile.
        Always returns a NUMPY tile.

        :param tile: the tile to convert.
        :param applyStyle: if True and there is a style, apply it.
        :param frame: the frame to use for auto-ranging.
        :returns: a numpy array and a target PIL image mode.
        """
        tile, mode = _imageToNumpy(tile)
        if applyStyle and getattr(self, 'style', None):
            with self._styleLock:
                if not getattr(self, '_skipStyle', False):
                    tile = self._applyStyle(tile, self.style, frame)
        if tile.shape[0] != self.tileHeight or tile.shape[1] != self.tileWidth:
            extend = numpy.zeros(
                (self.tileHeight, self.tileWidth, tile.shape[2]),
                dtype=tile.dtype)
            extend[:min(self.tileHeight, tile.shape[0]),
                   :min(self.tileWidth, tile.shape[1])] = tile
            tile = extend
        return tile, mode

    def _outputTile(self, tile, tileEncoding, x, y, z, pilImageAllowed=False,
                    numpyAllowed=False, applyStyle=True, **kwargs):
        """
        Convert a tile from a numpy array, PIL image, or image in memory to the
        desired encoding.

        :param tile: the tile to convert.
        :param tileEncoding: the current tile encoding.
        :param x: tile x value.  Used for cropping or edge adjustment.
        :param y: tile y value.  Used for cropping or edge adjustment.
        :param z: tile z (level) value.  Used for cropping or edge adjustment.
        :param pilImageAllowed: True if a PIL image may be returned.
        :param numpyAllowed: True if a NUMPY image may be returned.  'always'
            to return a numpy array.
        :param applyStyle: if True and there is a style, apply it.
        :returns: either a numpy array, a PIL image, or a memory object with an
            image file.
        """
        isEdge = False
        if self.edge:
            sizeX = int(self.sizeX * 2 ** (z - (self.levels - 1)))
            sizeY = int(self.sizeY * 2 ** (z - (self.levels - 1)))
            maxX = (x + 1) * self.tileWidth
            maxY = (y + 1) * self.tileHeight
            isEdge = maxX > sizeX or maxY > sizeY
        if (tileEncoding not in (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY) and
                numpyAllowed != 'always' and tileEncoding == self.encoding and
                not isEdge and (not applyStyle or not getattr(self, 'style', None))):
            return tile
        mode = None
        if (numpyAllowed == 'always' or tileEncoding == TILE_FORMAT_NUMPY or
                (applyStyle and getattr(self, 'style', None)) or isEdge):
            tile, mode = self._outputTileNumpyStyle(tile, applyStyle, kwargs.get('frame'))
        if isEdge:
            contentWidth = min(self.tileWidth,
                               sizeX - (maxX - self.tileWidth))
            contentHeight = min(self.tileHeight,
                                sizeY - (maxY - self.tileHeight))
            tile, mode = _imageToNumpy(tile)
            if self.edge in (True, 'crop'):
                tile = tile[:contentHeight, :contentWidth]
            else:
                color = PIL.ImageColor.getcolor(self.edge, mode)
                tile = tile.copy()
                tile[:, contentWidth:] = color
                tile[contentHeight:] = color
        if isinstance(tile, numpy.ndarray) and numpyAllowed:
            return tile
        tile = _imageToPIL(tile)
        if pilImageAllowed:
            return tile
        encoding = TileOutputPILFormat.get(self.encoding, self.encoding)
        if encoding == 'JPEG' and tile.mode not in ('L', 'RGB'):
            tile = tile.convert('RGB')
        # If we can't redirect, but the tile is read from a file in the desired
        # output format, just read the file
        if hasattr(tile, 'fp') and self._pilFormatMatches(tile):
            tile.fp.seek(0)
            return tile.fp.read()
        output = BytesIO()
        params = {}
        if encoding == 'JPEG':
            params['quality'] = self.jpegQuality
            params['subsampling'] = self.jpegSubsampling
        elif encoding == 'TIFF':
            params['compression'] = self.tiffCompression
        tile.save(output, encoding, **params)
        return output.getvalue()

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        return None

    @classmethod
    def canRead(cls, *args, **kwargs):
        """
        Check if we can read the input.  This takes the same parameters as
        __init__.

        :returns: True if this class can read the input.  False if it cannot.
        """
        return False

    def getMetadata(self):
        """
        Return metadata about this tile source.  In addition to the keys that
        are listed in this template function, tile sources that expose multiple
        frames will also contain:
        - frames: a list of frames.  Each frame entry is a dictionary with
          - Frame: a 0-values frame index (the location in the list)
          - Channel (optional): the name of the channel, if known
          - IndexC (optional if unique): a 0-based index into the channel list
          - IndexT (optional if unique): a 0-based index for time values
          - IndexZ (optional if unique): a 0-based index for z values
          - IndexXY (optional if unique): a 0-based index for view (xy) values
          - Index: a 0-based index of non-channel unique sets.  If the frames
              vary only by channel and are adjacent, they will have the same
              index.
        - IndexRange: a dictionary of the number of unique index values from
            frames if greater than 1 (e.g., if an entry like IndexXY is not
            present, then all frames either do not have that value or have a
            value of 0).
        - channels (optional): if known, a list of channel names
        - channelmap (optional): if known, a dictionary of channel names with
            their offset into the channel list.
        """
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

    def _addMetadataFrameInformation(self, metadata, channels=None):
        """
        Given a metadata response that has a `frames` list, where each frame
        has some of `Index(XY|Z|C|T)`, populate the `Frame`, `Index` and
        possibly the `Channel` of each frame in the list and the `IndexRange`,
        `IndexStride`, and possibly the `channels` and `channelmap` entries of
        the metadata.

        :param metadata: the metadata response that might contain `frames`.
            Modified.
        :param channels: an optional list of channel names.
        """
        if 'frames' not in metadata:
            return
        maxref = {}
        refkeys = {'IndexC', 'IndexZ', 'IndexXY', 'IndexT'}
        index = 0
        for idx, frame in enumerate(metadata['frames']):
            for key in refkeys:
                if key in frame and frame[key] + 1 > maxref.get(key, 0):
                    maxref[key] = frame[key] + 1
            frame['Frame'] = idx
            if idx and any(
                    frame.get(key) != metadata['frames'][idx - 1].get(key)
                    for key in refkeys if key != 'IndexC'):
                index += 1
            frame['Index'] = index
        if any(val > 1 for val in maxref.values()):
            metadata['IndexRange'] = {key: value for key, value in maxref.items() if value > 1}
            metadata['IndexStride'] = {
                key: [idx for idx, frame in enumerate(metadata['frames']) if frame[key] == 1][0]
                for key in metadata['IndexRange']
            }
        if channels and len(channels) >= maxref.get('IndexC', 1):
            metadata['channels'] = channels[:maxref.get('IndexC', 1)]
            metadata['channelmap'] = {
                cname: c for c, cname in enumerate(channels[:maxref.get('IndexC', 1)])}
            for frame in metadata['frames']:
                frame['Channel'] = channels[frame.get('IndexC', 0)]

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        return None

    def _xyzInRange(self, x, y, z):
        """
        Check if a tile at x, y, z is in range based on self.levels,
        self.tileWidth, self.tileHeight, self.sizeX, and self.sizeY,  Raise an
        exception if not.
        """
        if z < 0 or z >= self.levels:
            raise exceptions.TileSourceException('z layer does not exist')
        scale = 2 ** (self.levels - 1 - z)
        offsetx = x * self.tileWidth * scale
        if not (0 <= offsetx < self.sizeX):
            raise exceptions.TileSourceException('x is outside layer')
        offsety = y * self.tileHeight * scale
        if not (0 <= offsety < self.sizeY):
            raise exceptions.TileSourceException('y is outside layer')

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                sparseFallback=False, frame=None):
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
            jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: thumbData, thumbMime: the image data and the mime type.
        """
        if ((width is not None and (not isinstance(width, six.integer_types) or width < 2)) or
                (height is not None and (not isinstance(height, six.integer_types) or height < 2))):
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
        image = _imageToPIL(tileData)
        imageWidth = int(math.floor(
            metadata['sizeX'] * 2 ** -(metadata['levels'] - 1)))
        imageHeight = int(math.floor(
            metadata['sizeY'] * 2 ** -(metadata['levels'] - 1)))
        image = image.crop((0, 0, imageWidth, imageHeight))

        if width or height:
            maxWidth, maxHeight = width, height
            width, height, calcScale = self._calculateWidthHeight(
                width, height, imageWidth, imageHeight)

            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > imageWidth else PIL.Image.LANCZOS)
            if kwargs.get('fill') and maxWidth and maxHeight:
                image = _letterboxImage(image, maxWidth, maxHeight, kwargs['fill'])
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

    def convertRegionScale(
            self, sourceRegion, sourceScale=None, targetScale=None,
            targetUnits=None, cropToImage=True):
        """
        Convert a region from one scale to another.

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
        :param cropToImage: if True, don't return region coordinates outside of
            the image.
        """
        units = sourceRegion.get('units')
        if units not in TileInputUnits:
            raise ValueError('Invalid units %r' % units)
        units = TileInputUnits[units]
        if targetUnits is not None:
            if targetUnits not in TileInputUnits:
                raise ValueError('Invalid units %r' % targetUnits)
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
            metadata, desiredMagnification=mag, cropToImage=cropToImage,
            **sourceRegion)
        # If requested, convert region to targetUnits
        magArgs = (targetScale or {}).copy()
        magArgs['rounding'] = None
        magLevel = self.getLevelForMagnification(**magArgs)
        desiredMagnification = self.getMagnificationForLevel(magLevel)
        scaleX, scaleY = self._scaleFromUnits(metadata, targetUnits, desiredMagnification)
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
            encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
            tileIterator.
        :returns: regionData, formatOrRegionMime: the image data and either the
            mime type, if the format is TILE_FORMAT_IMAGE, or the format.
        """
        if not isinstance(format, (tuple, set, list)):
            format = (format, )
        if 'tile_position' in kwargs:
            kwargs = kwargs.copy()
            kwargs.pop('tile_position', None)
        iterInfo = self._tileIteratorInfo(**kwargs)
        if iterInfo is None:
            image = PIL.Image.new('RGB', (0, 0))
            return _encodeImage(image, format=format, **kwargs)
        regionWidth = iterInfo['region']['width']
        regionHeight = iterInfo['region']['height']
        top = iterInfo['region']['top']
        left = iterInfo['region']['left']
        mode = None if TILE_FORMAT_NUMPY in format else iterInfo['mode']
        outWidth = iterInfo['output']['width']
        outHeight = iterInfo['output']['height']
        image = None
        for tile in self._tileIterator(iterInfo):
            # Add each tile to the image
            subimage, _ = _imageToNumpy(tile['tile'])
            if image is None:
                try:
                    image = numpy.zeros(
                        (regionHeight, regionWidth, subimage.shape[2]),
                        dtype=subimage.dtype)
                except MemoryError:
                    raise exceptions.TileSourceException(
                        'Insufficient memory to get region of %d x %d pixels.' % (
                            regionWidth, regionHeight))
            x0, y0 = tile['x'] - left, tile['y'] - top
            if x0 < 0:
                subimage = subimage[:, -x0:]
                x0 = 0
            if y0 < 0:
                subimage = subimage[-y0:, :]
                y0 = 0
            subimage = subimage[:min(subimage.shape[0], regionHeight - y0),
                                :min(subimage.shape[1], regionWidth - x0)]
            if subimage.shape[2] > image.shape[2]:
                newimage = numpy.ones((image.shape[0], image.shape[1], subimage.shape[2]))
                newimage[:, :, :image.shape[2]] = image
                image = newimage
            image[y0:y0 + subimage.shape[0], x0:x0 + subimage.shape[1],
                  :subimage.shape[2]] = subimage
        # Scale if we need to
        outWidth = int(math.floor(outWidth))
        outHeight = int(math.floor(outHeight))
        if outWidth != regionWidth or outHeight != regionHeight:
            image = _imageToPIL(image, mode).resize(
                (outWidth, outHeight),
                PIL.Image.BICUBIC if outWidth > regionWidth else
                PIL.Image.LANCZOS)
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if kwargs.get('fill') and maxWidth and maxHeight:
            image = _letterboxImage(_imageToPIL(image, mode), maxWidth, maxHeight, kwargs['fill'])
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
                                'keyword argument of "%s"' % key)
        region = self.convertRegionScale(sourceRegion, sourceScale,
                                         targetScale, targetUnits)
        return self.getRegion(region=region, scale=targetScale, **kwargs)

    def getPointAtAnotherScale(self, point, sourceScale=None, sourceUnits=None,
                               targetScale=None, targetUnits=None, **kwargs):
        """
        Given a point as a (x, y) tuple, convert it from one scale to another.
        The sourceScale, sourceUnits, targetScale, and targetUnits parameters
        are the same as convertRegionScale, where sourceUnits are the units
        used with sourceScale.
        """
        sourceRegion = {
            'units': 'base_pixels' if sourceUnits is None else sourceUnits,
            'left': point[0],
            'top': point[1],
            'right': point[0],
            'bottom': point[1],
        }
        region = self.convertRegionScale(
            sourceRegion, sourceScale, targetScale, targetUnits,
            cropToImage=False)
        return (region['left'], region['top'])

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
            the magnification factor of.
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
        if mag.get('level') == self.levels - 1:
            mag['scale'] = 1.0
        return mag

    def getLevelForMagnification(self, magnification=None, exact=False,
                                 mm_x=None, mm_y=None, rounding='round',
                                 **kwargs):
        """
        Get the level for a specific magnification or pixel size.  If the
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

    def tileIterator(self, format=(TILE_FORMAT_NUMPY, ), resample=True,
                     **kwargs):
        """
        Iterate on all tiles in the specified region at the specified scale.
        Each tile is returned as part of a dictionary that includes
            x, y: (left, top) coordinates in current magnification pixels
            width, height: size of current tile in current magnification pixels
            tile: cropped tile image
            format: format of the tile
            level: level of the current tile
            level_x, level_y: the tile reference number within the level.
                Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
                yielded may not be (0, 0) if a region is specified.
            tile_position: a dictionary of the tile position within the
                    iterator, containing:
                level_x, level_y: the tile reference number within the level.
                region_x, region_y: 0, 0 is the first tile in the full
                    iteration (when not restricting the iteration to a single
                    tile).
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
            gx, gy: (left, top) coordinates in maximum-resolution pixels
            gwidth, gheight: size of of the current tile in maximum-resolution
                pixels.
            tile_overlap: the amount of overlap with neighboring tiles (left,
                top, right, and bottom).  Overlap never extends outside of the
                requested region.
        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom edges in any case.  If an exact
        magnification or scale is requested, no tiles will be returned.

        :param format: the desired format or a tuple of allowed formats.
            Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
            TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding must be
            specified.
        :param resample: If True or one of PIL.Image.NEAREST, LANCZOS,
            BILINEAR, or BICUBIC to resample tiles that are not the target
            output size.  Tiles that are resampled will have additional
            dictionary entries of:
                scaled: the scaling factor that was applied (less than 1 is
                    downsampled).
                tile_x, tile_y: (left, top) coordinates before scaling
                tile_width, tile_height: size of the current tile before
                    scaling.
                tile_magnification: magnification of the current tile before
                    scaling.
                tile_mm_x, tile_mm_y: size of a pixel in a tile in millimeters
                    before scaling.
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
                is specified, magnification, mm_x, and mm_y are ignored.
            maxHeight: maximum height in pixels.
        :param scale: a dictionary of optional values which specify the scale
                of the region and / or output.  This applies to region if
                pixels or mm are used for inits.  It applies to output if
                neither output maxWidth nor maxHeight is specified.
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
            encoding (typically 'PNG', 'JPEG', or 'TIFF').  Must also be in the
            TileOutputMimeTypes map.
        :param jpegQuality: the quality to use when encoding a JPEG.
        :param jpegSubsampling: the subsampling level to use when encoding a
            JPEG.
        :param tiffCompression: the compression format when encoding a TIFF.
            This is usually 'raw', 'tiff_lzw', 'jpeg', or 'tiff_adobe_deflate'.
            Some of these are aliased: 'none', 'lzw', 'deflate'.
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
        iterInfo = self._tileIteratorInfo(format=iterFormat, resample=resample,
                                          **kwargs)
        if not iterInfo:
            return
        # check if the desired scale is different from the actual scale and
        # resampling is needed.  Ignore small scale differences.
        if (resample in (False, None) or
                round(iterInfo['requestedScale'], 2) == 1.0):
            resample = False
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
                                'keyword argument of "%s"' % key)
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

    def getTileCount(self, *args, **kwargs):
        """
        Return the number of tiles that the tileIterator will return.  See
        tileIterator for parameters.

        :return: the number of tiles that the tileIterator will yield.
        """
        tile = next(self.tileIterator(*args, **kwargs), None)
        if tile is not None:
            return tile['iterator_range']['position']
        return 0

    def getAssociatedImagesList(self):
        """
        Return a list of associated images.

        :return: the list of image keys.
        """
        return []

    def getAssociatedImage(self, imageKey, *args, **kwargs):
        """
        Return an associated image.

        :param imageKey: the key of the associated image to retrieve.
        :param **kwargs: optional arguments.  Some options are width, height,
            encoding, jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: imageData, imageMime: the image data and the mime type, or
            None if the associated image doesn't exist.
        """
        image = self._getAssociatedImage(imageKey)
        if not image:
            return
        imageWidth, imageHeight = image.size
        width = kwargs.get('width')
        height = kwargs.get('height')
        if width or height:
            width, height, calcScale = self._calculateWidthHeight(
                width, height, imageWidth, imageHeight)
            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > imageWidth else PIL.Image.LANCZOS)
        return _encodeImage(image, **kwargs)

    def getPixel(self, includeTileRecord=False, **kwargs):
        """
        Get a single pixel from the current tile source.
        :param includeTileRecord: if True, include the tile used for computing
            the pixel in the response.
        :param **kwargs: optional arguments.  Some options are region, output,
            encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
            tileIterator.
        :returns: a dictionary with the value of the pixel for each channel on
            a scale of [0-255], including alpha, if available.  This may
            contain additional information.
        """
        regionArgs = kwargs.copy()
        regionArgs['region'] = regionArgs.get('region', {}).copy()
        regionArgs['region']['width'] = regionArgs['region']['height'] = 1
        regionArgs['region']['unitsWH'] = 'base_pixels'
        pixel = {}
        # This could be
        #  img, format = self.getRegion(format=TILE_FORMAT_PIL, **regionArgs)
        # where img is the PIL image (rather than tile['tile'], but using
        # _tileIteratorInfo and the _tileIterator is slightly more efficient.
        iterInfo = self._tileIteratorInfo(format=TILE_FORMAT_PIL, **regionArgs)
        if iterInfo is not None:
            tile = next(self._tileIterator(iterInfo), None)
            if includeTileRecord:
                pixel['tile'] = tile
            img = tile['tile']
            if img.size[0] >= 1 and img.size[1] >= 1:
                pixel.update(dict(zip(img.mode.lower(), img.load()[0, 0])))
        return pixel


class FileTileSource(TileSource):

    def __init__(self, path, *args, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super(FileTileSource, self).__init__(*args, **kwargs)
        self.largeImagePath = path

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            args[0], kwargs.get('encoding', 'JPEG'), kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0), kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False), kwargs.get('style', None))

    def getState(self):
        return '%s,%s,%s,%s,%s,%s,%s' % (
            self._getLargeImagePath(),
            self.encoding,
            self.jpegQuality,
            self.jpegSubsampling,
            self.tiffCompression,
            self.edge,
            self._jsonstyle)

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
        except exceptions.TileSourceException:
            return False
