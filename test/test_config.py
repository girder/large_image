from test.datastore import datastore

import pytest

import large_image
from large_image.config import getConfig, setConfig


@pytest.fixture
def default_projection():
    setConfig('default_projection', 'EPSG:3857')
    yield getConfig('default_projection')
    setConfig('default_projection', None)


@pytest.mark.singular
def testConfigFunctions():
    assert isinstance(getConfig(), dict)
    setConfig('cache_backend', 'python')
    assert getConfig('cache_backend') == 'python'
    setConfig('cache_backend', 'memcached')
    assert getConfig('cache_backend') == 'memcached'
    setConfig('cache_backend', 'redis')
    assert getConfig('cache_backend') == 'redis'
    setConfig('cache_backend', None)
    assert getConfig('cache_backend') is None
    assert getConfig('unknown', 'python') == 'python'
    setConfig('default_encoding', 'PNG')
    assert getConfig('default_encoding') == 'PNG'
    setConfig('default_projection', 'EPSG:3857')
    assert getConfig('default_projection') == 'EPSG:3857'

    # set defaults back
    setConfig('default_encoding', 'JPEG')
    setConfig('default_projection', None)


@pytest.mark.singular
def testChangeDefaultEncodingCacheMiss():
    imagePath = datastore.fetch('sample_Easy1.png')
    setConfig('default_encoding', 'PNG')
    source_1 = large_image.open(imagePath)
    assert source_1.encoding == 'PNG'

    setConfig('default_encoding', 'JPEG')
    source_2 = large_image.open(imagePath)
    assert source_2.encoding == 'JPEG'


def testGDALDefaultProjection(default_projection):
    import large_image_source_gdal

    path = 'test/test_files/rgba_geotiff.tiff'
    src = large_image_source_gdal.open(path)
    assert src.projection == default_projection.lower().encode()


def testGDALDefaultNoProjection():
    import large_image_source_gdal

    path = 'test/test_files/test_orient0.tif'
    src = large_image_source_gdal.open(path)
    assert src.projection is None


def testRasterioDefaultProjection(default_projection):
    import large_image_source_rasterio
    import rasterio

    path = 'test/test_files/rgba_geotiff.tiff'
    src = large_image_source_rasterio.open(path)
    assert src.projection == rasterio.CRS.from_string(default_projection)


def testRasterioDefaultNoProjection():
    import large_image_source_rasterio

    path = 'test/test_files/test_orient1.tif'
    src = large_image_source_rasterio.open(path)
    assert src.projection is None
