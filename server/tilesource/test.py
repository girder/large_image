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
    # TODO: move this class to its own file, and only import if PIL v3+ is available
    def __init__(self, tileSize=256, levels=10):
        super(TestTileSource, self).__init__()
        self.tileSize = tileSize
        self.levels = levels
        self.sizeX = (2 ** (self.levels - 1)) * self.tileSize
        self.sizeY = (2 ** (self.levels - 1)) * self.tileSize


    def getTile(self, x, y, z):
        widthCount = 2 ** z

        if not (0 <= x < widthCount):
            raise TileSourceException('x is outside layer')
        if not (0 <= y < widthCount):
            raise TileSourceException('y is outside layer')
        if not (0 <= z < self.levels):
            raise TileSourceException('z layer does not exist')

        xFraction = float(x) / (widthCount - 1) if z != 0 else 0
        yFraction = float(y) / (widthCount - 1) if z != 0 else 0

        backgroundColor = colorsys.hsv_to_rgb(
            h=xFraction,
            s=(0.3 + (0.7 * yFraction)),
            v=(0.3 + (0.7 * yFraction)),
        )

        image = Image.new(
            mode='RGB',
            size=(self.tileSize, self.tileSize),
            color=tuple(int(val * 255) for val in backgroundColor)
        )
        imageDraw = ImageDraw.Draw(image)
        try:
            imageDrawFont = ImageFont.truetype(
                font='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
                size=int(0.24 * self.tileSize)  # this size fills the whole tile
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
        image.save(output, 'JPEG')
        return output.getvalue()
