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

from six.moves import range

import openslide
import PIL

from .base import FileTileSource, TileSourceException
from ..cache_util import LruCacheMetaclass, methodcache

try:
    import girder
    from girder import logger
    from .base import GirderTileSource
except ImportError:
    girder = None
    import logging as logger


@six.add_metaclass(LruCacheMetaclass)
class SVSFileTileSource(FileTileSource):
    """
    Provides tile access to SVS files.
    """
    cacheName = 'tilesource'
    name = 'svsfile'

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.

        :param path: the associated file path.
        """
        super(SVSFileTileSource, self).__init__(path, **kwargs)

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
        maxSize = 16384   # This should probably be based on available memory
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
            if (self.tileWidth * scale > maxSize or
                    self.tileHeight * scale > maxSize):
                msg = ('OpenSlide has no small-scale tiles (level %d is at %d '
                       'scale)' % (level, scale))
                logger.info(msg)
                raise TileSourceException(msg)
            self._svslevels.append({
                'svslevel': bestlevel,
                'scale': scale
            })

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        try:
            mag = self._openslide.properties[
                openslide.PROPERTY_NAME_OBJECTIVE_POWER]
            mag = float(mag) if mag else None
        except (KeyError, ValueError):
            mag = None
        try:
            mm_x = float(self._openslide.properties[
                openslide.PROPERTY_NAME_MPP_X]) * 0.001
            mm_y = float(self._openslide.properties[
                openslide.PROPERTY_NAME_MPP_Y]) * 0.001
        except Exception:
            mm_x = mm_y = None
        return {
            'magnification': mag,
            'mm_x': mm_x,
            'mm_y': mm_y,
        }

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, **kwargs):
        if z < 0:
            raise TileSourceException('z layer does not exist')
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
        try:
            tile = self._openslide.read_region(
                (offsetx, offsety), svslevel['svslevel'],
                (self.tileWidth * svslevel['scale'],
                 self.tileHeight * svslevel['scale']))
        except openslide.lowlevel.OpenSlideError as exc:
            raise TileSourceException(
                'Failed to get OpenSlide region (%r).' % exc)
        # Always scale to the svs level 0 tile size.
        if svslevel['scale'] != 1:
            tile = tile.resize((self.tileWidth, self.tileHeight),
                               PIL.Image.LANCZOS)
        return self._outputTile(tile, 'PIL', x, y, z, pilImageAllowed, **kwargs)

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


if girder:
    class SVSGirderTileSource(SVSFileTileSource, GirderTileSource):
        """
        Provides tile access to Girder items with an SVS file.
        """
        cacheName = 'tilesource'
        name = 'svs'
