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

import PIL.Image

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@six.add_metaclass(LruCacheMetaclass)
class BioFormatsFileTileSource(FileTileSource):
    """
    Provides tile access to single image PIL files.
    """

    cacheName = 'tilesource'
    name = 'bioformats'
    extensions = {
        'jp2': SourcePriority.HIGH
    }
    mimeTypes = {
        'image/jp2': SourcePriority.HIGH
    }

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

        # try:
        #     ij = self._ij = imagej.init('sc.fiji:fiji')
        #     img = self._img = self._ij.io.open(largeImagePath)
        #     self._pilImage = PIL.Image.fromarray(arr, 'RGB')
        # except IOError:
        #     raise TileSourceException('File cannot be opened via ImageJ.')

        # dims = ij.py.dims(img)
        # self.sizeX = dims[0]
        # self.sizeY = dims[1]
        # self.tileWidth = dims[0]
        # self.tileHeight = dims[1]
        self.levels = 1

        # Throw an exception if too big
        if self.tileWidth <= 0 or self.tileHeight <= 0:
            raise TileSourceException('BioFormats tile size is invalid.')

        # img_from_ij = ij.py.from_java(ij_img)
        # # Fix the axis order
        # img_as_rgb = np.moveaxis(img_as_8bit, 0, -1)

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, mayRedirect=False, **kwargs):
        if z != 0:
            raise TileSourceException('z layer does not exist')
        if x != 0:
            raise TileSourceException('x is outside layer')
        if y != 0:
            raise TileSourceException('y is outside layer')
        return self._outputTile(self._pilImage, 'PIL', x, y, z,
                                pilImageAllowed, **kwargs)
