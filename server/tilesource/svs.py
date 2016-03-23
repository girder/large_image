#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################

import math
import six
import PIL

from girder import logger
from six import BytesIO
from six.moves import range

try:
    import openslide
except ImportError:
    logger.warning('Could not import openslide')
    raise

from .base import GirderTileSource, TileSourceException
from .cache import LruCacheMetaclass


@six.add_metaclass(LruCacheMetaclass)
class SVSGirderTileSource(GirderTileSource):
    """
    Provides tile access to Girder items with SVS file.
    """
    cacheMaxSize = 2
    cacheTimeout = 60

    @staticmethod
    def cacheKeyFunc(args, kwargs):
        item = args[0]
        return (item.get('largeImage', {}).get('fileId'),
                kwargs.get('jpegQuality'),
                kwargs.get('jpegSubsampling'),
                kwargs.get('encoding'))

    def __init__(self, item, jpegQuality=95, jpegSubsampling=0,
                 encoding='JPEG', **kwargs):
        """
        Initialize the tile class.

        :param item: the associated Girder item.
        :param jpegQuality: when serving jpegs, use this quality.
        :param jpegSubsampling: when serving jpegs, use this subsampling (0 is
                                full chroma, 1 is half, 2 is quarter).
        :param encoding: 'JPEG' or 'PNG'.
        """
        super(SVSGirderTileSource, self).__init__(item, **kwargs)

        if encoding not in ('PNG', 'JPEG'):
            raise ValueError('Invalid encoding "%s"' % encoding)

        self.encoding = encoding
        self.jpegQuality = int(jpegQuality)
        self.jpegSubsampling = int(jpegSubsampling)

        largeImagePath = self._getLargeImagePath()

        try:
            self._openslide = openslide.OpenSlide(largeImagePath)
        except openslide.lowlevel.OpenSlideUnsupportedFormatError:
            raise TileSourceException('File cannot be opened via OpenSlide.')
        # The tile size isn't in the official openslide interface
        # documentation, but every example has the tile size in the properties.
        # Try to read it, but fall back to 256 if it isn't et.
        self.tileWidth = self.tileHeight = 256
        try:
            self.tileWidth = int(self._openslide.properties[
                'openslide.level[0].tile-width'])
        except ValueError:
            pass
        try:
            self.tileHeight = int(self._openslide.properties[
                'openslide.level[0].tile-height'])
        except ValueError:
            pass
        if self.tileWidth <= 0 or self.tileHeight <= 0:
            raise TileSourceException('OpenSlide tile size is invalid.')
        self.sizeX = self._openslide.dimensions[0]
        self.sizeY = self._openslide.dimensions[1]
        if self.sizeX <= 0 or self.sizeY <= 0:
            raise TileSourceException('OpenSlide image size is invalid.')
        self.levels = int(math.ceil(max(
            math.log(float(self.sizeX) / self.tileWidth),
            math.log(float(self.sizeY) / self.tileHeight)) / math.log(2))) + 1
        if self.levels < 1:
            raise TileSourceException(
                'OpenSlide image must have at least one level.')
        self._svslevels = []
        svsLevelDimensions = self._openslide.level_dimensions
        # Precompute which SVS level should be used for our tile levels.  SVS
        # level 0 is the maximum resolution.  We assume that the SVS levels are
        # in descending resolution and are powers of two in scale.  For each of
        # our levels (where 0 is the minimum resolution), find the lowest
        # resolution SVS level that contains at least as many pixels.  If this
        # is not the same scale as we expect, note the scale factor so we can
        # load an appropriate area and scale it to the tile size later.
        for level in range(self.levels):
            levelW = max(1, self.sizeX / 2 ** (self.levels - 1 - level))
            levelH = max(1, self.sizeY / 2 ** (self.levels - 1 - level))
            # bestlevel and scale will be the picked svs level and the scale
            # between that level and what we really wanted.  We expect scale to
            # always be a positive integer power of two.
            bestlevel = 0
            scale = 1
            for svslevel in range(len(svsLevelDimensions)):
                if (svsLevelDimensions[svslevel][0] < levelW - 1 or
                        svsLevelDimensions[svslevel][1] < levelH - 1):
                    break
                bestlevel = svslevel
                scale = int(round(svsLevelDimensions[svslevel][0] / levelW))
            self._svslevels.append({
                'svslevel': bestlevel,
                'scale': scale
            })

    def getTile(self, x, y, z, pilImageAllowed=False):
        try:
            svslevel = self._svslevels[z]
        except IndexError:
            raise TileSourceException('z layer does not exist')
        # When we read a region from the SVS, we have to ask for it in the
        # SVS level 0 coordinate system.  Our x and y is in tile space at the
        # specifed z level, so the offset in SVS level 0 coordinates has to be
        # scaled by the tile size and by the z level.
        scale = 2 ** (self.levels - 1 - z)
        offsetx = x * self.tileWidth * scale
        if not (0 <= offsetx < self.sizeX):
            raise TileSourceException('x is outside layer')
        offsety = y * self.tileHeight * scale
        if not (0 <= offsety < self.sizeY):
            raise TileSourceException('y is outside layer')
        # We ask to read an area that will cover the tile at the z level.  The
        # scale we computed in the __init__ process for this svs level tells
        # how much larger a region we need to read.
        tile = self._openslide.read_region(
            (offsetx, offsety), svslevel['svslevel'],
            (self.tileWidth * svslevel['scale'],
             self.tileHeight * svslevel['scale']))
        # Always scale to the svs level 0 tile size.
        if svslevel['scale'] != 1:
            tile = tile.resize((self.tileWidth, self.tileHeight),
                               PIL.Image.LANCZOS)
        if pilImageAllowed:
            return tile
        output = BytesIO()
        tile.save(output, self.encoding, quality=self.jpegQuality,
                  subsampling=self.jpegSubsampling)
        return output.getvalue()

    def getTileMimeType(self):
        if self.encoding == 'JPEG':
            return 'image/jpeg'
        return 'image/png'

    def getPreferredLevel(self, level):
        """
        Given a desired level (0 is minimum resolution, self.levels - 1 is max
        resolution), return the level that contains actual data that is no
        lower resolution.

        :param level: desired level
        :returns level: a level with actual data that is no lower resolution.
        """
        level = max(0, min(level, self.levels - 1))
        scale = self._svslevels[level]['scale']
        while scale > 1:
            level += 1
            scale /= 2
        return level
