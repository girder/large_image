import glob
import io
import json
import os

import large_image_source_gdal
import numpy
import PIL.Image
import PIL.ImageChops
import pytest

from large_image import constants
from large_image.exceptions import TileSourceError, TileSourceInefficientError
from large_image.tilesource.utilities import ImageBytes

from . import utilities
from .datastore import datastore


def testProj4Proj():
    # Test obtaining pyproj.Proj projection values
    proj4Proj = large_image_source_gdal.GDALFileTileSource._proj4Proj

    proj = proj4Proj(b'epsg:4326')
    assert proj4Proj('epsg:4326').srs == proj.srs
    assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
    assert proj4Proj(4326) is None
