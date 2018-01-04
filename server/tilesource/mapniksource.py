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
import math
import PIL.Image
import pyproj
import six

from .base import FileTileSource, TileSourceException, TILE_FORMAT_PIL, TileInputUnits
from ..cache_util import LruCacheMetaclass, methodcache, strhash

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

    def __init__(self, path, projection=None, **kwargs):
        super(MapnikTileSource, self).__init__(path, **kwargs)
        self._bounds = {}
        self.dataset = gdal.Open(self._getLargeImagePath())
        self.tileSize = 256
        self.tileWidth = self.tileSize
        self.tileHeight = self.tileSize
        if projection and projection.lower().startswith('epsg:'):
            projection = '+init=' + projection.lower()
        if projection and not isinstance(projection, six.binary_type):
            projection = projection.encode('utf8')
        self.projection = projection
        try:
            self.sourceSizeX = self.sizeX = self.dataset.RasterXSize
            self.sourceSizeY = self.sizeY = self.dataset.RasterYSize
        except AttributeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        try:
            scale = self.getPixelSizeInMeters()
        except RuntimeError:
            raise TileSourceException('File cannot be opened via Mapnik.')
        if not scale:
            raise TileSourceException(
                'File does not have a projected scale, so will not be '
                'opened via Mapnik.')
        self.sourceLevels = self.levels = int(max(0, math.ceil(max(
            math.log(self.sizeX / self.tileWidth),
            math.log(self.sizeY / self.tileHeight)) / math.log(2))) + 1)
        if self.projection:
            # Note: this needs to change for projections that aren't spanning
            # -180 to +180 degrees horizontally.  We should accept this as a
            # parameter eventually.
            inProj = pyproj.Proj('+init=epsg:4326')
            outProj = pyproj.Proj(self.projection)
            if outProj.is_latlong():
                raise TileSourceException(
                    'Projection must not be geographic (it needs to use '
                    'linear units, not longitude/latitude).')
            equator = pyproj.transform(inProj, outProj, [-180, 180, 0], [0, 0, 0])
            self.unitsAcrossLevel0 = equator[0][1] - equator[0][0]
            self.projectionOrigin = (equator[0][2], equator[1][2])
            # Calculate values for this projection
            self.levels = int(max(int(math.ceil(
                math.log(self.unitsAcrossLevel0 / self.getPixelSizeInMeters() / self.tileWidth) /
                math.log(2))) + 1, 1))
            # Report sizeX and sizeY as the whole world
            self.sizeX = 2 ** (self.levels - 1) * self.tileWidth
            self.sizeY = 2 ** (self.levels - 1) * self.tileHeight

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return strhash(
            super(MapnikTileSource, MapnikTileSource).getLRUHash(
                *args, **kwargs),
            kwargs.get('projection'))

    def getProj4String(self):
        """
        Returns proj4 string for the given dataset

        :returns: The proj4 string or None.
        """
        wkt = self.dataset.GetProjection()
        if not wkt:
            return
        proj = osr.SpatialReference()
        proj.ImportFromWkt(wkt)
        return proj.ExportToProj4()

    def getPixelSizeInMeters(self):
        """
        Get the approximate base pixel size in meters.  This is calculated as
        the average scale of the four edges in the WGS84 ellipsoid.

        :returns: the pixel size in meters or None.
        """
        bounds = self.getBounds('+init=epsg:4326')
        if not bounds:
            return
        geod = pyproj.Geod(ellps='WGS84')
        az12, az21, s1 = geod.inv(bounds['ul']['x'], bounds['ul']['y'],
                                  bounds['ur']['x'], bounds['ur']['y'])
        az12, az21, s2 = geod.inv(bounds['ur']['x'], bounds['ur']['y'],
                                  bounds['lr']['x'], bounds['lr']['y'])
        az12, az21, s3 = geod.inv(bounds['lr']['x'], bounds['lr']['y'],
                                  bounds['ll']['x'], bounds['ll']['y'])
        az12, az21, s4 = geod.inv(bounds['ll']['x'], bounds['ll']['y'],
                                  bounds['ul']['x'], bounds['ul']['y'])
        return (s1 + s2 + s3 + s4) / (self.sourceSizeX * 2 + self.sourceSizeY * 2)

    def getNativeMagnification(self):
        """
        Get the magnification at the base level.

        :return: width of a pixel in mm, height of a pixel in mm.
        """
        scale = self.getPixelSizeInMeters()
        if not scale:
            return {
                'magnification': None,
                'mm_x': None,
                'mm_y': None
            }
        return {
            'magnification': None,
            'mm_x': scale * 100,
            'mm_y': scale * 100
        }

    def getBounds(self, srs=None):
        """
        Returns bounds of the image.

        :param srs: the projection for the bounds.  None for the default.
        :returns: an object with the four corners and the projection that was
            used.  None if we don't know the original projection.
        """
        if srs not in self._bounds:
            gt = self.dataset.GetGeoTransform()
            nativeSrs = self.getProj4String()
            if not nativeSrs:
                self._bounds[srs] = None
                return
            bounds = {
                'll': {
                    'x': gt[0] + self.sourceSizeY * gt[2],
                    'y': gt[3] + self.sourceSizeY * gt[5]
                },
                'ul': {
                    'x': gt[0],
                    'y': gt[3],
                },
                'lr': {
                    'x': gt[0] + self.sourceSizeX * gt[1] + self.sourceSizeY * gt[2],
                    'y': gt[3] + self.sourceSizeX * gt[4] + self.sourceSizeY * gt[5]
                },
                'ur': {
                    'x': gt[0] + self.sourceSizeX * gt[1],
                    'y': gt[3] + self.sourceSizeX * gt[4]
                },
                'srs': nativeSrs,
            }
            if srs and srs != nativeSrs:
                inProj = pyproj.Proj(nativeSrs)
                outProj = pyproj.Proj(srs)
                for key in ('ll', 'ul', 'lr', 'ur'):
                    pt = pyproj.transform(inProj, outProj, bounds[key]['x'], bounds[key]['y'])
                    bounds[key]['x'] = pt[0]
                    bounds[key]['y'] = pt[1]
                bounds['srs'] = srs
            bounds['xmin'] = min(bounds['ll']['x'], bounds['ul']['x'],
                                 bounds['lr']['x'], bounds['ur']['x'])
            bounds['xmax'] = max(bounds['ll']['x'], bounds['ul']['x'],
                                 bounds['lr']['x'], bounds['ur']['x'])
            bounds['ymin'] = min(bounds['ll']['y'], bounds['ul']['y'],
                                 bounds['lr']['y'], bounds['ur']['y'])
            bounds['ymax'] = max(bounds['ll']['y'], bounds['ul']['y'],
                                 bounds['lr']['y'], bounds['ur']['y'])
            self._bounds[srs] = bounds
        return self._bounds[srs]

    def getMetadata(self):
        metadata = {
            'geospatial': bool(self.dataset.GetProjection()),
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'sourceLevels': self.sourceLevels,
            'sourceSizeX': self.sourceSizeX,
            'sourceSizeY': self.sourceSizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
            'bounds': self.getBounds(self.projection),
            'sourceBounds': self.getBounds(),
        }
        metadata.update(self.getNativeMagnification())
        return metadata

    def getTileCorners(self, z, x, y):
        """
        Returns bounds of a tile for a given x,y,z index.

        :param z: tile level
        :param x: tile offset from left.
        :param y: tile offset from right
        :returns: (xmin, ymin, xmax, ymax) in the current projection or base
            pixels.
        """
        if self.projection:
            # Scale tile into the range [-0.5, 0.5], [-0.5, 0.5]
            xmin = -0.5 + float(x) / 2.0 ** z
            xmax = -0.5 + float(x + 1) / 2.0 ** z
            ymin = 0.5 - float(y + 1) / 2.0 ** z
            ymax = 0.5 - float(y) / 2.0 ** z
            # Convert to projection coordinates
            xmin = self.projectionOrigin[0] + xmin * self.unitsAcrossLevel0
            xmax = self.projectionOrigin[0] + xmax * self.unitsAcrossLevel0
            ymin = self.projectionOrigin[1] + ymin * self.unitsAcrossLevel0
            ymax = self.projectionOrigin[1] + ymax * self.unitsAcrossLevel0
        else:
            xmin = 2 ** (self.sourceLevels - 1 - z) * x * self.tileWidth
            ymin = 2 ** (self.sourceLevels - 1 - z) * y * self.tileHeight
            xmax = xmin + 2 ** (self.sourceLevels - 1 - z) * self.tileWidth
            ymax = ymin + 2 ** (self.sourceLevels - 1 - z) * self.tileHeight
            ymin, ymax = self.sourceSizeY - ymax, self.sourceSizeY - ymin
        return xmin, ymin, xmax, ymax

    def addStyle(self, m):
        """
        Attaches raster style option to mapnik raster layer.

        :param m: mapnik map.
        """
        style = mapnik.Style()
        rule = mapnik.Rule()
        sym = mapnik.RasterSymbolizer()
        rule.symbols.append(sym)
        style.rules.append(rule)
        m.append_style('Raster Style', style)

    @methodcache()
    def getTile(self, x, y, z, **kwargs):
        if self.projection:
            mapSrs = self.projection
            layerSrs = self.getProj4String()
            extent = None
        else:
            mapSrs = '+proj=longlat +axis=esu'
            layerSrs = '+proj=longlat +axis=esu'
            extent = '0 0 %d %d' % (self.sourceSizeX, self.sourceSizeY)
        m = mapnik.Map(self.tileWidth, self.tileHeight, mapSrs)
        xmin, ymin, xmax, ymax = self.getTileCorners(z, x, y)
        m.zoom_to_box(mapnik.Box2d(xmin, ymin, xmax, ymax))
        img = mapnik.Image(self.tileWidth, self.tileHeight)
        self.addStyle(m)
        lyr = mapnik.Layer('layer')
        lyr.srs = layerSrs
        if extent:
            lyr.datasource = mapnik.Gdal(
                base='', file=self._getLargeImagePath(), band=-1, extent=extent)
        else:
            lyr.datasource = mapnik.Gdal(
                base='', file=self._getLargeImagePath(), band=-1)
        lyr.styles.append('Raster Style')
        m.layers.append(lyr)
        mapnik.render(m, img)
        pilimg = PIL.Image.frombytes('RGBA', (img.width(), img.height()), img.tostring())
        return self._outputTile(pilimg, TILE_FORMAT_PIL, x, y, z, **kwargs)

    def _getRegionBounds(self, metadata, left=None, top=None, right=None,
                         bottom=None, width=None, height=None, units=None,
                         **kwargs):
        """
        Given a set of arguments that can include left, right, top, bottom,
        width, height, and units, generate actual pixel values for left, top,
        right, and bottom.  If units is `'projection'`, use the source's
        projection.  Otherwise, just use the super function.

        :param metadata: the metadata associated with this source.
        :param left: the left edge (inclusive) of the region to process.
        :param top: the top edge (inclusive) of the region to process.
        :param right: the right edge (exclusive) of the region to process.
        :param bottom: the bottom edge (exclusive) of the region to process.
        :param width: the width of the region to process.  Ignored if both
            left and right are specified.
        :param height: the height of the region to process.  Ignores if both
            top and bottom are specified.
        :param units: either 'projection' or one of the super's values.
        :param **kwargs: optional parameters.  See above.
        :returns: left, top, right, bottom bounds in pixels.
        """
        units = TileInputUnits[units]
        if units == 'projection' and self.projection:
            bounds = self.getBounds(self.projection)
            # Fill in missing values
            if left is None:
                left = bounds['xmin'] if right is None or width is None else right - width
            if right is None:
                right = bounds['xmax'] if width is None else left + width
            if top is None:
                top = bounds['ymax'] if bottom is None or width is None else bottom - width
            if bottom is None:
                bottom = bounds['ymin'] if width is None else top + width
            width = height = None
            # Convert to [-0.5, 0.5], [-0.5, 0.5] coordinate range
            left = (left - self.projectionOrigin[0]) / self.unitsAcrossLevel0
            right = (right - self.projectionOrigin[0]) / self.unitsAcrossLevel0
            top = (top - self.projectionOrigin[1]) / self.unitsAcrossLevel0
            bottom = (bottom - self.projectionOrigin[1]) / self.unitsAcrossLevel0
            # Convert to world=wide 'base pixels' and crop to the world
            xScale = 2 ** (self.levels - 1) * self.tileWidth
            yScale = 2 ** (self.levels - 1) * self.tileHeight
            left = max(0, min(xScale, (0.5 + left) * xScale))
            right = max(0, min(xScale, (0.5 + right) * xScale))
            top = max(0, min(yScale, (0.5 - top) * yScale))
            bottom = max(0, min(yScale, (0.5 - bottom) * yScale))
            # Ensire correct ordering
            left, right = min(left, right), max(left, right)
            top, bottom = min(top, bottom), max(top, bottom)
            units = 'base_pixels'
        return super(MapnikTileSource, self)._getRegionBounds(
            metadata, left, top, right, bottom, width, height, units, **kwargs)

    @methodcache()
    def getThumbnail(self, width=None, height=None, levelZero=False, **kwargs):
        """
        Get a basic thumbnail from the current tile source.  Aspect ratio is
        preserved.  If neither width nor height is given, a default value is
        used.  If both are given, the thumbnail will be no larger than either
        size.

        :param width: maximum width in pixels.
        :param height: maximum height in pixels.
        :param levelZero: if true, always use the level zero tile.  Otherwise,
            the thumbnail is generated so that it is never upsampled.
        :param **kwargs: optional arguments.  Some options are encoding,
            jpegQuality, jpegSubsampling, and tiffCompression.
        :returns: thumbData, thumbMime: the image data and the mime type.
        """
        if self.projection:
            if ((width is not None and width < 2) or
                    (height is not None and height < 2)):
                raise ValueError('Invalid width or height.  Minimum value is 2.')
            if width is None and height is None:
                width = height = 256
            params = dict(kwargs)
            params['output'] = {'maxWidth': width, 'maxHeight': height}
            params['region'] = {'units': 'projection'}
            return self.getRegion(**params)
        return super(MapnikTileSource, self).getThumbnail(width, height, levelZero, **kwargs)


if girder:
    class MapnikGirderTileSource(MapnikTileSource, GirderTileSource):
        """
        Provides tile access to Girder items for mapnik layers.
        """
        name = 'mapnik'
        cacheName = 'tilesource'


TileInputUnits['projection'] = 'projection'
TileInputUnits['proj'] = 'projection'
