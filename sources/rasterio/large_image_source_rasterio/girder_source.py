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

import packaging.version  # noqa F401
from girder_large_image.girder_tilesource import GirderTileSource

from large_image.config import getConfig

from . import RasterioFileTileSource


class RasterioGirderTileSource(RasterioFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items for rasterio layers.
    """

    name = 'rasterio'
    cacheName = 'tilesource'

    @staticmethod
    def getLRUHash(*args, **kwargs):
        projection = kwargs.get(
            'projection',
            args[1] if len(args) >= 2 else None,
        ) or getConfig('default_projection')
        unitPerPixel = kwargs.get('unitsPerPixel', args[3] if len(args) >= 4 else None)

        return (
            GirderTileSource.getLRUHash(*args, **kwargs) +
            f',{projection},{unitPerPixel}'
        )
