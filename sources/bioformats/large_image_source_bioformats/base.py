# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import atexit
import bioformats
import javabridge

from bioformats import log4j
from pathlib import PurePath
import numpy as np
import PIL.Image

from girder import logger
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource


try:
    javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
    log4j.basic_config()
    atexit.register(lambda: javabridge.kill_vm())
    logger.info('started JVM for BioFormat tile source')
except RuntimeError as e:
    logger.exception('cannot start JVM BioFormat source not working', e)


class BioFormatsFileTileSource(FileTileSource):
    """
    Provides tile access to via BioFormat.
    """

    _attached = False
    _img = None
    _metadata = {}

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: the associated file path.
        :param maxSize: either a number or an object with {'width': (width),
            'height': height} in pixels.  If None, the default max size is
            used.
        """
        super(BioFormatsFileTileSource, self).__init__(path, **kwargs)

        largeImagePath = self._getLargeImagePath()
        print(largeImagePath)

        if not PurePath(largeImagePath).suffix:
            raise TileSourceException('File cannot be opened via BioFormats, cause it does not '
                                      'contain the file suffix. (%s)' % largeImagePath)

        try:
            javabridge.attach()
            self._img = bioformats.ImageReader(largeImagePath)

            self._metadata = javabridge.jdictionary_to_string_dictionary(self._img.rdr.getMetadata())

            self.sizeX = self._img.rdr.getSizeX()
            self.sizeY = self._img.rdr.getSizeY()

            self.computeTiles()
            self.computeLevels()
        except javabridge.JavaException as e:
            es = javabridge.to_string(e.throwable)
            raise TileSourceException('File cannot be opened via BioFormats. (%s)' % es)
        finally:
            if javabridge.get_env():
                javabridge.detach()

        if self.levels < 1:
            raise TileSourceException(
                'OpenSlide image must have at least one level.')

        if self.sizeX <= 0 or self.sizeY <= 0:
            raise TileSourceException('BioFormats tile size is invalid.')

    def computeTiles(self):
        self.tileWidth = self.sizeX
        self.tileHeight = self.sizeY

    def computeLevels(self):
        self.levels = 1

    def getTile(self, x, y, z, pilImageAllowed=False, mayRedirect=False, **kwargs):
        if z < 0:
            raise TileSourceException('z layer does not exist')
        scale = 2 ** (self.levels - 1)
        offsetx = x * self.tileWidth * scale
        if not (0 <= offsetx < self.sizeX):
            raise TileSourceException('x is outside layer')
        offsety = y * self.tileHeight * scale
        if not (0 <= offsety < self.sizeY):
            raise TileSourceException('y is outside layer')

        width = self.tileWidth * scale
        height = self.tileHeight * scale

        try:
            javabridge.attach()
            arr = self._img.read(XYWH=(offsetx, offsety, width, height))

            # convert to rgb 256
            if arr.dtype == np.float32:
                arr = (arr * 255 / np.max(arr)).astype(np.uint8)

            tile = PIL.Image.fromarray(arr)
        except javabridge.JavaException as exc:
            raise TileSourceException('Failed to get BioFormat region (%r).' % exc)
        finally:
            if javabridge.get_env():
                javabridge.detach()
        if scale != 1:
            tile = tile.resize((self.tileWidth, self.tileHeight), PIL.Image.LANCZOS)
        return self._outputTile(tile, 'PIL', x, y, z, pilImageAllowed, **kwargs)

    def __del__(self):
        if self._img is not None:
            try:
                javabridge.attach()
                self._img.close()
            finally:
                if javabridge.get_env():
                    javabridge.detach()
