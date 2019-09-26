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

import six
from pkg_resources import DistributionNotFound, get_distribution

from large_image.cache_util import LruCacheMetaclass, methodcache, strhash
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@six.add_metaclass(LruCacheMetaclass)
class ImageJFileTileSource(FileTileSource):
    """
    Provides tile access to single image PIL files.
    """

    cacheName = 'tilesource'
    name = 'imagejfile'
    # No extensions or mime types are explicitly added for the PIL tile source,
    # as it should always be a fallback source

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: the associated file path.
        :param maxSize: either a number or an object with {'width': (width),
            'height': height} in pixels.  If None, the default max size is
            used.
        """
        super(ImageJFileTileSource, self).__init__(path, **kwargs)

        largeImagePath = self._getLargeImagePath()

        # try:
        #     self._pilImage = PIL.Image.open(largeImagePath)
        # except IOError:
        #     raise TileSourceException('File cannot be opened via PIL.')

        # self.sizeX = self._pilImage.width
        # self.sizeY = self._pilImage.height
        # # We have just one tile which is the entire image.
        # self.tileWidth = self.sizeX
        # self.tileHeight = self.sizeY
        # self.levels = 1
        # # Throw an exception if too big
        # if self.tileWidth <= 0 or self.tileHeight <= 0:
        #     raise TileSourceException('ImageJ tile size is invalid.')

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(ImageJFileTileSource, ImageJFileTileSource).getLRUHash(
                *args, **kwargs))

    @methodcache()
    def getTile(self, x, y, z, imagejImageAllowed=False, mayRedirect=False, **kwargs):
        if z != 0:
            raise TileSourceException('z layer does not exist')
        if x != 0:
            raise TileSourceException('x is outside layer')
        if y != 0:
            raise TileSourceException('y is outside layer')
        # TODO
        return self._outputTile(self._pilImage, 'ImageJ', x, y, z,
                                imagejImageAllowed, **kwargs)
