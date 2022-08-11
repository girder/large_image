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

import re

import packaging.version
from girder_large_image.girder_tilesource import GirderTileSource

from girder import logger
from girder.models.file import File

from . import RasterioFileTileSource


class RasterioGirderTileSource(RasterioFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items for rasterio layers.
    """

    name = "rasterio"
    cacheName = "tilesource"

    @staticmethod
    def getLRUHash(*args, **kwargs):
        projection = kwargs.get("projection", args[1] if len(args) >= 2 else None)
        unitPerPixel = kwargs.get("unitsPerPixel", args[3] if len(args) >= 4 else None)

        return (
            GirderTileSource.getLRUHash(*args, **kwargs)
            + f",{projection},{unitPerPixel}"
        )

    def _getLargeImagePath(self):
        """
        GDAL can read directly from http/https/ftp via /vsicurl. If this
        is a link file, try to use it.
        """
        try:
            largeImageFileId = self.item["largeImage"]["fileId"]
            largeImageFile = File().load(largeImageFileId, force=True)
            if (
                largeImageFile.get("linkUrl")
                and not largeImageFile.get("assetstoreId")
                and re.match(r"(http(|s)|ftp)://", largeImageFile["linkUrl"])
            ):
                largeImagePath = "/vsicurl/" + largeImageFile["linkUrl"]
                logger.info("Using %s" % largeImagePath)
                return largeImagePath
        except Exception:
            pass
        return GirderTileSource._getLargeImagePath(self)
