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

import colorsys
from PIL import Image, ImageDraw, ImageFont
from pkg_resources import DistributionNotFound, get_distribution

from large_image.constants import SourcePriority, TILE_FORMAT_PIL
from large_image.cache_util import strhash, methodcache, LruCacheMetaclass
from large_image.exceptions import TileSourceException
from large_image.tilesource import TileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


_counters = {
    'tiles': 0
}


class TestTileSource(TileSource, metaclass=LruCacheMetaclass):
    cacheName = 'tilesource'
    name = 'test'
    extensions = {
        None: SourcePriority.MANUAL
    }

    def __init__(self, ignored_path=None, minLevel=0, maxLevel=9,
                 tileWidth=256, tileHeight=256, sizeX=None, sizeY=None,
                 fractal=False, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param ignored_path: for compatibility with FileTileSource.
        :param minLevel: minimum tile level
        :param maxLevel: maximum tile level
        :param tileWidth: tile width in pixels
        :param tileHeight: tile height in pixels
        :param sizeX: image width in pixels at maximum level.  Computed from
            maxLevel and tileWidth if None.
        :param sizeY: image height in pixels at maximum level.  Computer from
            maxLevel and tileHeight if None.
        :param fractal: if True, and the tile size is square and a power of
            two, draw a simple fractal on the tiles.
        """
        if not kwargs.get('encoding'):
            kwargs = kwargs.copy()
            kwargs['encoding'] = 'PNG'
        super().__init__(**kwargs)

        self.minLevel = minLevel
        self.maxLevel = maxLevel
        self.tileWidth = tileWidth
        self.tileHeight = tileHeight
        # Don't generate a fractal tile if the tile isn't square or not a power
        # of 2 in size.
        self.fractal = (fractal and self.tileWidth == self.tileHeight and
                        not (self.tileWidth & (self.tileWidth - 1)))
        self.sizeX = (((2 ** self.maxLevel) * self.tileWidth)
                      if sizeX is None else sizeX)
        self.sizeY = (((2 ** self.maxLevel) * self.tileHeight)
                      if sizeY is None else sizeY)
        # Used for reporting tile information
        self.levels = self.maxLevel + 1

    @classmethod
    def canRead(cls, *args, **kwargs):
        return True

    def fractalTile(self, image, x, y, widthCount, color=(0, 0, 0)):
        imageDraw = ImageDraw.Draw(image)
        x *= self.tileWidth
        y *= self.tileHeight
        sq = widthCount * self.tileWidth
        while sq >= 4:
            sq1 = sq // 4
            sq2 = sq1 + sq // 2
            for t in range(-(y % sq), self.tileWidth, sq):
                if t + sq1 < self.tileWidth and t + sq2 >= 0:
                    for l in range(-(x % sq), self.tileWidth, sq):
                        if l + sq1 < self.tileWidth and l + sq2 >= 0:
                            imageDraw.rectangle([
                                max(-1, l + sq1), max(-1, t + sq1),
                                min(self.tileWidth, l + sq2 - 1),
                                min(self.tileWidth, t + sq2 - 1),
                            ], color, None)
            sq //= 2

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        return {'fractal': self.fractal}

    @methodcache()
    def getTile(self, x, y, z, *args, **kwargs):
        widthCount = 2 ** z

        if not (0 <= x < float(self.sizeX) / self.tileWidth * 2 ** (
                z - self.maxLevel)):
            raise TileSourceException('x is outside layer')
        if not (0 <= y < float(self.sizeY) / self.tileHeight * 2 ** (
                z - self.maxLevel)):
            raise TileSourceException('y is outside layer')
        if not (self.minLevel <= z <= self.maxLevel):
            raise TileSourceException('z layer does not exist')

        xFraction = float(x) / (widthCount - 1) if z != 0 else 0
        yFraction = float(y) / (widthCount - 1) if z != 0 else 0

        backgroundColor = colorsys.hsv_to_rgb(
            h=(0.9 * xFraction),
            s=(0.3 + (0.7 * yFraction)),
            v=(0.3 + (0.7 * yFraction)),
        )
        rgbColor = tuple(int(val * 255) for val in backgroundColor)

        image = Image.new(
            mode='RGB',
            size=(self.tileWidth, self.tileHeight),
            color=(rgbColor if not self.fractal else (255, 255, 255))
        )
        imageDraw = ImageDraw.Draw(image)

        if self.fractal:
            self.fractalTile(image, x, y, widthCount, rgbColor)

        try:
            # the font size should fill the whole tile
            imageDrawFont = ImageFont.truetype(
                font='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                size=int(0.15 * min(self.tileWidth, self.tileHeight))
            )
        except OSError:
            imageDrawFont = ImageFont.load_default()
        imageDraw.multiline_text(
            xy=(10, 10),
            text='x=%d\ny=%d\nz=%d' % (x, y, z),
            fill=(0, 0, 0),
            font=imageDrawFont
        )
        _counters['tiles'] += 1
        return self._outputTile(image, TILE_FORMAT_PIL, x, y, z, **kwargs)

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(TestTileSource, TestTileSource).getLRUHash(
                *args, **kwargs),
            kwargs.get('minLevel'), kwargs.get('maxLevel'),
            kwargs.get('tileWidth'), kwargs.get('tileHeight'),
            kwargs.get('fractal'))

    def getState(self):
        return 'test %r %r %r %r %r %r' % (
            super().getState(), self.minLevel,
            self.maxLevel, self.tileWidth, self.tileHeight, self.fractal)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return TestTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return TestTileSource.canRead(*args, **kwargs)
