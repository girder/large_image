import sys
from unittest import TestCase

import pytest

try:
    import large_image_source_rasterio
except ImportError:
    pass

from .source_geo_base import _GDALBaseSourceTest


@pytest.mark.skipif(sys.version_info > (3, 14), reason='cannot yet be tested in 3.14')
class RasterioSourceTests(_GDALBaseSourceTest, TestCase):

    basemodule = large_image_source_rasterio
    baseclass = large_image_source_rasterio.RasterioFileTileSource
