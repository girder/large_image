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

from .base import GirderTileSource, TileSourceException
from .cache import LruCacheMetaclass
from .tiff_reader import TiledTiffDirectory, TiffException, \
    InvalidOperationTiffException, IOTiffException

try:
    import PIL
except ImportError:
    PIL = None


@six.add_metaclass(LruCacheMetaclass)
class TiffGirderTileSource(GirderTileSource):
    """
    Provides tile access to Girder items with TIFF file.
    """
    cacheMaxSize = 2
    cacheTimeout = 60

    @staticmethod
    def cacheKeyFunc(args, kwargs):
        item = args[0]
        return item.get('largeImage', {}).get('fileId')

    def __init__(self, item, **kwargs):
        super(TiffGirderTileSource, self).__init__(item, **kwargs)

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
            import logging
            logger = logging.getLogger('girder')
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
