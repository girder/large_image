import os
from unittest import TestCase

import large_image_source_gdal
import numpy

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
