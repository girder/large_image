import sys
from unittest import TestCase

try:
    import large_image_source_rasterio
except ImportError:
    pass
import pytest

from .source_geo_base import _GDALBaseSourceTest

if sys.version_info < (3, 8):
    pytest.skip(reason='requires python3.8 or higher', allow_module_level=True)
# pytestmark = [
#     pytest.mark.skipif(sys.version_info < (3, 8), reason='requires python3.8 or higher'),
# ]


class RasterioSourceTests(_GDALBaseSourceTest, TestCase):

    basemodule = large_image_source_rasterio
    baseclass = large_image_source_rasterio.RasterioFileTileSource
