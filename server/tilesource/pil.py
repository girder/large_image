#!/usr/bin/env python
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
import six

import PIL.Image

try:
    from girder import logger
except ImportError:
    import logging as logger
    logger.getLogger().setLevel(logger.INFO)

try:
    import numpy
except ImportError:
    logger.warning('Error: Could not import numpy')
    numpy = None

from .base import FileTileSource, TileSourceException
from ..cache_util import LruCacheMetaclass, strhash, methodcache

try:
    import girder
    from girder.models.setting import Setting
    from .base import GirderTileSource
    from .. import constants
    import cherrypy
except ImportError:
    girder = None


def getMaxSize(size=None):
    """
    Get the maximum width and height that we allow for an image.

    :param size: the requested maximum size.  This is either a number to use
        for both width and height, or an object with {'width': (width),
        'height': height} in pixels.  If None, the default max size is used.
    :returns: maxWidth, maxHeight in pixels.  0 means no images are allowed.
    """
    # We may want different defaults if the image will be sent to a viewer, as
    # texture buffers are typically 2k to 16k square.  We may want to read the
    # default value from girder settings or config.
    maxWidth = maxHeight = 4096
    if girder:
        maxWidth = maxHeight = int(Setting().get(
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE))
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

    def __init__(self, path, maxSize=None, **kwargs):
        """
        Initialize the tile class.

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

        try:
            self._pilImage = PIL.Image.open(largeImagePath)
        except IOError:
            raise TileSourceException('File cannot be opened via PIL.')
        # If this is encoded as a 32-bit integer or a 32-bit float, convert it
        # to an 8-bit integer.  This expects the source value to either have a
        # maximum of 1, 2^8-1, 2^16-1, 2^24-1, or 2^32-1, and scales it to
        # [0, 255]
        pilImageMode = self._pilImage.mode.split(';')[0]
        if pilImageMode in ('I', 'F') and numpy:
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
        maxWidth, maxHeight = getMaxSize(maxSize)
        if self.tileWidth > maxWidth or self.tileHeight > maxHeight:
            raise TileSourceException('PIL tile size is too large.')

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


if girder:
    class PILGirderTileSource(PILFileTileSource, GirderTileSource):
        """
        Provides tile access to Girder items with a PIL file.
        """
        # Cache size is based on what the class needs, which does not include
        # individual tiles
        cacheName = 'tilesource'
        name = 'pil'

        @staticmethod
        def getLRUHash(*args, **kwargs):
            return strhash(
                super(PILGirderTileSource, PILGirderTileSource).getLRUHash(
                    *args, **kwargs),
                kwargs.get('maxSize', args[1] if len(args) >= 2 else None))

        def getState(self):
            return super(PILGirderTileSource, self).getState() + ',' + str(
                self.maxSize)

        @methodcache()
        def getTile(self, x, y, z, pilImageAllowed=False, mayRedirect=False, **kwargs):
            if z != 0:
                raise TileSourceException('z layer does not exist')
            if x != 0:
                raise TileSourceException('x is outside layer')
            if y != 0:
                raise TileSourceException('y is outside layer')
            if (mayRedirect and not pilImageAllowed and
                    self._pilFormatMatches(self._pilImage, mayRedirect, **kwargs)):
                url = '%s/api/v1/file/%s/download' % (
                    cherrypy.request.base, self.item['largeImage']['fileId'])
                raise cherrypy.HTTPRedirect(url)
            return self._outputTile(self._pilImage, 'PIL', x, y, z,
                                    pilImageAllowed, **kwargs)
