import io
import json
import math
import os
import pathlib
import re
import tempfile
import threading
import time
import types

import numpy
import PIL
import PIL.Image
import PIL.ImageCms
import PIL.ImageColor
import PIL.ImageDraw

from .. import config, exceptions
from ..cache_util import getTileCache, methodcache, strhash
from ..constants import (TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL,
                         SourcePriority, TileInputUnits, TileOutputMimeTypes,
                         TileOutputPILFormat, dtypeToGValue)
from .tiledict import LazyTileDict
from .utilities import (JSONDict, _encodeImage,  # noqa: F401
                        _encodeImageBinary, _gdalParameters, _imageToNumpy,
                        _imageToPIL, _letterboxImage, _makeSameChannelDepth,
                        _vipsCast, _vipsParameters, dictToEtree, etreeToDict,
                        getPaletteColors, histogramThreshold, nearPowerOfTwo)


class TileSource:
    #: Name of the tile source
    name = None

    #: A dictionary of known file extensions and the ``SourcePriority`` given
    #: to each.  It must contain a None key with a priority for the tile source
    #: when the extension does not match.
    extensions = {
        None: SourcePriority.FALLBACK
    }

    #: A dictionary of common mime-types handled by the source and the
    #: ``SourcePriority`` given to each.  This are used in place of or in
    #: additional to extensions.
    mimeTypes = {
        None: SourcePriority.FALLBACK
    }

    geospatial = False

    def __init__(self, encoding='JPEG', jpegQuality=95, jpegSubsampling=0,
                 tiffCompression='raw', edge=False, style=None, *args,
                 **kwargs):
        """
        Initialize the tile class.

        :param jpegQuality: when serving jpegs, use this quality.
        :param jpegSubsampling: when serving jpegs, use this subsampling (0 is
            full chroma, 1 is half, 2 is quarter).
        :param encoding: 'JPEG', 'PNG', 'TIFF', or 'TILED'.
        :param edge: False to leave edge tiles whole, True or 'crop' to crop
            edge tiles, otherwise, an #rrggbb color to fill edges.
        :param tiffCompression: the compression format to use when encoding a
            TIFF.
        :param style: if None, use the default style for the file.  Otherwise,
            this is a string with a json-encoded dictionary.  The style can
            contain the following keys:

                :band: if -1 or None, and if style is specified at all, the
                    greyscale value is used.  Otherwise, a 1-based numerical
                    index into the channels of the image or a string that
                    matches the interpretation of the band ('red', 'green',
                    'blue', 'gray', 'alpha').  Note that 'gray' on an RGB or
                    RGBA image will use the green band.
                :frame: if specified, override the frame value for this band.
                    When used as part of a bands list, this can be used to
                    composite multiple frames together.  It is most efficient
                    if at least one band either doesn't specify a frame
                    parameter or specifies the same frame value as the primary
                    query.
                :framedelta: if specified and frame is not specified, override
                    the frame value for this band by using the current frame
                    plus this value.
                :min: the value to map to the first palette value.  Defaults to
                    0.  'auto' to use 0 if the reported minimum and maximum of
                    the band are between [0, 255] or use the reported minimum
                    otherwise.  'min' or 'max' to always uses the reported
                    minimum or maximum.  'full' to always use 0.
                :max: the value to map to the last palette value.  Defaults to
                    255.  'auto' to use 0 if the reported minimum and maximum
                    of the band are between [0, 255] or use the reported
                    maximum otherwise.  'min' or 'max' to always uses the
                    reported minimum or maximum.  'full' to use the maximum
                    value of the base data type (either 1, 255, or 65535).
                :palette: a list of two or more color strings, where color
                    strings are of the form #RRGGBB, #RRGGBBAA, #RGB, #RGBA, or
                    any string parseable by the PIL modules, or, if it is
                    installed, byt matplotlib.  Alternately, this can be a
                    single color, which implies ['#000', <color>], or the name
                    of a palettable paletter or, if available, a matplotlib
                    palette.
                :nodata: the value to use for missing data.  null or unset to
                    not use a nodata value.
                :composite: either 'lighten' or 'multiply'.  Defaults to
                    'lighten' for all except the alpha band.
                :clamp: either True to clamp (also called clip or crop) values
                    outside of the [min, max] to the ends of the palette or
                    False to make outside values transparent.
                :dtype: convert the results to the specified numpy dtype.
                    Normally, if a style is applied, the results are
                    intermediately a float numpy array with a value range of
                    [0,255].  If this is 'uint16', it will be cast to that and
                    multiplied by 65535/255.  If 'float', it will be divided by
                    255.
                :axis: keep only the specified axis from the numpy intermediate
                    results.  This can be used to extract a single channel
                    after compositing.

            Alternately, the style object can contain a single key of 'bands',
            which has a value which is a list of style dictionaries as above,
            excepting that each must have a band that is not -1.  Bands are
            composited in the order listed.  This base object may also contain
            the 'dtype' and 'axis' values.
        """
        self.logger = config.getConfig('logger')
        self.cache, self.cache_lock = getTileCache()

        self.tileWidth = None
        self.tileHeight = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None
        self._styleLock = threading.RLock()

        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)

        self.encoding = encoding
        self.jpegQuality = int(jpegQuality)
        self.jpegSubsampling = int(jpegSubsampling)
        self.tiffCompression = tiffCompression
        self.edge = edge
        self._setStyle(style)

    def __getstate__(self):
        """
        Allow pickling.

        We reconstruct our state via the creation caused by the inverse of
        reduce, so we don't report state here.
        """
        return None

    def __reduce__(self):
        """
        Allow pickling.

        Reduce can pass the args but not the kwargs, so use a partial class
        call to recosntruct kwargs.
        """
        import functools
        import pickle

        if not hasattr(self, '_initValues') or hasattr(self, '_unpickleable'):
            raise pickle.PicklingError('Source cannot be pickled')
        return functools.partial(type(self), **self._initValues[1]), self._initValues[0]

    def __repr__(self):
        return self.getState()

    def _repr_png_(self):
        return self.getThumbnail(encoding='PNG')[0]

    def _setStyle(self, style):
        """
        Check and set the specified style from a json string or a dictionary.

        :param style: The new style.
        """
        for key in {'_unlocked_classkey', '_classkeyLock'}:
            try:
                delattr(self, key)
            except Exception:
                pass
        self._bandRanges = {}
        self._jsonstyle = style
        if style:
            if isinstance(style, dict):
                self._style = JSONDict(style)
                self._jsonstyle = json.dumps(style, sort_keys=True, separators=(',', ':'))
            else:
                try:
                    style = json.loads(style)
                    if not isinstance(style, dict):
                        raise TypeError
                    self._style = JSONDict(style)
                except TypeError:
                    raise exceptions.TileSourceError('Style is not a valid json object.')

    @property
    def style(self):
        return self._style

    @staticmethod
    def getLRUHash(*args, **kwargs):
        """
        Return a string hash used as a key in the recently-used cache for tile
        sources.

        :returns: a string hash value.
        """
        return strhash(
            kwargs.get('encoding', 'JPEG'), kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0), kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False),
            '__STYLESTART__', kwargs.get('style', None), '__STYLEEND__')

    def getState(self):
        """
        Return a string reflecting the state of the tile source.  This is used
        as part of a cache key when hashing function return values.

        :returns: a string hash value of the source state.
        """
        if hasattr(self, '_classkey'):
            return self._classkey
        return '%s,%s,%s,%s,%s,__STYLESTART__,%s,__STYLEEND__' % (
            self.encoding,
            self.jpegQuality,
            self.jpegSubsampling,
            self.tiffCompression,
            self.edge,
            self._jsonstyle)

    def wrapKey(self, *args, **kwargs):
        """
        Return a key for a tile source and function parameters that can be used
        as a unique cache key.

        :param args: arguments to add to the hash.
        :param kwaths: arguments to add to the hash.
        :returns: a cache key.
        """
        return strhash(self.getState()) + strhash(*args, **kwargs)

    def _ignoreSourceNames(self, configKey, path, default=None):
        """
        Given a path, if it is an actual file and there is a setting
        "source_<configKey>_ignored_names", raise a TileSoruceError if the
        path matches the ignore names setting regex in a case-insensitve
        search.

        :param configKey: key to use to fetch value from settings.
        :param path: the file path to check.
        :param default: a default ignore regex, or None for no default.
        """
        ignored_names = config.getConfig('source_%s_ignored_names' % configKey) or default
        if not ignored_names or not os.path.isfile(path):
            return
        if re.search(ignored_names, os.path.basename(path), flags=re.IGNORECASE):
            raise exceptions.TileSourceError('File will not be opened by %s reader' % configKey)

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
        scaledWidth = max(1, int(regionWidth * height / regionHeight))
        scaledHeight = max(1, int(regionHeight * width / regionWidth))
        if scaledWidth == width or (
                width * regionHeight > height * regionWidth and not scaledHeight == height):
            scale = float(regionHeight) / height
            width = scaledWidth
        else:
            scale = float(regionWidth) / width
            height = scaledHeight
        return width, height, scale

    def _scaleFromUnits(self, metadata, units, desiredMagnification, **kwargs):
        """
        Get scaling parameters based on the source metadata and specified
        units.

        :param metadata: the metadata associated with this source.
        :param units: the units used for the scale.
        :param desiredMagnification: the output from getMagnificationForLevel
            for the desired magnification used to convert mag_pixels and mm.
        :param kwargs: optional parameters.
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
        are interpreted as an offset from the right or bottom edge of the
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
        :param kwargs: optional parameters.  These are passed to
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

            :left: the left edge (inclusive) of the region to process.
            :top: the top edge (inclusive) of the region to process.
            :right: the right edge (exclusive) of the region to process.
            :bottom: the bottom edge (exclusive) of the region to process.
            :width: the width of the region to process.
            :height: the height of the region to process.
            :units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.
            :unitsWH: if not specified, this is the same as `units`.
                Otherwise, these units will be used for the width and height if
                specified.

        :param output: a dictionary of optional values which specify the size
                of the output.

            :maxWidth: maximum width in pixels.
            :maxHeight: maximum height in pixels.

        :param scale: a dictionary of optional values which specify the scale
            of the region and / or output.  This applies to region if
            pixels or mm are used for units.  It applies to output if
            neither output maxWidth nor maxHeight is specified.

            :magnification: the magnification ratio.
            :mm_x: the horizontal size of a pixel in millimeters.
            :mm_y: the vertical size of a pixel in millimeters.
            :exact: if True, only a level that matches exactly will be
                returned.  This is only applied if magnification, mm_x, or mm_y
                is used.

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

            :width: the desired tile width.
            :height: the desired tile height.

        :param tile_overlap: if present, retile the output adding a symmetric
            overlap to the tiles.  If either x or y is not specified, it
            defaults to zero.  The overlap does not change the tile size,
            only the stride of the tiles.  This is a dictionary containing:

            :x: the horizontal overlap in pixels.
            :y: the vertical overlap in pixels.
            :edges: if True, then the edge tiles will exclude the overlap
                distance.  If unset or False, the edge tiles are full size.

        :param kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, tiffCompression, frame.
        :returns: a dictionary of information needed for the tile iterator.
            This is None if no tiles will be returned.  Otherwise, this
            contains:

            :region: a dictionary of the source region information:

                :width, height: the total output of the iterator in pixels.
                    This may be larger than the requested resolution (given by
                    output width and output height) if there isn't an exact
                    match between the requested resolution and available native
                    tiles.
                :left, top, right, bottom: the coordinates within the image of
                    the region returned in the level pixel space.

            :xmin, ymin, xmax, ymax: the tiles that will be included during the
                iteration: [xmin, xmax) and [ymin, ymax).
            :mode: either 'RGB' or 'RGBA'.  This determines the color space
                used for tiles.
            :level: the tile level used for iteration.
            :metadata: tile source metadata (from getMetadata)
            :output: a dictionary of the output resolution information.

                :width, height: the requested output resolution in pixels.  If
                    this is different that region width and region height, then
                    the original request was asking for a different scale than
                    is being delivered.

            :frame: the frame value for the base image.
            :format: a tuple of allowed output formats.
            :encoding: if the output format is TILE_FORMAT_IMAGE, the desired
                encoding.
            :requestedScale: the scale needed to convert from the region width
                and height to the output width and height.
        """
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if ((maxWidth is not None and
                (not isinstance(maxWidth, int) or maxWidth < 0)) or
                (maxHeight is not None and
                 (not isinstance(maxHeight, int) or maxHeight < 0))):
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
        if (regionWidth < 0 or regionHeight < 0 or outWidth == 0 or
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
            'range_x': 0,
            'range_y': 0
        }
        if not tile_overlap['edges']:
            # offset by half the overlap
            tile_overlap['offset_x'] = tile_overlap['x'] // 2
            tile_overlap['offset_y'] = tile_overlap['y'] // 2
            tile_overlap['range_x'] = tile_overlap['x']
            tile_overlap['range_y'] = tile_overlap['y']
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
        # adjust the tile size and tile overlap parameters appropriately.
        if resample is not False:
            tile_size['width'] = max(1, int(math.ceil(tile_size['width'] * requestedScale)))
            tile_size['height'] = max(1, int(math.ceil(tile_size['height'] * requestedScale)))
            tile_overlap['x'] = int(math.ceil(tile_overlap['x'] * requestedScale))
            tile_overlap['y'] = int(math.ceil(tile_overlap['y'] * requestedScale))

        # If the overlapped tiles don't run over the edge, then the functional
        # size of the region is reduced by the overlap.  This factor is stored
        # in the overlap offset_*.
        xmin = int(left / tile_size['width'])
        xmax = max(int(math.ceil((float(right) - tile_overlap['range_x']) /
                                 tile_size['width'])), xmin + 1)
        ymin = int(top / tile_size['height'])
        ymax = max(int(math.ceil((float(bottom) - tile_overlap['range_y']) /
                                 tile_size['height'])), ymin + 1)
        tile_overlap.update({'xmin': xmin, 'xmax': xmax,
                             'ymin': ymin, 'ymax': ymax})

        # Use RGB for JPEG, RGBA for PNG
        mode = 'RGBA' if kwargs.get('encoding') in {'PNG', 'TIFF', 'TILED'} else 'RGB'

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

            :x, y: (left, top) coordinate in current magnification pixels
            :width, height: size of current tile in current magnification
                pixels
            :tile: cropped tile image
            :format: format of the tile.  One of TILE_FORMAT_NUMPY,
                TILE_FORMAT_PIL, or TILE_FORMAT_IMAGE.  TILE_FORMAT_IMAGE is
                only returned if it was explicitly allowed and the tile is
                already in the correct image encoding.
            :level: level of the current tile
            :level_x, level_y: the tile reference number within the level.
                Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
                yielded may not be (0, 0) if a region is specified.
            :tile_position: a dictionary of the tile position within the
                iterator, containing:

                :level_x, level_y: the tile reference number within the level.
                :region_x, region_y: 0, 0 is the first tile in the full
                    iteration (when not restricting the iteration to a single
                    tile).
                :position: a 0-based value for the tile within the full
                    iteration.

            :iterator_range: a dictionary of the output range of the iterator:

                :level_x_min, level_x_max: the tiles that are be included
                    during the full iteration: [layer_x_min, layer_x_max).
                :level_y_min, level_y_max: the tiles that are be included
                    during the full iteration: [layer_y_min, layer_y_max).
                :region_x_max, region_y_max: the number of tiles included during
                    the full iteration.   This is layer_x_max - layer_x_min,
                    layer_y_max - layer_y_min.
                :position: the total number of tiles included in the full
                    iteration.  This is region_x_max * region_y_max.

            :magnification: magnification of the current tile
            :mm_x, mm_y: size of the current tile pixel in millimeters.
            :gx, gy: (left, top) coordinates in maximum-resolution pixels
            :gwidth, gheight: size of of the current tile in maximum-resolution
                pixels.
            :tile_overlap: the amount of overlap with neighboring tiles (left,
                top, right, and bottom).  Overlap never extends outside of the
                requested region.

        If a region that includes partial tiles is requested, those tiles are
        cropped appropriately.  Most images will have tiles that get cropped
        along the right and bottom edges in any case.

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

        self.logger.debug(
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
                overlap['right'] = (
                    max(0, tileWidth - tileSize['width'] - overlap['left'])
                    if x != xmin or not tileOverlap['range_x'] else
                    min(tileWidth, tileOverlap['range_x'] - tileOverlap['offset_x']))
                overlap['bottom'] = (
                    max(0, tileHeight - tileSize['height'] - overlap['top'])
                    if y != ymin or not tileOverlap['range_y'] else
                    min(tileHeight, tileOverlap['range_y'] - tileOverlap['offset_y']))
                if tileOverlap['range_x']:
                    overlap['left'] = 0 if x == tileOverlap['xmin'] else overlap['left']
                    overlap['right'] = 0 if x + 1 == tileOverlap['xmax'] else overlap['right']
                if tileOverlap['range_y']:
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
        :param kwargs: additional parameters to use in determining format.
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

    @methodcache()
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
        :param args: parameters to pass to the tileIterator.
        :param kwargs: parameters to pass to the tileIterator.
        :returns: if onlyMinMax is true, this is a dictionary with keys min and
            max, each of which is a numpy array with the minimum and maximum of
            all of the bands.  If onlyMinMax is False, this is a dictionary
            with a single key 'histogram' that contains a list of histograms
            per band.  Each entry is a dictionary with min, max, range, hist,
            and bin_edges.  range is [min, (max + 1)].  hist is the counts
            (normalized if density is True) for each bin.  bin_edges is an
            array one longer than the hist array that contains the boundaries
            between bins.
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
            tilesum = numpy.array([
                numpy.sum(tile[:, :, idx]) for idx in range(tile.shape[2])], float)
            tilesum2 = numpy.array([
                numpy.sum(numpy.array(tile[:, :, idx], float) ** 2)
                for idx in range(tile.shape[2])], float)
            tilecount = tile.shape[0] * tile.shape[1]
            if results is None:
                results = {
                    'min': tilemin,
                    'max': tilemax,
                    'sum': tilesum,
                    'sum2': tilesum2,
                    'count': tilecount
                }
            else:
                results['min'] = numpy.minimum(results['min'], tilemin[:len(results['min'])])
                results['max'] = numpy.maximum(results['max'], tilemax[:len(results['min'])])
                results['sum'] += tilesum[:len(results['min'])]
                results['sum2'] += tilesum2[:len(results['min'])]
                results['count'] += tilecount
        results['mean'] = results['sum'] / results['count']
        results['stdev'] = numpy.maximum(
            results['sum2'] / results['count'] - results['mean'] ** 2,
            [0] * results['sum2'].shape[0]) ** 0.5
        results.pop('sum', None)
        results.pop('sum2', None)
        results.pop('count', None)
        if results is None or onlyMinMax:
            return results
        results['histogram'] = [{
            'min': results['min'][idx],
            'max': results['max'][idx],
            'mean': results['mean'][idx],
            'stdev': results['stdev'][idx],
            'range': ((results['min'][idx], results['max'][idx] + 1)
                      if histRange is None else histRange),
            'hist': None,
            'bin_edges': None,
            'density': bool(density),
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
                    entry['hist'] = entry['hist'].astype(float) / entry['samples']
        return results

    def _unstyledClassKey(self):
        """
        Create a class key that doesn't use style.  If already created, just
        return the created value.
        """
        if not hasattr(self, '_classkey_unstyled'):
            key = self._classkey
            if '__STYLEEND__' in key:
                parts = key.split('__STYLEEND__', 1)
                key = key.split('__STYLESTART__', 1)[0] + parts[1]
            key += '__unstyled'
            self._classkey_unstyled = key
        return self._classkey_unstyled

    def _scanForMinMax(self, dtype, frame=None, analysisSize=1024, onlyMinMax=True, **kwargs):
        """
        Scan the image at a lower resolution to find the minimum and maximum
        values.

        :param dtype: the numpy dtype.  Used for guessing the range.
        :param frame: the frame to use for auto-ranging.
        :param analysisSize: the size of the image to use for analysis.
        :param onlyMinMax: if True, only find the min and max.  If False, get
            the entire histogram.
        """
        self._setSkipStyle(True)
        try:
            self._bandRanges[frame] = self.histogram(
                dtype=dtype,
                onlyMinMax=onlyMinMax,
                output={'maxWidth': min(self.sizeX, analysisSize),
                        'maxHeight': min(self.sizeY, analysisSize)},
                resample=False,
                frame=frame, **kwargs)
            if self._bandRanges[frame]:
                self.logger.info('Style range is %r' % {
                    k: v for k, v in self._bandRanges[frame].items() if k in {
                        'min', 'max', 'mean', 'stdev'}})
        finally:
            self._setSkipStyle(False)

    def _validateMinMaxValue(self, value, frame, dtype):
        """
        Validate the min/max setting and return a specific string or float
        value and with any threshold.

        :param value: the specified value, 'auto', 'min', or 'max'.  'auto'
            uses the parameter specified in 'minmax' or 0 or 255 if the
            band's minimum is in the range [0, 254] and maximum is in the range
            [2, 255].  'min:<value>' and 'max:<value>' use the histogram to
            threshold the image based on the value.  'auto:<value>' applies a
            histogram threshold if the parameter specified in minmax is used.
        :param dtype: the numpy dtype.  Used for guessing the range.
        :param frame: the frame to use for auto-ranging.
        :returns: the validated value and a threshold from [0-1].
        """
        threshold = 0
        if value not in {'min', 'max', 'auto', 'full'}:
            try:
                if ':' in str(value) and value.split(':', 1)[0] in {'min', 'max', 'auto'}:
                    threshold = float(value.split(':', 1)[1])
                    value = value.split(':', 1)[0]
                else:
                    value = float(value)
            except ValueError:
                self.logger.warning('Style min/max value of %r is not valid; using "auto"', value)
                value = 'auto'
        if value in {'min', 'max', 'auto'} and (
                frame not in self._bandRanges or (
                    threshold and 'histogram' not in self._bandRanges[frame])):
            self._scanForMinMax(dtype, frame, onlyMinMax=not threshold)
        return value, threshold

    def _getMinMax(self, minmax, value, dtype, bandidx=None, frame=None):  # noqa
        """
        Get an appropriate minimum or maximum for a band.

        :param minmax: either 'min' or 'max'.
        :param value: the specified value, 'auto', 'min', or 'max'.  'auto'
            uses the parameter specified in 'minmax' or 0 or 255 if the
            band's minimum is in the range [0, 254] and maximum is in the range
            [2, 255].  'min:<value>' and 'max:<value>' use the histogram to
            threshold the image based on the value.  'auto:<value>' applies a
            histogram threshold if the parameter specified in minmax is used.
        :param dtype: the numpy dtype.  Used for guessing the range.
        :param bandidx: the index of the channel that could be used for
            determining the min or max.
        :param frame: the frame to use for auto-ranging.
        """
        frame = frame or 0
        value, threshold = self._validateMinMaxValue(value, frame, dtype)
        if value == 'full':
            value = 0
            if minmax != 'min':
                if dtype == numpy.uint16:
                    value = 65535
                elif dtype.kind == 'f':
                    value = 1
                else:
                    value = 255
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
                if threshold:
                    value = histogramThreshold(
                        self._bandRanges[frame]['histogram'][bandidx], threshold)
                else:
                    value = self._bandRanges[frame]['min'][bandidx]
            else:
                value = 0
        elif value == 'max':
            if bandidx is not None and self._bandRanges.get(frame):
                if threshold:
                    value = histogramThreshold(
                        self._bandRanges[frame]['histogram'][bandidx], threshold, True)
                else:
                    value = self._bandRanges[frame]['max'][bandidx]
            elif dtype == numpy.uint16:
                value = 65535
            elif dtype.kind == 'f':
                value = 1
            else:
                value = 255
        return float(value)

    def _applyStyleFunction(self, image, sc, stage, function=None):
        """
        Check if a style ahs a style function for the current stage.  If so,
        apply it.

        :param image: the numpy image to adjust.  This varies by stage:
            For pre, this is the source image.
            For preband, this is the band image (often the source image).
            For band, this is the scaled band image before palette has been
                applied.
            For postband, this is the output image at the current time.
            For main, this is the output image before adjusting to the target
                style.
            For post, this is the final output image.
        :param sc: the style context.
        :param stage: one of the stages: pre, preband, band, postband, main,
            post.
        :param function: if None, this is taken from the sc.style object using
            the appropriate band index.  Otherwise, this is a style: either a
            list of style objects, or a style object with name (the
            module.function_name), stage (either a stage or a list of stages
            that this function applies to), context (falsy to not pass the
            style context to the function, True to pass it as the parameter
            'context', or a string to pass it as a parameter of that name),
            parameters (a dictionary of parameters to pass to the function).
            If function is a string, it is shorthand for {'name': <function>}.
        :returns: the modified numpy image.
        """
        import importlib

        if function is None:
            function = (
                sc.style.get('function') if not hasattr(sc, 'styleIndex') else
                sc.style['bands'][sc.styleIndex].get('function'))
            if function is None:
                return image
        if isinstance(function, (list, tuple)):
            for func in function:
                image = self._applyStyleFunction(image, sc, stage, func)
            return image
        if isinstance(function, str):
            function = {'name': function}
        useOnStages = (
            [function['stage']] if isinstance(function.get('stage'), str)
            else function.get('stage', ['main', 'band']))
        if stage not in useOnStages:
            return image
        sc.stage = stage
        try:
            module_name, func_name = function['name'].rsplit('.', 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
        except Exception as exc:
            self._styleFunctionWarnings = getattr(self, '_styleFunctionWarnings', {})
            if function['name'] not in self._styleFunctionWarnings:
                self._styleFunctionWarnings[function['name']] = exc
                self.logger.exception('Failed to import style function %s' % function['name'])
            return image
        kwargs = function.get('parameters', {}).copy()
        if function.get('context'):
            kwargs['context' if function['context'] is True else function['context']] = sc
        try:
            return func(image, **kwargs)
        except Exception as exc:
            self._styleFunctionWarnings = getattr(self, '_styleFunctionWarnings', {})
            if function['name'] not in self._styleFunctionWarnings:
                self._styleFunctionWarnings[function['name']] = exc
                self.logger.exception('Failed to execute style function %s' % function['name'])
            return image

    def getICCProfiles(self, idx=None, onlyInfo=False):
        """
        Get a list of all ICC profiles that are available for the source, or
        get a specific profile.

        :param idx: a 0-based index into the profiles to get one profile, or
            None to get a list of all profiles.
        :param onlyInfo: if idx is None and this is true, just return the
            profile information.
        :returns: either one or a list of PIL.ImageCms.CmsProfile objects, or
            None if no profiles are available.  If a list, entries in the list
            may be None.
        """
        if not hasattr(self, '_iccprofiles'):
            return None
        results = []
        for pidx, prof in enumerate(self._iccprofiles):
            if idx is not None and pidx != idx:
                continue
            if hasattr(self, '_iccprofilesObjects') and self._iccprofilesObjects[pidx] is not None:
                prof = self._iccprofilesObjects[pidx]['profile']
            elif not isinstance(prof, PIL.ImageCms.ImageCmsProfile):
                prof = PIL.ImageCms.getOpenProfile(io.BytesIO(prof))
            if idx == pidx:
                return prof
            results.append(prof)
        if onlyInfo:
            results = [
                PIL.ImageCms.getProfileInfo(prof).strip() or 'present'
                if prof else None for prof in results]
        return results

    def _applyICCProfile(self, sc, frame):
        """
        Apply an ICC profile to an image.

        :param sc: the style context.
        :param frame: the frame to use for auto ranging.
        :returns: an image with the icc profile, if any, applied.
        """
        profileIdx = frame if frame and len(self._iccprofiles) >= frame + 1 else 0
        sc.iccimage = sc.image
        sc.iccapplied = False
        if not self._iccprofiles[profileIdx]:
            return sc.image
        if not hasattr(self, '_iccprofilesObjects'):
            self._iccprofilesObjects = [None] * len(self._iccprofiles)
        image = _imageToPIL(sc.image)
        mode = image.mode
        if hasattr(PIL.ImageCms, 'Intent'):  # PIL >= 9
            intent = getattr(PIL.ImageCms.Intent, str(sc.style.get('icc')).upper(),
                             PIL.ImageCms.Intent.PERCEPTUAL)
        else:
            intent = getattr(PIL.ImageCms, 'INTENT_' + str(sc.style.get('icc')).upper(),
                             PIL.ImageCms.INTENT_PERCEPTUAL)
        if not hasattr(self, '_iccsrgbprofile'):
            try:
                self._iccsrgbprofile = PIL.ImageCms.createProfile('sRGB')
            except ImportError:
                self._iccsrgbprofile = None
                self.logger.warning(
                    'Failed to import PIL.ImageCms.  Cannot perform ICC '
                    'color adjustments.  Does your platform support '
                    'PIL.ImageCms?')
        if self._iccsrgbprofile is None:
            return sc.image
        try:
            key = (mode, intent)
            if self._iccprofilesObjects[profileIdx] is None:
                self._iccprofilesObjects[profileIdx] = {
                    'profile': self.getICCProfiles(profileIdx)
                }
                if key not in self._iccprofilesObjects[profileIdx]:
                    self._iccprofilesObjects[profileIdx][key] = \
                        PIL.ImageCms.buildTransformFromOpenProfiles(
                            self._iccprofilesObjects[profileIdx]['profile'],
                            self._iccsrgbprofile, mode, mode,
                            renderingIntent=intent)
                    self.logger.debug(
                        'Created an ICC profile transform for mode %s, intent %s', mode, intent)
            transform = self._iccprofilesObjects[profileIdx][key]

            PIL.ImageCms.applyTransform(image, transform, inPlace=True)
            sc.iccimage = _imageToNumpy(image)[0]
            sc.iccapplied = True
        except Exception as exc:
            if not hasattr(self, '_iccerror'):
                self._iccerror = exc
                self.logger.exception('Failed to apply ICC profile')
        return sc.iccimage

    def _setSkipStyle(self, setSkip=False):
        if setSkip:
            self._unlocked_classkey = self._classkey
            if hasattr(self, 'cache_lock'):
                with self.cache_lock:
                    self._classkeyLock = self._styleLock
            self._skipStyle = True
            # Divert the tile cache while querying unstyled tiles
            self._classkey = self._unstyledClassKey()
        else:
            del self._skipStyle
            self._classkey = self._unlocked_classkey

    def _applyStyle(self, image, style, x, y, z, frame=None):  # noqa
        """
        Apply a style to a numpy image.

        :param image: the image to modify.
        :param style: a style object.
        :param x: the x tile position; used for multi-frame styles.
        :param y: the y tile position; used for multi-frame styles.
        :param z: the z tile position; used for multi-frame styles.
        :param frame: the frame to use for auto ranging.
        :returns: a styled image.
        """
        sc = types.SimpleNamespace(
            image=image, originalStyle=style, x=x, y=y, z=z, frame=frame,
            mainImage=image, mainFrame=frame, dtype=None, axis=None)
        if style is None or ('icc' in style and len(style) == 1):
            sc.style = {'icc': (style or {}).get(
                'icc', config.getConfig('icc_correction', True)), 'bands': []}
        else:
            sc.style = style if 'bands' in style else {'bands': [style]}
            sc.dtype = style.get('dtype')
            sc.axis = style.get('axis')
        if hasattr(self, '_iccprofiles') and sc.style.get(
                'icc', config.getConfig('icc_correction', True)):
            image = self._applyICCProfile(sc, frame)
        if style is None or ('icc' in style and len(style) == 1):
            sc.output = image
        else:
            sc.output = numpy.zeros((image.shape[0], image.shape[1], 4), float)
        image = self._applyStyleFunction(image, sc, 'pre')
        for eidx, entry in enumerate(sc.style['bands']):
            sc.styleIndex = eidx
            sc.dtype = sc.dtype if sc.dtype is not None else entry.get('dtype')
            sc.axis = sc.axis if sc.axis is not None else entry.get('axis')
            sc.bandidx = 0 if image.shape[2] <= 2 else 1
            sc.band = None
            if ((entry.get('frame') is None and not entry.get('framedelta')) or
                    entry.get('frame') == frame):
                image = sc.mainImage
                frame = sc.mainFrame
            else:
                frame = entry['frame'] if entry.get('frame') is not None else (
                    sc.mainFrame + entry['framedelta'])
                self._setSkipStyle(True)
                try:
                    image = self.getTile(x, y, z, frame=frame, numpyAllowed=True)
                    image = image[:sc.mainImage.shape[0],
                                  :sc.mainImage.shape[1],
                                  :sc.mainImage.shape[2]]
                finally:
                    self._setSkipStyle(False)
            if (isinstance(entry.get('band'), int) and
                    entry['band'] >= 1 and entry['band'] <= image.shape[2]):
                sc.bandidx = entry['band'] - 1
            sc.composite = entry.get('composite', 'lighten')
            if (hasattr(self, '_bandnames') and entry.get('band') and
                    str(entry['band']).lower() in self._bandnames and
                    image.shape[2] > self._bandnames[str(entry['band']).lower()]):
                sc.bandidx = self._bandnames[str(entry['band']).lower()]
            if entry.get('band') == 'red' and image.shape[2] > 2:
                sc.bandidx = 0
            elif entry.get('band') == 'blue' and image.shape[2] > 2:
                sc.bandidx = 2
                sc.band = image[:, :, 2]
            elif entry.get('band') == 'alpha':
                sc.bandidx = image.shape[2] - 1 if image.shape[2] in (2, 4) else None
                sc.band = (image[:, :, -1] if image.shape[2] in (2, 4) else
                           numpy.full(image.shape[:2], 255, numpy.uint8))
                sc.composite = entry.get('composite', 'multiply')
            if sc.band is None:
                sc.band = image[:, :, sc.bandidx]
            sc.band = self._applyStyleFunction(sc.band, sc, 'preband')
            sc.palette = getPaletteColors(entry.get(
                'palette', ['#000', '#FFF']
                if entry.get('band') != 'alpha' else ['#FFF0', '#FFFF']))
            sc.discrete = entry.get('scheme') == 'discrete'
            sc.palettebase = numpy.linspace(0, 1, len(sc.palette), endpoint=True)
            sc.nodata = entry.get('nodata')
            sc.min = self._getMinMax(
                'min', entry.get('min', 'auto'), image.dtype, sc.bandidx, frame)
            sc.max = self._getMinMax(
                'max', entry.get('max', 'auto'), image.dtype, sc.bandidx, frame)
            sc.clamp = entry.get('clamp', True)
            delta = sc.max - sc.min if sc.max != sc.min else 1
            if sc.nodata is not None:
                sc.mask = sc.band != float(sc.nodata)
            else:
                sc.mask = numpy.full(image.shape[:2], True)
            sc.band = (sc.band - sc.min) / delta
            if not sc.clamp:
                sc.mask = sc.mask & (sc.band >= 0) & (sc.band <= 1)
            sc.band = self._applyStyleFunction(sc.band, sc, 'band')
            # To implement anything other multiply or lighten, we should mimic
            # mapnik (and probably delegate to a family of functions).
            # mapnik's options are: clear src dst src_over dst_over src_in
            # dst_in src_out dst_out src_atop dst_atop xor plus minus multiply
            # screen overlay darken lighten color_dodge color_burn hard_light
            # soft_light difference exclusion contrast invert grain_merge
            # grain_extract hue saturation color value linear_dodge linear_burn
            # divide.
            # See https://docs.gimp.org/en/gimp-concepts-layer-modes.html for
            # some details.
            for channel in range(4):
                if numpy.all(sc.palette[:, channel] == sc.palette[0, channel]):
                    if ((sc.palette[0, channel] == 0 and sc.composite != 'multiply') or
                            (sc.palette[0, channel] == 255 and sc.composite == 'multiply')):
                        continue
                    clrs = numpy.full(sc.band.shape, sc.palette[0, channel], dtype=sc.band.dtype)
                else:
                    # Don't recompute if the sc.palette is repeated two channels
                    # in a row.
                    if not channel or numpy.any(
                            sc.palette[:, channel] != sc.palette[:, channel - 1]):
                        if not sc.discrete:
                            clrs = numpy.interp(sc.band, sc.palettebase, sc.palette[:, channel])
                        else:
                            clrs = sc.palette[
                                numpy.floor(sc.band * len(sc.palette)).astype(int).clip(
                                    0, len(sc.palette) - 1), channel]
                if sc.composite == 'multiply':
                    if eidx:
                        sc.output[:sc.mask.shape[0], :sc.mask.shape[1], channel] = numpy.multiply(
                            sc.output[:sc.mask.shape[0], :sc.mask.shape[1], channel],
                            numpy.where(sc.mask, clrs / 255, 1))
                else:
                    if not eidx:
                        sc.output[:sc.mask.shape[0],
                                  :sc.mask.shape[1],
                                  channel] = numpy.where(sc.mask, clrs, 0)
                    else:
                        sc.output[:sc.mask.shape[0], :sc.mask.shape[1], channel] = numpy.maximum(
                            sc.output[:sc.mask.shape[0], :sc.mask.shape[1], channel],
                            numpy.where(sc.mask, clrs, 0))
            sc.output = self._applyStyleFunction(sc.output, sc, 'postband')
        sc.output = self._applyStyleFunction(sc.output, sc, 'main')
        if sc.dtype == 'uint16':
            sc.output = (sc.output * 65535 / 255).astype(numpy.uint16)
        elif sc.dtype == 'float':
            sc.output /= 255
        if sc.axis is not None and 0 <= int(sc.axis) < sc.output.shape[2]:
            sc.output = sc.output[:, :, sc.axis:sc.axis + 1]
        sc.output = self._applyStyleFunction(sc.output, sc, 'post')
        return sc.output

    def _outputTileNumpyStyle(self, tile, applyStyle, x, y, z, frame=None):
        """
        Convert a tile to a numpy array.  Optionally apply the style to a tile.
        Always returns a numpy tile.

        :param tile: the tile to convert.
        :param applyStyle: if True and there is a style, apply it.
        :param x: the x tile position; used for multi-frame styles.
        :param y: the y tile position; used for multi-frame styles.
        :param z: the z tile position; used for multi-frame styles.
        :param frame: the frame to use for auto-ranging.
        :returns: a numpy array and a target PIL image mode.
        """
        tile, mode = _imageToNumpy(tile)
        if applyStyle and (getattr(self, 'style', None) or hasattr(self, '_iccprofiles')):
            with self._styleLock:
                if not getattr(self, '_skipStyle', False):
                    tile = self._applyStyle(tile, getattr(self, 'style', None), x, y, z, frame)
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
        :param numpyAllowed: True if a numpy image may be returned.  'always'
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
        hasStyle = (
            len(set(getattr(self, 'style', {})) - {'icc'}) or
            getattr(self, 'style', {}).get('icc', config.getConfig('icc_correction', True)))
        if (tileEncoding not in (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY) and
                numpyAllowed != 'always' and tileEncoding == self.encoding and
                not isEdge and (not applyStyle or not hasStyle)):
            return tile
        mode = None
        if (numpyAllowed == 'always' or tileEncoding == TILE_FORMAT_NUMPY or
                (applyStyle and hasStyle) or isEdge):
            tile, mode = self._outputTileNumpyStyle(
                tile, applyStyle, x, y, z, self._getFrame(**kwargs))
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
        # If we can't redirect, but the tile is read from a file in the desired
        # output format, just read the file
        if getattr(tile, 'fp', None) and self._pilFormatMatches(tile):
            tile.fp.seek(0)
            return tile.fp.read()
        result = _encodeImageBinary(
            tile, self.encoding, self.jpegQuality, self.jpegSubsampling, self.tiffCompression)
        return result

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
        Return metadata about this tile source.  This contains

            :levels: number of tile levels in this image.
            :sizeX: width of the image in pixels.
            :sizeY: height of the image in pixels.
            :tileWidth: width of a tile in pixels.
            :tileHeight: height of a tile in pixels.
            :magnification: if known, the magnificaiton of the image.
            :mm_x: if known, the width of a pixel in millimeters.
            :mm_y: if known, the height of a pixel in millimeters.

            In addition to the keys that listed above, tile sources that expose
            multiple frames will also contain

            :frames: a list of frames.  Each frame entry is a dictionary with

                :Frame: a 0-values frame index (the location in the list)
                :Channel: optional.  The name of the channel, if known
                :IndexC: optional if unique.  A 0-based index into the channel
                    list
                :IndexT: optional if unique.  A 0-based index for time values
                :IndexZ: optional if unique.  A 0-based index for z values
                :IndexXY: optional if unique.  A 0-based index for view (xy)
                    values
                :Index<axis>: optional if unique.  A 0-based index for an
                    arbitrary axis.
                :Index: a 0-based index of non-channel unique sets.  If the
                    frames vary only by channel and are adjacent, they will
                    have the same index.

            :IndexRange: a dictionary of the number of unique index values from
                frames if greater than 1 (e.g., if an entry like IndexXY is not
                present, then all frames either do not have that value or have
                a value of 0).
            :IndexStride: a dictionary of the spacing between frames where
                unique axes values change.
            :channels: optional.  If known, a list of channel names
            :channelmap: optional.  If known, a dictionary of channel names
                with their offset into the channel list.

        Note that this does nto include band information, though some tile
        sources may do so.
        """
        mag = self.getNativeMagnification()
        return JSONDict({
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'magnification': mag['magnification'],
            'mm_x': mag['mm_x'],
            'mm_y': mag['mm_y'],
        })

    @property
    def metadata(self):
        return self.getMetadata()

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
        refkeys = {'IndexC'}
        index = 0
        for idx, frame in enumerate(metadata['frames']):
            refkeys |= {key for key in frame
                        if key.startswith('Index') and len(key.split('Index', 1)[1])}
            for key in refkeys:
                if key in frame and frame[key] + 1 > maxref.get(key, 0):
                    maxref[key] = frame[key] + 1
            frame['Frame'] = idx
            if idx and (any(
                    frame.get(key) != metadata['frames'][idx - 1].get(key)
                    for key in refkeys if key != 'IndexC') or not any(
                    metadata['frames'][idx].get(key) for key in refkeys)):
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

    def getOneBandInformation(self, band):
        """
        Get band information for a single band.

        :param band: a 1-based band.
        :returns: a dictionary of band information.  See getBandInformation.
        """
        return self.getBandInformation()[band]

    def getBandInformation(self, statistics=False, **kwargs):
        """
        Get information about each band in the image.

        :param statistics: if True, compute statistics if they don't already
            exist.
        :returns: a dictionary of one dictionary per band.  Each dictionary
            contains known values such as interpretation, min, max, mean,
            stdev.
        """
        if not getattr(self, '_bandInfo', None):
            bandInterp = {
                1: ['gray'],
                2: ['gray', 'alpha'],
                3: ['red', 'green', 'blue'],
                4: ['red', 'green', 'blue', 'alpha']}
            if not statistics:
                if not getattr(self, '_bandInfoNoStats', None):
                    tile = self.getSingleTile()['tile']
                    bands = tile.shape[2] if len(tile.shape) > 2 else 1
                    interp = bandInterp.get(bands, bandInterp[3])
                    bandInfo = {
                        idx + 1: {'interpretation': interp[idx] if idx < len(interp)
                                  else 'unknown'} for idx in range(bands)}
                    self._bandInfoNoStats = bandInfo
                return self._bandInfoNoStats
            analysisSize = 2048
            histogram = self.histogram(
                onlyMinMax=True,
                output={'maxWidth': min(self.sizeX, analysisSize),
                        'maxHeight': min(self.sizeY, analysisSize)},
                resample=False,
                **kwargs)
            bands = histogram['min'].shape[0]
            interp = bandInterp.get(bands, 3)
            bandInfo = {
                idx + 1: {'interpretation': interp[idx] if idx < len(interp)
                          else 'unknown'} for idx in range(bands)}
            for key in {'min', 'max', 'mean', 'stdev'}:
                if key in histogram:
                    for idx in range(bands):
                        bandInfo[idx + 1][key] = histogram[key][idx]
            self._bandInfo = bandInfo
        return self._bandInfo

    def _getFrame(self, frame=None, **kwargs):
        """
        Get the current frame number.  If a style is used that completely
        specified the frame, use that value instead.

        :param frame: an integer or string with the frame number.
        :returns: an integer frame number.
        """
        frame = int(frame or 0)
        if (not getattr(self, '_skipStyle', None) and
                hasattr(self, '_style') and 'bands' in self.style and
                len(self.style['bands']) and
                all(entry.get('frame') is not None for entry in self.style['bands'])):
            frame = int(self.style['bands'][0]['frame'])
        return frame

    def _xyzInRange(self, x, y, z, frame=None, numFrames=None):
        """
        Check if a tile at x, y, z is in range based on self.levels,
        self.tileWidth, self.tileHeight, self.sizeX, and self.sizeY,  Raise an
        ``TileSourceXYZRangeError`` exception if not.
        """
        if z < 0 or z >= self.levels:
            raise exceptions.TileSourceXYZRangeError('z layer does not exist')
        scale = 2 ** (self.levels - 1 - z)
        offsetx = x * self.tileWidth * scale
        if not (0 <= offsetx < self.sizeX):
            raise exceptions.TileSourceXYZRangeError('x is outside layer')
        offsety = y * self.tileHeight * scale
        if not (0 <= offsety < self.sizeY):
            raise exceptions.TileSourceXYZRangeError('y is outside layer')
        if frame is not None and numFrames is not None:
            if frame < 0 or frame >= numFrames:
                raise exceptions.TileSourceXYZRangeError('Frame does not exist')

    def _xyzToCorners(self, x, y, z):
        """
        Convert a tile in x, y, z to corners and scale factor.   The corners
        are in full resolution image coordinates.  The scale is always a power
        of two >= 1.

        To convert the output to the resolution at the specified z level,
        integer divide the corners by the scale (e.g., x0z = x0 // scale).

        :param x, y, z: the tile position.
        :returns: x0, y0, x1, y1, scale.
        """
        step = int(2 ** (self.levels - 1 - z))
        x0 = x * step * self.tileWidth
        x1 = min((x + 1) * step * self.tileWidth, self.sizeX)
        y0 = y * step * self.tileHeight
        y1 = min((y + 1) * step * self.tileHeight, self.sizeY)
        return x0, y0, x1, y1, step

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                sparseFallback=False, frame=None):
        """
        Get a tile from a tile source, returning it as an binary image, a PIL
        image, or a numpy array.

        :param x: the 0-based x position of the tile on the specified z level.
            0 is left.
        :param y: the 0-based y position of the tile on the specified z level.
            0 is top.
        :param z: the z level of the tile.  May range from [0, self.levels],
            where 0 is the lowest resolution, single tile for the whole source.
        :param pilImageAllowed: True if a PIL image may be returned.
        :param numpyAllowed: True if a numpy image may be returned.  'always'
            to return a numpy array.
        :param sparseFallback: if False and a tile doesn't exist, raise an
            error.  If True, check if a lower resolution tile exists, and, if
            so, interpolate the needed data for this tile.
        :param frame: the frame number within the tile source.  None is the
            same as 0 for multi-frame sources.
        :returns: either a numpy array, a PIL image, or a memory object with an
            image file.
        """
        raise NotImplementedError()

    def getTileMimeType(self):
        """
        Return the default mimetype for image tiles.

        :returns: the mime type of the tile.
        """
        return TileOutputMimeTypes.get(self.encoding, 'image/jpeg')

    @methodcache()
    def getThumbnail(self, width=None, height=None, **kwargs):
        """
        Get a basic thumbnail from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, a default value is
        used.  If both are given, the thumbnail will be no larger than either
        size.  A thumbnail has the same options as a region except that it
        always includes the entire image and has a default size of 256 x 256.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: thumbData, thumbMime: the image data and the mime type.
        """
        if ((width is not None and (not isinstance(width, int) or width < 2)) or
                (height is not None and (not isinstance(height, int) or height < 2))):
            raise ValueError('Invalid width or height.  Minimum value is 2.')
        if width is None and height is None:
            width = height = 256
        params = dict(kwargs)
        params['output'] = {'maxWidth': width, 'maxHeight': height}
        params.pop('region', None)
        return self.getRegion(**params)

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

            :left: the left edge (inclusive) of the region to process.
            :top: the top edge (inclusive) of the region to process.
            :right: the right edge (exclusive) of the region to process.
            :bottom: the bottom edge (exclusive) of the region to process.
            :width: the width of the region to process.
            :height: the height of the region to process.
            :units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.

        :param sourceScale: a dictionary of optional values which specify the
            scale of the source region.  Required if the sourceRegion is
            in "mag_pixels" units.

            :magnification: the magnification ratio.
            :mm_x: the horizontal size of a pixel in millimeters.
            :mm_y: the vertical size of a pixel in millimeters.

        :param targetScale: a dictionary of optional values which specify the
            scale of the target region.  Required in targetUnits is in
            "mag_pixels" units.

            :magnification: the magnification ratio.
            :mm_x: the horizontal size of a pixel in millimeters.
            :mm_y: the vertical size of a pixel in millimeters.

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
        :param kwargs: optional arguments.  Some options are region, output,
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
        tiled = TILE_FORMAT_IMAGE in format and kwargs.get('encoding') == 'TILED'
        image = None
        for tile in self._tileIterator(iterInfo):
            # Add each tile to the image
            subimage, _ = _imageToNumpy(tile['tile'])
            x0, y0 = tile['x'] - left, tile['y'] - top
            if x0 < 0:
                subimage = subimage[:, -x0:]
                x0 = 0
            if y0 < 0:
                subimage = subimage[-y0:, :]
                y0 = 0
            subimage = subimage[:min(subimage.shape[0], regionHeight - y0),
                                :min(subimage.shape[1], regionWidth - x0)]
            image = self._addRegionTileToImage(
                image, subimage, x0, y0, regionWidth, regionHeight, tiled, tile, **kwargs)
        # Scale if we need to
        outWidth = int(math.floor(outWidth))
        outHeight = int(math.floor(outHeight))
        if tiled:
            return self._encodeTiledImage(image, outWidth, outHeight, iterInfo, **kwargs)
        if outWidth != regionWidth or outHeight != regionHeight:
            dtype = image.dtype
            image = _imageToPIL(image, mode).resize(
                (outWidth, outHeight),
                getattr(PIL.Image, 'Resampling', PIL.Image).BICUBIC
                if outWidth > regionWidth else
                getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)
            if dtype == numpy.uint16 and TILE_FORMAT_NUMPY in format:
                image = _imageToNumpy(image)[0].astype(dtype) * 257
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if kwargs.get('fill') and maxWidth and maxHeight:
            image = _letterboxImage(_imageToPIL(image, mode), maxWidth, maxHeight, kwargs['fill'])
        return _encodeImage(image, format=format, **kwargs)

    def _addRegionTileToImage(
            self, image, subimage, x, y, width, height, tiled=False, tile=None, **kwargs):
        """
        Add a subtile to a larger image.

        :param image: the output image record.  None for not created yet.
        :param subimage: a numpy array with the sub-image to add.
        :param x: the location of the upper left point of the sub-image within
            the output image.
        :param y: the location of the upper left point of the sub-image within
            the output image.
        :param width: the output image size.
        :param height: the output image size.
        :param tiled: true to generate a tiled output image.
        :param tile: the original tile record with the current scale, etc.
        :returns: the output image record.
        """
        if tiled:
            return self._addRegionTileToTiled(image, subimage, x, y, width, height, tile, **kwargs)
        if image is None:
            try:
                image = numpy.zeros(
                    (height, width, subimage.shape[2]),
                    dtype=subimage.dtype)
            except MemoryError:
                raise exceptions.TileSourceError(
                    'Insufficient memory to get region of %d x %d pixels.' % (
                        width, height))
        image, subimage = _makeSameChannelDepth(image, subimage)
        image[y:y + subimage.shape[0], x:x + subimage.shape[1], :] = subimage
        return image

    def _vipsAddAlphaBand(self, vimg, *otherImages):
        """
        Add an alpha band to a vips image.  The alpha value is either 1, 255,
        or 65535 depending on the max value in the image and any other images
        passed for reference.

        :param vimg: the image to modify.
        :param otherImages: a list of other images to use for determining the
            alpha value.
        :returns: the original image with an alpha band.
        """
        maxValue = vimg.max()
        for img in otherImages:
            maxValue = max(maxValue, img.max())
        alpha = 1
        if maxValue >= 2 and maxValue < 2**9:
            alpha = 255
        elif maxValue >= 2**8 and maxValue < 2**17:
            alpha = 65535
        return vimg.bandjoin(alpha)

    def _addRegionTileToTiled(self, image, subimage, x, y, width, height, tile=None, **kwargs):
        """
        Add a subtile to a vips image.

        :param image: an object with information on the output.
        :param subimage: a numpy array with the sub-image to add.
        :param x: the location of the upper left point of the sub-image within
            the output image.
        :param y: the location of the upper left point of the sub-image within
            the output image.
        :param width: the output image size.
        :param height: the output image size.
        :param tile: the original tile record with the current scale, etc.
        :returns: the output object.
        """
        import pyvips

        if subimage.dtype.char not in dtypeToGValue:
            subimage = subimage.astype('d')
        vimgMem = pyvips.Image.new_from_memory(
            numpy.ascontiguousarray(subimage).data,
            subimage.shape[1], subimage.shape[0], subimage.shape[2],
            dtypeToGValue[subimage.dtype.char])
        vimg = pyvips.Image.new_temp_file('%s.v')
        vimgMem.write(vimg)
        if image is None:
            image = {
                'width': width,
                'height': height,
                'mm_x': tile.get('mm_x') if tile else None,
                'mm_y': tile.get('mm_y') if tile else None,
                'magnification': tile.get('magnification') if tile else None,
                'channels': subimage.shape[2],
                'strips': {},
            }
        if y not in image['strips']:
            image['strips'][y] = vimg
            if not x:
                return image
        if image['strips'][y].bands + 1 == vimg.bands:
            image['strips'][y] = self._vipsAddAlphaBand(image['strips'][y], vimg)
        elif vimg.bands + 1 == image['strips'][y].bands:
            vimg = self._vipsAddAlphaBand(vimg, image['strips'][y])
        image['strips'][y] = image['strips'][y].insert(vimg, x, 0, expand=True)
        return image

    def _encodeTiledImage(self, image, outWidth, outHeight, iterInfo, **kwargs):
        """
        Given an image record of a set of vips image strips, generate a tiled
        tiff file at the specified output size.

        :param image: a record with partial vips images and the current output
            size.
        :param outWidth: the output size after scaling and before any
            letterboxing.
        :param outHeight: the output size after scaling and before any
            letterboxing.
        :param iterInfo: information about the region based on the tile
            iterator.

        Additional parameters are available.

        :param fill: a color to use in letterboxing.
        :param maxWidth: the output size if letterboxing is applied.
        :param maxHeight: the output size if letterboxing is applied.
        :param compression: the internal compression format.  This can handle
            a variety of options similar to the converter utility.
        :returns: a pathlib.Path of the output file and the output mime type.
        """
        vimg = image['strips'][0]
        for y in sorted(image['strips'].keys())[1:]:
            if image['strips'][y].bands + 1 == vimg.bands:
                image['strips'][y] = self._vipsAddAlphaBand(image['strips'][y], vimg)
            elif vimg.bands + 1 == image['strips'][y].bands:
                vimg = self._vipsAddAlphaBand(vimg, image['strips'][y])
            vimg = vimg.insert(image['strips'][y], 0, y, expand=True)

        if outWidth != image['width'] or outHeight != image['height']:
            scale = outWidth / image['width']
            vimg = vimg.resize(outWidth / image['width'], vscale=outHeight / image['height'])
            image['width'] = outWidth
            image['height'] = outHeight
            image['mm_x'] = image['mm_x'] / scale if image['mm_x'] else image['mm_x']
            image['mm_y'] = image['mm_y'] / scale if image['mm_y'] else image['mm_y']
            image['magnification'] = (
                image['magnification'] * scale
                if image['magnification'] else image['magnification'])
        return self._encodeTiledImageFromVips(vimg, iterInfo, image, **kwargs)

    def _encodeTiledImageFromVips(self, vimg, iterInfo, image, **kwargs):
        """
        Save a vips image as a tiled tiff.

        :param vimg: a vips image.
        :param iterInfo: information about the region based on the tile
            iterator.
        :param image: a record with partial vips images and the current output
            size.

        Additional parameters are available.

        :param compression: the internal compression format.  This can handle
            a variety of options similar to the converter utility.
        :returns: a pathlib.Path of the output file and the output mime type.
        """
        import pyvips

        convertParams = _vipsParameters(defaultCompression='lzw', **kwargs)
        vimg = _vipsCast(vimg, convertParams['compression'] in {'webp', 'jpeg'})
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if (kwargs.get('fill') and str(kwargs.get('fill')).lower() != 'none' and
                maxWidth and maxHeight and
                (maxWidth > image['width'] or maxHeight > image['height'])):
            corner, fill = False, kwargs.get('fill')
            if fill.lower().startswith('corner:'):
                corner, fill = True, fill.split(':', 1)[1]
            color = PIL.ImageColor.getcolor(
                fill, ['L', 'LA', 'RGB', 'RGBA'][vimg.bands - 1])
            if isinstance(color, int):
                color = [color]
            lbimage = pyvips.Image.black(maxWidth, maxHeight, bands=vimg.bands)
            lbimage = lbimage.cast(vimg.format)
            lbimage = lbimage.draw_rect(
                [c * (257 if vimg.format == pyvips.BandFormat.USHORT else 1) for c in color],
                0, 0, maxWidth, maxHeight, fill=True)
            vimg = lbimage.insert(
                vimg,
                (maxWidth - image['width']) // 2 if not corner else 0,
                (maxHeight - image['height']) // 2 if not corner else 0)
        if image['mm_x'] and image['mm_y']:
            vimg = vimg.copy(xres=1 / image['mm_x'], yres=1 / image['mm_y'])
        fd, outputPath = tempfile.mkstemp('.tiff', 'tiledRegion_')
        os.close(fd)
        try:
            vimg.write_to_file(outputPath, **convertParams)
            return pathlib.Path(outputPath), TileOutputMimeTypes['TILED']
        except Exception as exc:
            try:
                pathlib.Path(outputPath).unlink()
            except Exception:
                pass
            raise exc

    def tileFrames(self, format=(TILE_FORMAT_IMAGE, ), frameList=None,
                   framesAcross=None, **kwargs):
        """
        Given the parameters for getRegion, plus a list of frames and the
        number of frames across, make a larger image composed of a region from
        each listed frame composited together.

        :param format: the desired format or a tuple of allowed formats.
            Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
            TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding may be
            specified.
        :param frameList: None for all frames, or a list of 0-based integers.
        :param framesAcross: the number of frames across the final image.  If
            unspecified, this is the ceiling of sqrt(number of frames in frame
            list).
        :param kwargs: optional arguments.  Some options are region, output,
            encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
            tileIterator.
        :returns: regionData, formatOrRegionMime: the image data and either the
            mime type, if the format is TILE_FORMAT_IMAGE, or the format.
        """
        lastlog = time.time()
        kwargs = kwargs.copy()
        kwargs.pop('tile_position', None)
        kwargs.pop('frame', None)
        numFrames = len(self.getMetadata().get('frames', [0]))
        if frameList:
            frameList = [f for f in frameList if f >= 0 and f < numFrames]
        if not frameList:
            frameList = list(range(numFrames))
        if len(frameList) == 1:
            return self.getRegion(format=format, frame=frameList[0], **kwargs)
        if not framesAcross:
            framesAcross = int(math.ceil(len(frameList) ** 0.5))
        framesAcross = min(len(frameList), framesAcross)
        framesHigh = int(math.ceil(len(frameList) / framesAcross))
        if not isinstance(format, (tuple, set, list)):
            format = (format, )
        tiled = TILE_FORMAT_IMAGE in format and kwargs.get('encoding') == 'TILED'
        iterInfo = self._tileIteratorInfo(frame=frameList[0], **kwargs)
        if iterInfo is None:
            image = PIL.Image.new('RGB', (0, 0))
            return _encodeImage(image, format=format, **kwargs)
        frameWidth = iterInfo['output']['width']
        frameHeight = iterInfo['output']['height']
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if kwargs.get('fill') and maxWidth and maxHeight:
            frameWidth, frameHeight = maxWidth, maxHeight
        outWidth = frameWidth * framesAcross
        outHeight = frameHeight * framesHigh
        tile = next(self._tileIterator(iterInfo))
        image = None
        for idx, frame in enumerate(frameList):
            subimage, _ = self.getRegion(format=TILE_FORMAT_NUMPY, frame=frame, **kwargs)
            offsetX = (idx % framesAcross) * frameWidth
            offsetY = (idx // framesAcross) * frameHeight
            if time.time() - lastlog > 10:
                self.logger.info(
                    'Tiling frame %d (%d/%d), offset %dx%d',
                    frame, idx, len(frameList), offsetX, offsetY)
                lastlog = time.time()
            else:
                self.logger.debug(
                    'Tiling frame %d (%d/%d), offset %dx%d',
                    frame, idx, len(frameList), offsetX, offsetY)
            image = self._addRegionTileToImage(
                image, subimage, offsetX, offsetY, outWidth, outHeight, tiled,
                tile=tile, **kwargs)
        if tiled:
            return self._encodeTiledImage(image, outWidth, outHeight, iterInfo, **kwargs)
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

            :x, y: (left, top) coordinates in current magnification pixels
            :width, height: size of current tile in current magnification pixels
            :tile: cropped tile image
            :format: format of the tile
            :level: level of the current tile
            :level_x, level_y: the tile reference number within the level.
                Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
                yielded may not be (0, 0) if a region is specified.
            :tile_position: a dictionary of the tile position within the
                iterator, containing:

                :level_x, level_y: the tile reference number within the level.
                :region_x, region_y: 0, 0 is the first tile in the full
                    iteration (when not restricting the iteration to a single
                    tile).
                :position: a 0-based value for the tile within the full
                    iteration.

            :iterator_range: a dictionary of the output range of the iterator:

                :level_x_min, level_x_max: the tiles that are be included
                    during the full iteration: [layer_x_min, layer_x_max).
                :level_y_min, level_y_max: the tiles that are be included
                    during the full iteration: [layer_y_min, layer_y_max).
                :region_x_max, region_y_max: the number of tiles included during
                    the full iteration.   This is layer_x_max - layer_x_min,
                    layer_y_max - layer_y_min.
                :position: the total number of tiles included in the full
                    iteration.  This is region_x_max * region_y_max.

            :magnification: magnification of the current tile
            :mm_x, mm_y: size of the current tile pixel in millimeters.
            :gx, gy: (left, top) coordinates in maximum-resolution pixels
            :gwidth, gheight: size of of the current tile in maximum-resolution
                pixels.
            :tile_overlap: the amount of overlap with neighboring tiles (left,
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
        :param resample: If True or one of PIL.Image.Resampling.NEAREST,
            LANCZOS, BILINEAR, or BICUBIC to resample tiles that are not the
            target output size.  Tiles that are resampled will have additional
            dictionary entries of:

            :scaled: the scaling factor that was applied (less than 1 is
                downsampled).
            :tile_x, tile_y: (left, top) coordinates before scaling
            :tile_width, tile_height: size of the current tile before
                scaling.
            :tile_magnification: magnification of the current tile before
                scaling.
            :tile_mm_x, tile_mm_y: size of a pixel in a tile in millimeters
                before scaling.

            Note that scipy.misc.imresize uses PIL internally.
        :param region: a dictionary of optional values which specify the part
            of the image to process:

            :left: the left edge (inclusive) of the region to process.
            :top: the top edge (inclusive) of the region to process.
            :right: the right edge (exclusive) of the region to process.
            :bottom: the bottom edge (exclusive) of the region to process.
            :width: the width of the region to process.
            :height: the height of the region to process.
            :units: either 'base_pixels' (default), 'pixels', 'mm', or
                'fraction'.  base_pixels are in maximum resolution pixels.
                pixels is in the specified magnification pixels.  mm is in the
                specified magnification scale.  fraction is a scale of 0 to 1.
                pixels and mm are only available if the magnification and mm
                per pixel are defined for the image.

        :param output: a dictionary of optional values which specify the size
            of the output.

            :maxWidth: maximum width in pixels.  If either maxWidth or maxHeight
                is specified, magnification, mm_x, and mm_y are ignored.
            :maxHeight: maximum height in pixels.

        :param scale: a dictionary of optional values which specify the scale
            of the region and / or output.  This applies to region if
            pixels or mm are used for inits.  It applies to output if
            neither output maxWidth nor maxHeight is specified.

            :magnification: the magnification ratio.  Only used if maxWidth and
                maxHeight are not specified or None.
            :mm_x: the horizontal size of a pixel in millimeters.
            :mm_y: the vertical size of a pixel in millimeters.
            :exact: if True, only a level that matches exactly will be returned.
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

            :width: the desired tile width.
            :height: the desired tile height.

        :param tile_overlap: if present, retile the output adding a symmetric
            overlap to the tiles.  If either x or y is not specified, it
            defaults to zero.  The overlap does not change the tile size,
            only the stride of the tiles.  This is a dictionary containing:

            :x: the horizontal overlap in pixels.
            :y: the vertical overlap in pixels.
            :edges: if True, then the edge tiles will exclude the overlap
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
            encoding (typically 'PNG', 'JPEG', or 'TIFF') or 'TILED' (identical
            to TIFF).  Must also be in the TileOutputMimeTypes map.
        :param jpegQuality: the quality to use when encoding a JPEG.
        :param jpegSubsampling: the subsampling level to use when encoding a
            JPEG.
        :param tiffCompression: the compression format when encoding a TIFF.
            This is usually 'raw', 'tiff_lzw', 'jpeg', or 'tiff_adobe_deflate'.
            Some of these are aliased: 'none', 'lzw', 'deflate'.
        :param frame: the frame number within the tile source.  None is the
            same as 0 for multi-frame sources.
        :param kwargs: optional arguments.
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
        :param kwargs: optional arguments.  Some options are width, height,
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
                getattr(PIL.Image, 'Resampling', PIL.Image).BICUBIC
                if width > imageWidth else
                getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)
        return _encodeImage(image, **kwargs)

    def getPixel(self, includeTileRecord=False, **kwargs):
        """
        Get a single pixel from the current tile source.

        :param includeTileRecord: if True, include the tile used for computing
            the pixel in the response.
        :param kwargs: optional arguments.  Some options are region, output,
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
                if len(img.mode) > 1:
                    pixel.update(dict(zip(img.mode.lower(), img.load()[0, 0])))
                else:
                    pixel.update(dict(zip([img.mode.lower()], [img.load()[0, 0]])))
        return pixel

    @property
    def frames(self):
        """A property with the number of frames."""
        if not hasattr(self, '_frameCount'):
            self._frameCount = len(self.getMetadata().get('frames', [])) or 1
        return self._frameCount


class FileTileSource(TileSource):

    def __init__(self, path, *args, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(*args, **kwargs)
        # Expand the user without converting datatype of path.
        try:
            path = (path.expanduser() if callable(getattr(path, 'expanduser', None)) else
                    os.path.expanduser(path))
        except TypeError:
            # Don't fail if the path is unusual -- maybe a source can handle it
            pass
        self.largeImagePath = path

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            args[0], kwargs.get('encoding', 'JPEG'), kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0), kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False),
            '__STYLESTART__', kwargs.get('style', None), '__STYLEEND__')

    def getState(self):
        if hasattr(self, '_classkey'):
            return self._classkey
        return '%s,%s,%s,%s,%s,%s,__STYLESTART__,%s,__STYLE_END__' % (
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
        except exceptions.TileSourceError:
            return False
