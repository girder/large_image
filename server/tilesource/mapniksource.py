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

import gdal
import osr
import mapnik
from pyproj import Proj, transform
from PIL import Image
import math
import six

from .base import FileTileSource, TileSourceException, TILE_FORMAT_PIL
from ..cache_util import LruCacheMetaclass, methodcache

try:
    import girder
    from girder import logger
    from .base import GirderTileSource
except ImportError:
    girder = None
    import logging as logger
    logger.getLogger().setLevel(logger.INFO)


@six.add_metaclass(LruCacheMetaclass)
class MapnikTileSource(FileTileSource):
    """
    Provides tile access to geospatial files.
    """

    cacheName = 'tilesource'
    name = 'mapnikfile'

    def __init__(self, path, **kwargs):
        super(MapnikTileSource, self).__init__(path, **kwargs)
        self.dataset = gdal.Open(self._getLargeImagePath())
        # Earth circumference for web mercator
        self.circumference = 40075016.68557849
        try:
            self.imageSizeX = self.dataset.RasterXSize
            self.imageSizeY = self.dataset.RasterYSize
        except AttributeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        self.tileSize = 256
        self.tileWidth = self.tileSize
        self.tileHeight = self.tileSize
        try:
            self.levels = self.getMaximumZoomLevel(self.getPixelSizeInMeters())
        except RuntimeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        # Report sizeX and sizeY as the whole world
        self.sizeX = 2 ** (self.levels - 1) * self.tileWidth
        self.sizeY = 2 ** (self.levels - 1) * self.tileHeight

    def getProj4String(self):
        """Returns proj4 string for the given dataset"""
        wkt = self.dataset.GetProjection()
        proj = osr.SpatialReference()
        proj.ImportFromWkt(wkt)

        return proj.ExportToProj4()

    def getMaximumZoomLevel(self, pixelSize):
        """Returns appropriate max zoom level for a layer"""
        maxZoom = 0
        for i in range(1, 30):
            mercatorPixelSize = self.getPixelSize(i)
            if mercatorPixelSize < pixelSize:
                maxZoom = i + 1
                break

        return maxZoom

    def getPixelSizeInMeters(self):
        """Returns pixel size in meters"""
        xmin, ymin, xmax, ymax = self.getBounds()
        inProj = Proj(self.getProj4String())
        outProj = Proj(self.getMercatorProjection())
        xmin, ymin = transform(inProj, outProj, xmin, ymin)
        xmax, ymax = transform(inProj, outProj, xmax, ymax)

        xres = abs((xmax-xmin)/self.imageSizeX)
        yres = abs((ymax-ymin)/self.imageSizeY)

        return min(xres, yres)

    def getNativeMagnification(self):
        """
        Get the magnification at the base level.

        :return: width of a pixel in mm, height of a pixel in mm.
        """
        scale = self.getPixelSize(self.levels - 1) * 100  # convert to mm
        return {
            'magnification': None,
            'mm_x': scale,
            'mm_y': scale
        }

    def getBounds(self):
        """Returns bounds of an image"""
        geotransform = self.dataset.GetGeoTransform()
        xmax = geotransform[0] + (self.dataset.RasterXSize * geotransform[1])
        ymin = geotransform[3] + (self.dataset.RasterYSize * geotransform[5])
        xmin = geotransform[0]
        ymax = geotransform[3]
        return xmin, ymin, xmax, ymax

    def getMetadata(self):
        geospatial = False
        if self.dataset.GetProjection():
            geospatial = True
        xmin, xmax, ymin, ymax = self.getBounds()
        mag = self.getNativeMagnification()
        return {
            'geospatial': geospatial,
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'srs': self.getProj4String(),
            'imageSize': {
                'x': self.imageSizeX,
                'y': self.imageSizeY
            },
            'bounds': {
                'xmin': xmin,
                'xmax': xmax,
                'ymin': ymin,
                'ymax': ymax
            },
            'mm_x': mag['mm_x'],
            'mm_y': mag['mm_y'],
            'circumference': self.circumference,
        }

    def getPixelSize(self, zoom):
        """Returns an approximate pixel size for a given zoom level"""

        equatorLatitude = 0
        # For simplification we assume everything is equator latitude
        pixelSize = self.circumference * math.cos(equatorLatitude) / 2 ** zoom / self.tileWidth
        return pixelSize

    def getTileCorners(self, z, x, y, tileSize=None):
        """Returns bounds of a tile for a given x,y,z index"""

        numberOfTiles = 2.0 ** (z * 2)
        pixelSize = self.getPixelSize(z)
        circumference = self.circumference
        xmin = x / numberOfTiles * (circumference * 2 ** z) - circumference / 2
        ymin = y / numberOfTiles * (circumference * 2 ** z) - circumference / 2
        xmax = xmin + pixelSize * tileSize
        ymax = ymin + pixelSize * tileSize

        return xmin, ymin, xmax, ymax

    def addStyle(self, m):
        """Attaches raster style option to mapnik raster layer"""
        style = mapnik.Style()
        rule = mapnik.Rule()
        sym = mapnik.RasterSymbolizer()
        rule.symbols.append(sym)
        style.rules.append(rule)
        m.append_style('Raster Style', style)
        lyr = mapnik.Layer('layer')
        lyr.srs = self.getProj4String()
        lyr.datasource = mapnik.Gdal(base='',
                                     file=self._getLargeImagePath(),
                                     band=-1)
        lyr.styles.append('Raster Style')
        m.layers.append(lyr)

    @staticmethod
    def getMercatorProjection():
        """Returns proj4 string for mercator projection"""
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(3857)

        return srs.ExportToProj4()

    @methodcache()
    def getTile(self, x, y, z, **kwargs):
        # xyz to tms conversion formula for y
        y = (2 ** z) - y - 1
        mapSrs = self.getMercatorProjection()
        m = mapnik.Map(self.tileWidth, self.tileHeight, mapSrs)
        xmin, ymin, xmax, ymax = self.getTileCorners(z, x, y, tileSize=self.tileSize)
        m.zoom_to_box(mapnik.Box2d(xmin, ymin, xmax, ymax))
        img = mapnik.Image(self.tileWidth, self.tileHeight)
        self.addStyle(m)
        mapnik.render(m, img)
        png = Image.frombytes('RGBA', (self.tileWidth, self.tileHeight), img.tostring())
        return self._outputTile(png, TILE_FORMAT_PIL, x, y, z, **kwargs)


if girder:
    class MapnikGirderTileSource(MapnikTileSource, GirderTileSource):
        """
        Provides tile access to Girder items for mapnik layers.
        """
        name = 'mapnik'
        cacheName = 'tilesource'
