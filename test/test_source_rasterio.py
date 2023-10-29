from unittest import TestCase

try:
    import large_image_source_rasterio
except ImportError:
    pass

from .source_geo_base import _GDALBaseSourceTest


class RasterioSourceTests(_GDALBaseSourceTest, TestCase):

    basemodule = large_image_source_rasterio
    baseclass = large_image_source_rasterio.RasterioFileTileSource
