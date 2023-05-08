from unittest import TestCase

import large_image_source_gdal

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
