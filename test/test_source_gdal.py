import os

import numpy
import PIL.ImageChops
import pytest
from unittest import TestCase

import large_image_source_gdal

from .datastore import datastore
from .source_geo_base import _GDALBaseSourceTest


class GDALSourceTests(_GDALBaseSourceTest, TestCase):

    def open(self, *args, **kwargs):
        return large_image_source_gdal.open(*args, **kwargs)

    def testProj4Proj(self):
        # Test obtaining pyproj.Proj projection values
        proj4Proj = large_image_source_gdal.GDALFileTileSource._proj4Proj

        proj = proj4Proj(b'epsg:4326')
        assert proj4Proj('epsg:4326').srs == proj.srs
        assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
        assert proj4Proj(4326) is None

    def testGetTiledRegion(self):
        imagePath = datastore.fetch('landcover_sample_1000.tif')
        ts = self.open(imagePath)
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(2006547, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(1319547, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(2658548, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(2149548, 1)
        assert '+proj=aea' in tileMetadata['bounds']['srs']
        region.unlink()

    def testGetTiledRegionWithProjection(self):
        imagePath = datastore.fetch('landcover_sample_1000.tif')
        ts = self.open(imagePath, projection='EPSG:3857')
        # This gets the whole world
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(20037508, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-20037508, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(20037508, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(-20037508, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

        # Ask for a smaller part
        region, _ = ts.getRegion(
            output=dict(maxWidth=1024, maxHeight=1024),
            region=dict(left=-8622811, right=-8192317, bottom=5294998,
                        top=5477835, units='projection'),
            encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(-8192215, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-8622708, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(5477783, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(5294946, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

    def testGetTiledRegion16Bit(self):
        imagePath = datastore.fetch('region_gcp.tiff')
        ts = self.open(imagePath)
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(-10753925, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-10871650, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(3949393, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(3899358, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

    def testGetTiledRegionWithStyle(self):
        imagePath = datastore.fetch('landcover_sample_1000.tif')
        ts = self.open(imagePath, style='{"bands":[]}')
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(2006547, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(1319547, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(2658548, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(2149548, 1)
        assert '+proj=aea' in tileMetadata['bounds']['srs']
        region.unlink()

    def testGetTiledRegionWithProjectionAndStyle(self):
        imagePath = datastore.fetch('landcover_sample_1000.tif')
        ts = self.open(imagePath, projection='EPSG:3857', style='{"bands":[]}')
        # This gets the whole world
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(20037508, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-20037508, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(20037508, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(-20037508, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

        # Ask for a smaller part
        region, _ = ts.getRegion(
            output=dict(maxWidth=1024, maxHeight=1024),
            region=dict(left=-8622811, right=-8192317, bottom=5294998,
                        top=5477835, units='projection'),
            encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(-8192215, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-8622708, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(5477783, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(5294946, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

    def testGetTiledRegion16BitWithStyle(self):
        imagePath = datastore.fetch('region_gcp.tiff')
        ts = self.open(imagePath, style='{"bands":[]}')
        region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                                 encoding='TILED')
        result = self.open(str(region))
        tileMetadata = result.getMetadata()
        assert tileMetadata['bounds']['xmax'] == pytest.approx(-10753925, 1)
        assert tileMetadata['bounds']['xmin'] == pytest.approx(-10871650, 1)
        assert tileMetadata['bounds']['ymax'] == pytest.approx(3949393, 1)
        assert tileMetadata['bounds']['ymin'] == pytest.approx(3899358, 1)
        assert '+proj=merc' in tileMetadata['bounds']['srs']
        region.unlink()

    def testAlphaProjection(self):
        testDir = os.path.dirname(os.path.realpath(__file__))
        imagePath = os.path.join(testDir, 'test_files', 'rgba_geotiff.tiff')
        source = self.open(
            imagePath, projection='EPSG:3857')
        base = source.getThumbnail(encoding='PNG')[0]
        basenp = source.getThumbnail(format='numpy')[0]
        assert numpy.count_nonzero(basenp[:, :, 3] == 255) > 30000
        source = self.open(
            imagePath, projection='EPSG:3857',
            style={'bands': [
                {'band': 1, 'palette': 'R'},
                {'band': 2, 'palette': 'G'},
                {'band': 3, 'palette': 'B'}]})
        assert source.getThumbnail(encoding='PNG')[0] == base
        assert not (source.getThumbnail(format='numpy')[0] - basenp).any()
        source = self.open(
            imagePath)
        assert numpy.count_nonzero(source.getThumbnail(format='numpy')[0][:, :, 3] == 255) > 30000
