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
import itertools
import math

from PIL import Image, ImageDraw, ImageFont
from pkg_resources import DistributionNotFound, get_distribution

from large_image.cache_util import LruCacheMetaclass, methodcache, strhash
from large_image.constants import TILE_FORMAT_PIL, SourcePriority
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
                 fractal=False, frames=None, monochrome=False, **kwargs):
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
        :param sizeY: image height in pixels at maximum level.  Computed from
            maxLevel and tileHeight if None.
        :param fractal: if True, and the tile size is square and a power of
            two, draw a simple fractal on the tiles.
        :param frames: if present, this is either a single number for generic
            frames, or comma-separated list of c,z,t,xy.
        :param monochrome: if True, return single channel tiles.
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
                      if not sizeX else sizeX)
        self.sizeY = (((2 ** self.maxLevel) * self.tileHeight)
                      if not sizeY else sizeY)
        self.maxLevel = int(math.ceil(math.log2(max(
            self.sizeX / self.tileWidth, self.sizeY / self.tileHeight))))
        self.frameSpec = frames or None
        self.monochrome = bool(monochrome)
        # Used for reporting tile information
        self.levels = self.maxLevel + 1
        if frames:
            frameList = []
            counts = [int(part) for part in str(frames).split(',')]
            self._framesParts = len(counts)
            for fidx in itertools.product(*(range(part) for part in counts[::-1])):
                curframe = {}
                if len(fidx) > 1:
                    for idx, (k, v) in enumerate(zip([
                            'IndexC', 'IndexZ', 'IndexT', 'IndexXY'], list(fidx)[::-1])):
                        if counts[idx] > 1:
                            curframe[k] = v
                else:
                    curframe['Index'] = fidx[0]
                frameList.append(curframe)
            if len(frameList) > 1:
                self._frames = frameList

    @classmethod
    def canRead(cls, *args, **kwargs):
        return True

    def fractalTile(self, image, x, y, widthCount, color=(0, 0, 0)):
        """
        Draw a simple fractal in a tile image.

        :param image: a Pil image to draw on.  Modified.
        :param x: the tile x position
        :param y: the tile y position
        :param widthCount: 2 ** z; the number of tiles across for a "full size"
            image at this z level.
        :param color: an rgb tuple on a scale of [0-255].
        """
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

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        if hasattr(self, '_frames') and len(self._frames) > 1:
            result['frames'] = self._frames
            self._addMetadataFrameInformation(result)
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        return {'fractal': self.fractal, 'monochrome': self.monochrome}

    @methodcache()
    def getTile(self, x, y, z, *args, **kwargs):
        frame = int(kwargs.get('frame') or 0)
        self._xyzInRange(x, y, z, frame, len(self._frames) if hasattr(self, '_frames') else None)

        if not (self.minLevel <= z <= self.maxLevel):
            raise TileSourceException('z layer does not exist')

        xFraction = (x + 0.5) * self.tileWidth * 2 ** (self.levels - 1 - z) / self.sizeX
        yFraction = (y + 0.5) * self.tileHeight * 2 ** (self.levels - 1 - z) / self.sizeY
        fFraction = yFraction
        if hasattr(self, '_frames'):
            fFraction = float(frame) / (len(self._frames) - 1)

        backgroundColor = colorsys.hsv_to_rgb(
            h=xFraction,
            s=(0.3 + (0.7 * fFraction)),
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
            self.fractalTile(image, x, y, 2 ** z, rgbColor)

        fontsize = 0.15
        text = 'x=%d\ny=%d\nz=%d' % (x, y, z)
        if hasattr(self, '_frames'):
            if self._framesParts == 1:
                text += '\nf=%d' % frame
            else:
                for k1, k2 in [('C', 'IndexC'), ('Z', 'IndexZ'),
                               ('T', 'IndexT'), ('XY', 'IndexXY')]:
                    if k2 in self._frames[frame]:
                        text += '\n%s=%d' % (k1, self._frames[frame][k2])
                fontsize = min(fontsize, 0.8 / len(text.split('\n')))
        try:
            # the font size should fill the whole tile
            imageDrawFont = ImageFont.truetype(
                font='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                size=int(fontsize * min(self.tileWidth, self.tileHeight))
            )
        except OSError:
            imageDrawFont = ImageFont.load_default()
        imageDraw.multiline_text(
            xy=(10, 10),
            text=text,
            fill=(0, 0, 0),
            font=imageDrawFont
        )
        _counters['tiles'] += 1
        if self.monochrome:
            image = image.convert('L')
        return self._outputTile(image, TILE_FORMAT_PIL, x, y, z, **kwargs)

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(TestTileSource, TestTileSource).getLRUHash(
                *args, **kwargs),
            kwargs.get('minLevel'), kwargs.get('maxLevel'),
            kwargs.get('tileWidth'), kwargs.get('tileHeight'),
            kwargs.get('fractal'), kwargs.get('sizeX'), kwargs.get('sizeY'),
            kwargs.get('frames'), kwargs.get('monochrome'),
        )

    def getState(self):
        return 'test %r %r %r %r %r %r %r %r %r %r' % (
            super().getState(), self.minLevel, self.maxLevel, self.tileWidth,
            self.tileHeight, self.fractal, self.sizeX, self.sizeY,
            self.frameSpec, self.monochrome)


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
