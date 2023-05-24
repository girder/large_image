import sys
from unittest import TestCase

import large_image_source_rasterio
import pytest

from .source_geo_base import _GDALBaseSourceTest

if sys.version_info < (3, 8):
    pytest.skip(reason='requires python3.8 or higher', allow_module_level=True)


class GDALSourceTests(_GDALBaseSourceTest, TestCase):

    def open(self, *args, **kwargs):
        return large_image_source_rasterio.open(*args, **kwargs)
