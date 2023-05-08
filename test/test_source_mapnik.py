from unittest import TestCase

import large_image_source_mapnik

import large_image

from .datastore import datastore
from .source_geo_base import _BaseGeoTests


class MapnikSourceTests(_BaseGeoTests, TestCase):

    def open(self, *args, **kwargs):
        return large_image_source_mapnik.open(*args, **kwargs)

    def testProj4Proj(self):
        # Test obtaining pyproj.Proj projection values
        proj4Proj = large_image_source_mapnik.GDALFileTileSource._proj4Proj

        proj = proj4Proj(b'epsg:4326')
        assert proj4Proj('epsg:4326').srs == proj.srs
        assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
        assert proj4Proj(4326) is None

    def testTileFromNetCDF(self):
        imagePath = datastore.fetch('04091217_ruc.nc')
        source = self.open(imagePath)
        tileMetadata = source.getMetadata()

        assert tileMetadata['tileWidth'] == 256
        assert tileMetadata['tileHeight'] == 256
        assert tileMetadata['sizeX'] == 93
        assert tileMetadata['sizeY'] == 65
        assert tileMetadata['levels'] == 1
        assert tileMetadata['bounds']['srs'].strip() == 'epsg:4326'
        assert tileMetadata['geospatial']

        # Getting the metadata with a specified projection will be different
        source = self.open(
            imagePath, projection='EPSG:3857')
        tileMetadata = source.getMetadata()

        assert tileMetadata['tileWidth'] == 256
        assert tileMetadata['tileHeight'] == 256
        assert tileMetadata['sizeX'] == 512
        assert tileMetadata['sizeY'] == 512
        assert tileMetadata['levels'] == 2
        assert tileMetadata['bounds']['srs'] in ('+init=epsg:3857', 'epsg:3857')
        assert tileMetadata['geospatial']

    def testTileSourceFromNetCDF(self):
        imagePath = datastore.fetch('04091217_ruc.nc')
        ts = large_image.open(imagePath)
        assert 'mapnik' in ts.name
