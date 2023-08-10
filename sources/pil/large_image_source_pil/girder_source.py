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

import cherrypy
from girder_large_image.constants import PluginSettings
from girder_large_image.girder_tilesource import GirderTileSource

from girder.models.setting import Setting
from large_image.cache_util import methodcache
from large_image.constants import TILE_FORMAT_PIL
from large_image.exceptions import TileSourceError

from . import PILFileTileSource


class PILGirderTileSource(PILFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with a PIL file.
    """

    # Cache size is based on what the class needs, which does not include
    # individual tiles
    cacheName = 'tilesource'
    name = 'pil'

    def defaultMaxSize(self):
        return int(Setting().get(
            PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE))

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return GirderTileSource.getLRUHash(*args, **kwargs) + ',%s' % (str(
            kwargs.get('maxSize', args[1] if len(args) >= 2 else None)))

    def getState(self):
        return super().getState() + ',' + str(
            self._maxSize)

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                mayRedirect=False, **kwargs):
        if z != 0:
            msg = 'z layer does not exist'
            raise TileSourceError(msg)
        if x != 0:
            msg = 'x is outside layer'
            raise TileSourceError(msg)
        if y != 0:
            msg = 'y is outside layer'
            raise TileSourceError(msg)
        if (mayRedirect and not pilImageAllowed and not numpyAllowed and
                cherrypy.request and
                self._pilFormatMatches(self._pilImage, mayRedirect, **kwargs)):
            url = '%s/api/v1/file/%s/download' % (
                cherrypy.request.base, self.item['largeImage']['fileId'])
            raise cherrypy.HTTPRedirect(url)
        return self._outputTile(self._pilImage, TILE_FORMAT_PIL, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)
