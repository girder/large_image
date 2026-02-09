import math
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

from ..constants import TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL, TileOutputMimeTypes
from . import utilities
from .tiledict import LazyTileDict

if TYPE_CHECKING:
    from .. import tilesource


class TileIterator:
    """
    A tile iterator on a TileSource.  Details about the iterator can be read
    via the `info` attribute on the iterator.
    """

    def __init__(
            self, source: 'tilesource.TileSource',
            format: str | tuple[str] = (TILE_FORMAT_NUMPY, ),
            resample: bool | None = True, **kwargs) -> None:
        self.source = source
        self._kwargs = kwargs
        if not isinstance(format, tuple):
            format = (format, )
        if TILE_FORMAT_IMAGE in format:
            encoding = kwargs.get('encoding')
            if encoding not in TileOutputMimeTypes:
                raise ValueError('Invalid encoding "%s"' % encoding)
        self.format = format
        self.resample = resample
        iterFormat = format if resample in (False, None) else (TILE_FORMAT_PIL, )
        self.info = self._tileIteratorInfo(format=iterFormat, resample=resample, **kwargs)
        if self.info is None:
            self._iter = None
            return
        if resample in (False, None) or round(self.info['requestedScale'], 2) == 1.0:
            self.resample = False
        self._iter = self._tileIterator(self.info)

    def __iter__(self) -> Iterator[LazyTileDict]:
        return self

    def __next__(self) -> LazyTileDict:
        if self._iter is None:
            raise StopIteration
        tile = next(self._iter)
        tile.setFormat(self.format, bool(self.resample), self._kwargs)
        return tile

    def __repr__(self) -> str:
        repr = f'TileIterator<{self.source}'
        if self.info:
            repr += (
                f': {self.info["output"]["width"]} x {self.info["output"]["height"]}'
                f'; tiles: {self.info["tile_count"]}'
                f'; region: {self.info["region"]}')
            if self.info['frame'] is not None:
                repr += f'; frame: {self.info["frame"]}>'
        repr += '>'
        return repr

    def _repr_json_(self) -> dict:
        if self.info:
            return self.info
        return {}

    def __len__(self) -> int | None:
        if self.info is None:
            return None
        iterlen = ((cast(int, self.info['xmax']) - cast(int, self.info['xmin'])) *
                   (cast(int, self.info['ymax']) - cast(int, self.info['ymin'])))
        if self.info.get('tile_position') is not None:
            return 1 if cast(int, self.info['tile_position']) < iterlen else 0
        return iterlen

    def _tileIteratorInfo(self, **kwargs) -> dict[str, Any] | None:  # noqa
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

        :param tile_offset: if present, adjust tile positions so that the
            corner of one tile is at the specified location.

            :left: the left offset in pixels.
            :top: the top offset in pixels.
            :auto: a boolean, if True, automatically set the offset to align
                with the region's left and top.

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
        source = self.source
        maxWidth = kwargs.get('output', {}).get('maxWidth')
        maxHeight = kwargs.get('output', {}).get('maxHeight')
        if ((maxWidth is not None and
                (not isinstance(maxWidth, int) or maxWidth < 0)) or
                (maxHeight is not None and
                 (not isinstance(maxHeight, int) or maxHeight < 0))):
            msg = 'Invalid output width or height.  Minimum value is 0.'
            raise ValueError(msg)

        magLevel = None
        mag = None
        if maxWidth is None and maxHeight is None:
            # If neither width nor height as specified, see if magnification,
            # mm_x, or mm_y are requested.
            magArgs = (kwargs.get('scale') or {}).copy()
            magArgs['rounding'] = None
            magLevel = source.getLevelForMagnification(**magArgs)
            if magLevel is None and kwargs.get('scale', {}).get('exact'):
                return None
            mag = source.getMagnificationForLevel(magLevel)
        metadata = source.metadata
        left, top, right, bottom = source._getRegionBounds(
            metadata, desiredMagnification=mag, **kwargs.get('region', {}))
        regionWidth = right - left
        regionHeight = bottom - top
        magRequestedScale: float | None = None
        if maxWidth is None and maxHeight is None and mag:
            if mag.get('scale') in (1.0, None):
                maxWidth, maxHeight = regionWidth, regionHeight
                magRequestedScale = 1
            else:
                maxWidth = regionWidth / cast(float, mag['scale'])
                maxHeight = regionHeight / cast(float, mag['scale'])
                magRequestedScale = cast(float, mag['scale'])
        outWidth, outHeight, calcScale = utilities._calculateWidthHeight(
            maxWidth, maxHeight, regionWidth, regionHeight)
        requestedScale = calcScale if magRequestedScale is None else magRequestedScale
        if (regionWidth < 0 or regionHeight < 0 or outWidth == 0 or
                outHeight == 0):
            return None

        preferredLevel = metadata['levels'] - 1
        # If we are scaling the result, pick the tile level that is at least
        # the resolution we need and is preferred by the tile source.
        if outWidth != regionWidth or outHeight != regionHeight:
            newLevel = source.getPreferredLevel(max(0, preferredLevel + int(
                math.ceil(round(math.log(min(float(outWidth) / regionWidth,
                                             float(outHeight) / regionHeight)) /
                                math.log(2), 4)))))
            if newLevel < preferredLevel:
                # scale the bounds to the level we will use
                factor = 2 ** (preferredLevel - newLevel)
                left = int(left / factor)
                right = max(int(right / factor), left + 1)
                regionWidth = right - left
                top = int(top / factor)
                bottom = max(int(bottom / factor), top + 1)
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
            'range_y': 0,
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
            msg = 'Invalid tile_size or tile_overlap.'
            raise ValueError(msg)

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

        offset_x = kwargs.get('tile_offset', {}).get('left', 0)
        offset_y = kwargs.get('tile_offset', {}).get('top', 0)
        if (kwargs.get('tile_offset', {}).get('auto') and
                regionWidth >= tile_size['width'] and
                regionHeight >= tile_size['height']):
            offset_x = left
            offset_y = top
        offset_x = (left - left % tile_size['width']) if offset_x > left else offset_x
        offset_y = (top - top % tile_size['height']) if offset_y > top else offset_y
        # If the overlapped tiles don't run over the edge, then the functional
        # size of the region is reduced by the overlap.  This factor is stored
        # in the overlap offset_*.
        xmin = int((left - offset_x) / tile_size['width'])
        xmax = max(int(math.ceil((float(right - offset_x) - tile_overlap['range_x']) /
                                 tile_size['width'])), xmin + 1)
        ymin = int((top - offset_y) / tile_size['height'])
        ymax = max(int(math.ceil((float(bottom - offset_y) - tile_overlap['range_y']) /
                                 tile_size['height'])), ymin + 1)
        tile_overlap.update({'xmin': xmin, 'xmax': xmax,
                             'ymin': ymin, 'ymax': ymax})
        tile_overlap['offset_x'] += offset_x
        tile_overlap['offset_y'] += offset_y

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
            'tile_count': (xmax - xmin) * (ymax - ymin),
            'tile_overlap': tile_overlap,
            'tile_position': kwargs.get('tile_position'),
            'tile_size': tile_size,
        }
        return info

    def _tileIterator(self, iterInfo: dict[str, Any]) -> Iterator[LazyTileDict]:
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
        source = self.source
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

        source.logger.debug(
            'Fetching region of an image with a source size of %d x %d; '
            'getting %d tile%s',
            regionWidth, regionHeight, (xmax - xmin) * (ymax - ymin),
            '' if (xmax - xmin) * (ymax - ymin) == 1 else 's')

        # If tile is specified, return at most one tile
        if iterInfo.get('tile_position') is not None:
            tilePos: int = cast(int, iterInfo.get('tile_position'))
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
        mag = source.getMagnificationForLevel(level)
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
                    'source': source,
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
                                     (iterInfo['ymax'] - iterInfo['ymin'])),
                    },
                    'tile_overlap': overlap,
                })
                tile['gx'] = tile['x'] * scale
                tile['gy'] = tile['y'] * scale
                tile['gwidth'] = tile['width'] * scale
                tile['gheight'] = tile['height'] * scale
                yield tile
