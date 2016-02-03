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

from .base import GirderTileSource, TileSourceException
from .cache import LruCacheMetaclass
from .tiff_reader import TiledTiffDirectory, TiffException, \
    InvalidOperationTiffException, IOTiffException


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
        return item.get('largeImage')

    def __init__(self, item):
        super(TiffGirderTileSource, self).__init__(item)

        largeImagePath = self._getLargeImagePath()

        self._tiffDirectories = list()
        for directoryNum in itertools.count():
            try:
                tiffDirectory = TiledTiffDirectory(largeImagePath, directoryNum)
            except TiffException:
                break
            else:
                self._tiffDirectories.append(tiffDirectory)

        if not self._tiffDirectories:
            raise TileSourceException('File must have at least 1 level')

        # Multiresolution TIFFs are stored with full-resolution layer in
        #   directory 0
        self._tiffDirectories.reverse()

        self.tileWidth = self._tiffDirectories[-1].tileWidth
        self.tileHeight = self._tiffDirectories[-1].tileHeight
        self.levels = len(self._tiffDirectories)
        self.sizeX = self._tiffDirectories[-1].imageWidth
        self.sizeY = self._tiffDirectories[-1].imageHeight

    def getTile(self, x, y, z):
        try:
            return self._tiffDirectories[z].getTile(x, y)
        except IndexError:
            raise TileSourceException('z layer does not exist')
        except InvalidOperationTiffException as e:
            raise TileSourceException(e.message)
        except IOTiffException as e:
            raise TileSourceException('Internal I/O failure: %s' % e.message)
