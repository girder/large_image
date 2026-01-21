import contextlib
from unittest import TestCase

with contextlib.suppress(ImportError):
    import large_image_source_rasterio

from .source_geo_base import _GDALBaseSourceTest


class RasterioSourceTests(_GDALBaseSourceTest, TestCase):

    basemodule = large_image_source_rasterio
    baseclass = large_image_source_rasterio.RasterioFileTileSource
