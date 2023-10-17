import json
import os
from unittest import TestCase

import large_image_source_mapnik

import large_image

from .datastore import datastore
from .source_geo_base import _BaseGeoTests


class InvalidMapnikTests:
    # TODO: fix styling on Mapnik source to match GDAL and delete this test

    def testTileLinearStyleFromGeotiffs(self):
        testDir = os.path.dirname(os.path.realpath(__file__))
        imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
        style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                            'palette': 'matplotlib.Plasma_6',
                            'scheme': 'linear'})
        source = large_image_source_mapnik.open(
            imagePath, projection='EPSG:3857', style=style)
        image = source.getTile(22, 51, 7, encoding='PNG')
        self._assertImageMatches(image, 'geotiff_style_linear_7_22_51')

    def testPixel(self):
        testDir = os.path.dirname(os.path.realpath(__file__))
        imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')

        # Test in pixel coordinates
        source = large_image_source_mapnik.open(imagePath)
        pixel = source.getPixel(region={'left': 212, 'top': 198})
        assert pixel == {
            'r': 62, 'g': 65, 'b': 66, 'a': 255,
            'bands': {1: 62.0, 2: 65.0, 3: 66.0},
            'value': [62, 65, 66, 255]}
        pixel = source.getPixel(region={'left': 2120, 'top': 198})
        assert pixel == {}

        # Test with a projection
        source = large_image_source_mapnik.open(imagePath, projection='EPSG:3857')
        pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
        assert pixel == {
            'r': 77, 'g': 82, 'b': 84, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [77, 82, 84, 255]}

        # Check if the point is outside of the image
        pixel = source.getPixel(region={'left': 10000000, 'top': 4000000, 'units': 'projection'})
        assert pixel['a'] == 0

        # Test with styles
        style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                            'scheme': 'discrete',
                            'palette': 'matplotlib.Plasma_6'})
        source = large_image_source_mapnik.open(
            imagePath, projection='EPSG:3857', style=style)
        pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
        assert pixel == {
            'r': 225, 'g': 100, 'b': 98, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [225, 100, 98, 255]}

        # Test with palette as an array of colors
        style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                            'scheme': 'discrete',
                            'palette': ['#0000ff', '#00ff00', '#ff0000']})
        source = large_image_source_mapnik.open(
            imagePath, projection='EPSG:3857', style=style)
        pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
        assert pixel == {
            'r': 0, 'g': 255, 'b': 0, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [0, 255, 0, 255]}

        # Test with projection units
        source = large_image_source_mapnik.open(imagePath, projection='EPSG:3857')
        pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
        assert pixel == {
            'r': 77, 'g': 82, 'b': 84, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [77, 82, 84, 255]}
        pixel = source.getPixel(region={'left': -117.975, 'top': 33.865, 'units': 'WGS84'})
        assert pixel == {
            'r': 77, 'g': 82, 'b': 84, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [77, 82, 84, 255]}
        # When the tile has a different projection, the pixel is the same as
        # the band values.
        source = large_image_source_mapnik.open(imagePath)
        pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
        assert pixel == {
            'r': 77, 'g': 82, 'b': 84, 'a': 255,
            'bands': {1: 77.0, 2: 82.0, 3: 84.0},
            'value': [77, 82, 84, 255]}


class MapnikSourceTests(InvalidMapnikTests, _BaseGeoTests, TestCase):

    basemodule = large_image_source_mapnik
    baseclass = large_image_source_mapnik.MapnikFileTileSource

    def testProj4Proj(self):
        # Test obtaining pyproj.Proj projection values
        proj4Proj = large_image_source_mapnik.GDALFileTileSource._proj4Proj

        proj = proj4Proj(b'epsg:4326')
        assert proj4Proj('epsg:4326').srs == proj.srs
        assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
        assert proj4Proj(4326) is None

    def testTileFromNetCDF(self):
        imagePath = datastore.fetch('04091217_ruc.nc')
        source = self.basemodule.open(imagePath)
        tileMetadata = source.getMetadata()

        assert tileMetadata['tileWidth'] == 256
        assert tileMetadata['tileHeight'] == 256
        assert tileMetadata['sizeX'] == 93
        assert tileMetadata['sizeY'] == 65
        assert tileMetadata['levels'] == 1
        assert tileMetadata['bounds']['srs'].strip() == 'epsg:4326'
        assert tileMetadata['geospatial']

        # Getting the metadata with a specified projection will be different
        source = self.basemodule.open(
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
