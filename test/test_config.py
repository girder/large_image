from test.datastore import datastore

import large_image
from large_image.config import getConfig, setConfig



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


def testChangeDefaultEncodingCacheMiss():
    imagePath = datastore.fetch('sample_Easy1.png')
    setConfig('default_encoding', 'JPEG')
    source_1 = large_image.open(imagePath)
    assert source_1.encoding == 'JPEG'

    setConfig('default_encoding', 'PNG')
    source_2 = large_image.open(imagePath)
    assert source_2.encoding == 'PNG'


def testGDALDefaultProjection():
    import large_image_source_gdal

    path = 'test/test_files/rgba_geotiff.tiff'
    src = large_image_source_gdal.open(path)
    proj = getConfig('default_projection')
    assert src.projection == proj.lower().encode()


def testGDALDefaultNoProjection():
    import large_image_source_gdal

    path = 'test/test_files/test_orient0.tif'
    src = large_image_source_gdal.open(path)
    assert src.projection is None


def testRasterioDefaultProjection():
    import large_image_source_rasterio
    import rasterio

    path = 'test/test_files/rgba_geotiff.tiff'
    src = large_image_source_rasterio.open(path)
    proj = getConfig('default_projection')
    assert src.projection == rasterio.CRS.from_string(proj)


def testRasterioDefaultNoProjection():
    import large_image_source_rasterio

    path = 'test/test_files/test_orient0.tif'
    src = large_image_source_rasterio.open(path)
    assert src.projection is None
