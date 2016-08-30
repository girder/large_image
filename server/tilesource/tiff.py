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

import itertools

import six
from six import BytesIO

from .base import FileTileSource, TileSourceException
from ..cache_util import pickAvailableCache, LruCacheMetaclass
from .tiff_reader import TiledTiffDirectory, TiffException, \
    InvalidOperationTiffException, IOTiffException

try:
    import girder
    from girder import logger
    from .base import GirderTileSource
except ImportError:
    girder = None
    import logging as logger

try:
    import PIL
except ImportError:
    PIL = None


@six.add_metaclass(LruCacheMetaclass)
class TiffFileTileSource(FileTileSource):
    """
    Provides tile access to TIFF files.
    """
    # Cache size is based on what the class needs, which does not include
    # individual tiles
    cacheMaxSize = pickAvailableCache(1024 ** 2)
    cacheTimeout = 300
    name = 'tifffile'

    @staticmethod
    def cacheKeyFunc(args, kwargs):
        path = args[0]
        return path

    def __init__(self, item, **kwargs):
        super(TiffFileTileSource, self).__init__(item, **kwargs)

        largeImagePath = self._getLargeImagePath()
        lastException = None

        self._tiffDirectories = list()
        for directoryNum in itertools.count():
            try:
                tiffDirectory = TiledTiffDirectory(largeImagePath, directoryNum)
            except TiffException as lastException:
                break
            else:
                self._tiffDirectories.append(tiffDirectory)

        if not self._tiffDirectories:
            logger.info('File %s didn\'t meet requirements for tile source: '
                        '%s' % (largeImagePath, lastException))
            raise TileSourceException('File must have at least 1 level')

        # Multiresolution TIFFs are stored with full-resolution layer in
        #   directory 0
        self._tiffDirectories.reverse()

        self.tileWidth = self._tiffDirectories[-1].tileWidth
        self.tileHeight = self._tiffDirectories[-1].tileHeight
        self.levels = len(self._tiffDirectories)
        self.sizeX = self._tiffDirectories[-1].imageWidth
        self.sizeY = self._tiffDirectories[-1].imageHeight

    def getMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        pixelInfo = self._tiffDirectories[-1].pixelInfo
        mm_x = pixelInfo.get('mm_x')
        mm_y = pixelInfo.get('mm_y')
        # Estimate the magnification, as we don't have a direct value
        mag = pixelInfo.get('magnification', 0.01 / mm_x if mm_x else None)
        return {
            'magnification': mag,
            'mm_x': mm_x,
            'mm_y': mm_y,
        }

    def getTile(self, x, y, z, pilImageAllowed=False, sparseFallback=False,
                **kwargs):
        try:
            return self._tiffDirectories[z].getTile(x, y)
        except IndexError:
            raise TileSourceException('z layer does not exist')
        except InvalidOperationTiffException as e:
            raise TileSourceException(e.message)
        except IOTiffException as e:
            if sparseFallback and pilImageAllowed and z and PIL:
                image = self.getTile(x / 2, y / 2, z - 1, pilImageAllowed,
                                     sparseFallback)
                if not isinstance(image, PIL.Image.Image):
                    image = PIL.Image.open(BytesIO(image))
                image = image.crop((
                    self.tileWidth / 2 if x % 2 else 0,
                    self.tileHeight / 2 if y % 2 else 0,
                    self.tileWidth if x % 2 else self.tileWidth / 2,
                    self.tileHeight if y % 2 else self.tileHeight / 2))
                image = image.resize((self.tileWidth, self.tileHeight))
                return image
            raise TileSourceException('Internal I/O failure: %s' % e.message)


if girder:
    class TiffGirderTileSource(TiffFileTileSource, GirderTileSource):
        """
        Provides tile access to Girder items with a TIFF file.
        """
        # Cache size is based on what the class needs, which does not include
        # individual tiles
        cacheMaxSize = pickAvailableCache(1024 ** 2)
        cacheTimeout = 300
        name = 'tiff'

        @staticmethod
        def cacheKeyFunc(args, kwargs):
            item = args[0]
            return item.get('largeImage', {}).get('fileId')
