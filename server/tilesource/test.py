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

try:
    import PIL
    from PIL import Image, ImageDraw, ImageFont
    if int(PIL.PILLOW_VERSION.split('.')[0]) < 3:
        raise ImportError('Pillow v3.0 or later is required')
except ImportError:
    # TODO: change print to use logger
    print 'Error: Could not import PIL'
    # re-raise it for now, but maybe do something else in the future
    raise
from six import StringIO

from .base import TileSource, TileSourceException


class TestTileSource(TileSource):
    # TODO: move this class to its own file, and only import if PIL v3+ is
    # available
    def __init__(self, tileSize=256, levels=10, params=None):
        """
        Initialize the tile class.  The optional params options can include:
          min: minimum tile level (default 0)
          max: maximum tile level (default levels - 1)
          fractal: if 'true', draw a simple fractal on the tiles.
          w: tile width in pixels (default tileSize)
          h: tile height in pixels (default tileSize)
          sizex: image width in pixels at maximum level.
          sizey: image height in pixels at maximum level.

        :param tileSize: square tile size if not overridden by params.
        :param levels: number of zoom levels if not overridden by params.  The
                       allowed zoom levels are [0, levels).
        :param params: a dictionary of optional parameters.  See above.
        """
        super(TestTileSource, self).__init__()
        self.tileWidth = self.tileHeight = tileSize
        self.maxlevel = levels - 1
        self.minlevel = 0
        self.fractal = False
        if params:
            self.minlevel = int(params.get('min', 0))
            self.maxlevel = int(params.get('max', self.maxlevel))
            self.fractal = (params.get('fractal') == 'true')
            self.tileWidth = int(params.get('w', self.tileWidth))
            self.tileHeight = int(params.get('h', self.tileHeight))
        self.sizeX = (2 ** self.maxlevel) * self.tileWidth
        self.sizeY = (2 ** self.maxlevel) * self.tileHeight
        if params:
            self.sizeX = int(params.get('sizex', self.sizeX))
            self.sizeY = int(params.get('sizey', self.sizeY))
        self.levels = self.maxlevel + 1
        self.tileSize = max(self.tileWidth, self.tileHeight)

    def fractalTile(self, image, x, y, widthCount, color=(0, 0, 0)):
        # Don't generate a fractal tile if the tile isn't square or not a power
        # of 2 in size.
        if (self.tileWidth != self.tileHeight or
                (self.tileWidth & (self.tileWidth - 1))):
            return
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
        if not (self.minlevel <= z <= self.maxlevel):
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
        image.save(output, 'PNG')
        return output.getvalue()
