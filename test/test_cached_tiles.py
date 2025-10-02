import gc
import os
import time

import large_image_source_test
import pytest
from large_image_source_tiff.tiff_reader import TiledTiffDirectory

import large_image
import large_image.cache_util.cache
from large_image import config
from large_image.cache_util import cachesClear

from . import utilities
from .datastore import datastore


@pytest.fixture
def monitorTileCounts():
    large_image_source_test._counters['tiles'] = 0

    originalWrapKey = large_image_source_test.TestTileSource.wrapKey
    keyPrefix = str(time.time())

    def wrapKey(*args, **kwargs):
        # Ensure that this test has unique keys
        return keyPrefix + originalWrapKey(*args, **kwargs)

    large_image_source_test.TestTileSource.wrapKey = wrapKey
    yield large_image_source_test.TestTileSource
    large_image_source_test.TestTileSource.wrapKey = originalWrapKey


class LargeImageCachedTilesTest:

    @pytest.mark.singular
    def testTilesFromTest(self, monitorTileCounts):
        # Create a test tile with the default options
        params = {'encoding': 'JPEG'}
        source = monitorTileCounts(None, **dict(
            params,
            tileWidth=256, tileHeight=256,
            sizeX=256 * 2 ** 9, sizeY=256 * 2 ** 9, levels=10,
        ))
        meta = source.getMetadata()
        utilities.checkTilesZXY(source, meta, params)
        # We should have generated tiles
        assert large_image_source_test._counters['tiles'] > 0
        counter1 = large_image_source_test._counters['tiles']
        # Running a second time should take entirely from cache
        utilities.checkTilesZXY(source, meta, params)
        assert large_image_source_test._counters['tiles'] == counter1

        # Test most of our parameters in a single special case
        params = {
            'minLevel': 2,
            'maxLevel': 5,
            'tileWidth': 160,
            'tileHeight': 120,
            'sizeX': 5000,
            'sizeY': 3000,
            'encoding': 'JPEG',
        }
        source = monitorTileCounts(None, **dict(
            params,
            tileWidth=160, tileHeight=120,
            sizeX=5000, sizeY=3000, levels=6,
            minLevel=2,
        ))
        meta = source.getMetadata()
        meta['minLevel'] = 2
        utilities.checkTilesZXY(source, meta, params)
        # We should have generated tiles
        assert large_image_source_test._counters['tiles'] > counter1
        counter2 = large_image_source_test._counters['tiles']
        # Running a second time should take entirely from cache
        utilities.checkTilesZXY(source, meta, params)
        assert large_image_source_test._counters['tiles'] == counter2
        # Test the fractal tiles with PNG
        params = {'fractal': 'true'}
        source = monitorTileCounts(None, **dict(
            params,
            tileWidth=256, tileHeight=256,
            sizeX=256 * 2 ** 9, sizeY=256 * 2 ** 9, levels=10,
        ))
        meta = source.getMetadata()
        utilities.checkTilesZXY(source, meta, params, utilities.PNGHeader)
        # We should have generated tiles
        assert large_image_source_test._counters['tiles'] > counter2
        counter3 = large_image_source_test._counters['tiles']
        # Running a second time should take entirely from cache
        utilities.checkTilesZXY(source, meta, params, utilities.PNGHeader)
        assert large_image_source_test._counters['tiles'] == counter3

    @pytest.mark.singular
    def testLargeRegion(self):
        imagePath = datastore.fetch(
            'sample_jp2k_33003_TCGA-CV-7242-11A-01-TS1.1838afb1-9eee-'
            '4a70-9ae3-50e3ab45e242.svs')
        source = large_image.open(imagePath)
        tileMetadata = source.getMetadata()
        params = {
            'region': {
                'width': min(10000, tileMetadata['sizeX']),
                'height': min(10000, tileMetadata['sizeY']),
            },
            'output': {
                'maxWidth': 480,
                'maxHeight': 480,
            },
            'encoding': 'PNG',
        }
        image, mimeType = source.getRegion(**params)
        assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader

    @pytest.mark.singular
    def testTiffClosed(self):
        # test the Tiff files are properly closed.
        orig_del = TiledTiffDirectory.__del__
        orig_init = TiledTiffDirectory.__init__
        self.delCount = 0
        self.initCount = 0

        def countDelete(*args, **kwargs):
            self.delCount += 1
            orig_del(*args, **kwargs)

        def countInit(*args, **kwargs):
            self.initCount += 1
            orig_init(*args, **kwargs)

        imagePath = datastore.fetch('sample_image.ptif')
        cachesClear()
        gc.collect(2)
        TiledTiffDirectory.__del__ = countDelete
        TiledTiffDirectory.__init__ = countInit
        self.initCount = 0
        self.delCount = 0
        source = large_image.open(imagePath)
        assert source is not None
        assert self.initCount == 11
        assert self.delCount < 11
        # Create another source; we shouldn't init it again, as it should be
        # cached.
        source = large_image.open(imagePath)
        assert source is not None
        assert self.initCount == 11
        assert self.delCount < 11
        source = None
        # Clear the cache to free references and force garbage collection
        cachesClear()
        gc.collect(2)
        cachesClear()
        assert self.delCount == 11


class TestMemcachedCache(LargeImageCachedTilesTest):
    @classmethod
    def setup_class(cls):
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'memcached')


@pytest.mark.skipif(os.getenv('REDIS_TEST_URL') is None, reason='REDIS_TEST_URL is not set')
class TestRedisCache(LargeImageCachedTilesTest):
    @classmethod
    def setup_class(cls):
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'redis')


class TestPythonCache(LargeImageCachedTilesTest):
    @classmethod
    def setup_class(cls):
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'python')
