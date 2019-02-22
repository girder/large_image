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

import json
import math
import numpy
import os
import six
from pkg_resources import DistributionNotFound, get_distribution

import PIL.Image

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache, strhash
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


def getMaxSize(size=None, maxDefault=4096):
    """
    Get the maximum width and height that we allow for an image.

    :param size: the requested maximum size.  This is either a number to use
        for both width and height, or an object with {'width': (width),
        'height': height} in pixels.  If None, the default max size is used.
    :param maxDefault: a default value to use for width and height.
    :returns: maxWidth, maxHeight in pixels.  0 means no images are allowed.
    """
    maxWidth = maxHeight = maxDefault
    if size is not None:
        if isinstance(size, dict):
            maxWidth = size.get('width', maxWidth)
            maxHeight = size.get('height', maxHeight)
        else:
            maxWidth = maxHeight = size
    # We may want to put an upper limit on what is requested so it can't be
    # completely overridden.
    return maxWidth, maxHeight


@six.add_metaclass(LruCacheMetaclass)
class PILFileTileSource(FileTileSource):
    """
    Provides tile access to single image PIL files.
    """
    cacheName = 'tilesource'
    name = 'pilfile'
    # No extensions or mime types are explicilty added for the PIL tile source,
    # as it should always be a fallback source

    def __init__(self, path, maxSize=None, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: the associated file path.
        :param maxSize: either a number or an object with {'width': (width),
            'height': height} in pixels.  If None, the default max size is
            used.
        """
        super(PILFileTileSource, self).__init__(path, **kwargs)

        if isinstance(maxSize, six.string_types):
            try:
                maxSize = json.loads(maxSize)
            except Exception:
                raise TileSourceException(
                    'maxSize must be None, an integer, a dictionary, or a '
                    'JSON string that converts to one of those.')
        self.maxSize = maxSize

        largeImagePath = self._getLargeImagePath()

        # Some formats shouldn't be read this way, even if they could.  For
        # instances, mirax (mrxs) files look like JPEGs, but opening them as
        # such misses most of the data.
        if os.path.splitext(largeImagePath)[1] in ('.mrxs', ):
            raise TileSourceException('File cannot be opened via PIL.')
        try:
            self._pilImage = PIL.Image.open(largeImagePath)
        except IOError:
            raise TileSourceException('File cannot be opened via PIL.')
        # If this is encoded as a 32-bit integer or a 32-bit float, convert it
        # to an 8-bit integer.  This expects the source value to either have a
        # maximum of 1, 2^8-1, 2^16-1, 2^24-1, or 2^32-1, and scales it to
        # [0, 255]
        pilImageMode = self._pilImage.mode.split(';')[0]
        if pilImageMode in ('I', 'F'):
            imgdata = numpy.asarray(self._pilImage)
            maxval = 256 ** math.ceil(math.log(numpy.max(imgdata) + 1, 256)) - 1
            self._pilImage = PIL.Image.fromarray(numpy.uint8(numpy.multiply(
                imgdata, 255.0 / maxval)))
        self.sizeX = self._pilImage.width
        self.sizeY = self._pilImage.height
        # We have just one tile which is the entire image.
        self.tileWidth = self.sizeX
        self.tileHeight = self.sizeY
        self.levels = 1
        # Throw an exception if too big
        if self.tileWidth <= 0 or self.tileHeight <= 0:
            raise TileSourceException('PIL tile size is invalid.')
        maxWidth, maxHeight = getMaxSize(maxSize, self.defaultMaxSize())
        if self.tileWidth > maxWidth or self.tileHeight > maxHeight:
            raise TileSourceException('PIL tile size is too large.')

    def defaultMaxSize(self):
        """
        Get the default max size from the config settings.

        :returns: the default max size.
        """
        return int(config.getConfig('max_small_image_size', 4096))

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(PILFileTileSource, PILFileTileSource).getLRUHash(
                *args, **kwargs),
            kwargs.get('maxSize'))

    def getState(self):
        return super(PILFileTileSource, self).getState() + ',' + str(
            self.maxSize)

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
