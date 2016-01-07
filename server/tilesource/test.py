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

import colorsys

from girder import logger

try:
    import PIL
    from PIL import Image, ImageDraw, ImageFont
    if int(PIL.PILLOW_VERSION.split('.')[0]) < 3:
        raise ImportError('Pillow v3.0 or later is required')
except ImportError:
    logger.info('Error: Could not import PIL')
    # re-raise it for now, but maybe do something else in the future
    raise
from six import StringIO

from .base import TileSource, TileSourceException


class TestTileSource(TileSource):
    def __init__(self, tileSize=256, minLevel=None, maxLevel=None,
                 tileWidth=None, tileHeight=None, sizeX=None, sizeY=None,
                 fractal=False, encoding='PNG'):
        """
        Initialize the tile class.  The optional params options can include:

        :param tileSize: square tile size if not overridden by w and h.
        :param minLevel: minimum tile level (default 0)
        :param maxLevel: maximum tile level (default 9)
        :param tileWidth: tile width in pixels (tileSize if None)
        :param tileHeight: tile height in pixels (tileSize if None)
        :param sizeX: image width in pixels at maximum level.  Computed from
            maxLevel and tileWidth if None.
        :param sizeY: image height in pixels at maximum level.  Computer from
            maxLevel and tileHeight if None.
        :param fractal: if True, and the tile size is square and a power of
            two, draw a simple fractal on the tiles.
        :param encoding: 'PNG' or 'JPEG'.
        """
        super(TestTileSource, self).__init__()

        tileSize = 256 if not tileSize else tileSize
        self.maxLevel = 9 if maxLevel is None else int(maxLevel)
        self.minLevel = 0 if minLevel is None else int(minLevel)
        self.tileWidth = int(tileSize if tileWidth is None else tileWidth)
        self.tileHeight = int(tileSize if tileHeight is None else tileHeight)
        # Don't generate a fractal tile if the tile isn't square or not a power
        # of 2 in size.
        self.fractal = (fractal and self.tileWidth == self.tileHeight and
                        not (self.tileWidth & (self.tileWidth - 1)))
        self.sizeX = (((2 ** self.maxLevel) * self.tileWidth)
                      if sizeX is None else int(sizeX))
        self.sizeY = (((2 ** self.maxLevel) * self.tileHeight)
                      if sizeY is None else int(sizeY))
        self.encoding = encoding if encoding in ('PNG', 'JPEG') else 'PNG'
        # Used for reporting tile information
        self.levels = self.maxLevel + 1

    def fractalTile(self, image, x, y, widthCount, color=(0, 0, 0)):
        imageDraw = ImageDraw.Draw(image)
        x *= self.tileWidth
        y *= self.tileHeight
        sq = widthCount * self.tileWidth
        while sq >= 4:
            sq1 = sq / 4
            sq2 = sq1 + sq / 2
            for t in range(-(y % sq), self.tileWidth, sq):
                if t + sq1 < self.tileWidth and t + sq2 >= 0:
                    for l in range(-(x % sq), self.tileWidth, sq):
                        if l + sq1 < self.tileWidth and l + sq2 >= 0:
                            imageDraw.rectangle([
                                max(-1, l + sq1), max(-1, t + sq1),
                                min(self.tileWidth, l + sq2 - 1),
                                min(self.tileWidth, t + sq2 - 1),
                            ], color, None)
            sq /= 2

    def getTile(self, x, y, z):
        widthCount = 2 ** z

        if not (0 <= x < widthCount):
            raise TileSourceException('x is outside layer')
        if not (0 <= y < widthCount):
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
        except IOError:
            imageDrawFont = ImageFont.load_default()
        imageDraw.multiline_text(
            xy=(10, 10),
            text='x=%d\ny=%d\nz=%d' % (x, y, z),
            fill=(0, 0, 0),
            font=imageDrawFont
        )

        output = StringIO()
        image.save(output, self.encoding, quality=95)
        return output.getvalue()

    def getTileMimeType(self):
        if self.encoding == 'JPEG':
            return 'image/jpeg'
        return 'image/png'
