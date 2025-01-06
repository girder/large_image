import concurrent.futures
import os
import threading
import time

import cachetools
import pytest

import large_image.cache_util.cache
from large_image import config
from large_image.cache_util import (LruCacheMetaclass, MemCache, RedisCache,
                                    cachesClear, cachesInfo, getTileCache,
                                    methodcache, strhash)


class Fib:
    def num(self, k):
        if k > 2:
            return self.num(k - 1) + self.num(k - 2)
        return 1


def cache_test(specific_cache, maxNum=100):
    temp = Fib()
    temp.num = cachetools.cached(cache=specific_cache, key=strhash)(temp.num)
    temp.num(maxNum)
    if maxNum >= 3:
        assert temp.num(3) == 2
    if maxNum >= 100:
        assert temp.num(100) == 354224848179261915075


def testLRUCacheTools():
    cache_test(cachetools.Cache(1000))


@pytest.mark.singular
def testCacheMemcached():
    cache_test(MemCache())


@pytest.mark.singular
def testCheckCacheMemcached():
    cache = MemCache()

    cache_test(cache)

    val = cache['(2,)']
    assert val == 1
    val = cache['(100,)']
    assert val == 354224848179261915075


@pytest.mark.singular
@pytest.mark.skipif(os.getenv('REDIS_TEST_URL') is None, reason='REDIS_TEST_URL is not set')
def testCacheRedis():
    config.setConfig('cache_redis_url', os.getenv('REDIS_TEST_URL'))
    cache_test(RedisCache())


@pytest.mark.singular
@pytest.mark.skipif(os.getenv('REDIS_TEST_URL') is None, reason='REDIS_TEST_URL is not set')
def testCheckCacheRedis():
    config.setConfig('cache_redis_url', os.getenv('REDIS_TEST_URL'))
    cache = RedisCache()

    cache_test(cache)

    val = cache['(2,)']
    assert val == 1
    val = cache['(100,)']
    assert val == 354224848179261915075


def testBadMemcachedUrl():
    # go though and check if all 100 fib numbers are in cache
    # it is stored in cache as ('fib', #)
    cache = MemCache(url=['192.0.2.254', '192.0.2.253'])

    cache_test(cache, 3)
    with pytest.raises(KeyError):
        cache['(2,)']


@pytest.mark.singular
def testGetTileCachePython():
    large_image.cache_util.cache._tileCache = None
    large_image.cache_util.cache._tileLock = None
    config.setConfig('cache_backend', 'python')
    tileCache, tileLock = getTileCache()
    assert isinstance(tileCache, cachetools.LRUCache)
    assert 'tileCache' in cachesInfo()


@pytest.mark.singular
def testGetTileCacheMemcached():
    large_image.cache_util.cache._tileCache = None
    large_image.cache_util.cache._tileLock = None
    config.setConfig('cache_backend', 'memcached')
    tileCache, tileLock = getTileCache()
    assert isinstance(tileCache, MemCache)
    assert 'tileCache' in cachesInfo()


@pytest.mark.singular
@pytest.mark.skipif(os.getenv('REDIS_TEST_URL') is None, reason='REDIS_TEST_URL is not set')
def testGetTileCacheRedis():
    large_image.cache_util.cache._tileCache = None
    large_image.cache_util.cache._tileLock = None
    config.setConfig('cache_backend', 'redis')
    config.setConfig('cache_redis_url', os.getenv('REDIS_TEST_URL'))
    tileCache, tileLock = getTileCache()
    assert isinstance(tileCache, RedisCache)
    assert 'tileCache' in cachesInfo()


class TestClass:
    def testLRUThreadSafety(self):
        # The cachetools LRU cache is not thread safe, and if two threads ask
        # to evict an old value concurrently, the cache will raise a KeyError
        # and then be in a broken state.  Test that we fall-back garcefully in
        # this case.  Better, is to use a threading lock when setting the
        # cache, which should never have the problem.

        self.cache = cachetools.LRUCache(10)
        self.cache_lock = None
        loopSize = 10000
        sumDelta = 2

        def keyFunc(x):
            return x

        @methodcache(keyFunc)
        def add(self, x):
            return x + sumDelta

        def loop():
            sum = 0
            for x in range(loopSize):
                sum += add(self, x)
            sums.append(sum)

        # Without a thread lock
        sums = []
        threadList = [threading.Thread(target=loop) for t in range(5)]
        for t in threadList:
            t.start()
        for t in threadList:
            t.join()
        for sum in sums:
            assert sum == loopSize * (loopSize - 1) / 2 + loopSize * sumDelta

        # With a thread lock
        self.cache = cachetools.LRUCache(10)
        self.cache_lock = threading.Lock()

        sums = []
        threadList = [threading.Thread(target=loop) for t in range(5)]
        for t in threadList:
            t.start()
        for t in threadList:
            t.join()
        for sum in sums:
            assert sum == loopSize * (loopSize - 1) / 2 + loopSize * sumDelta

    class ExampleWithMetaclass(metaclass=LruCacheMetaclass):
        cacheName = 'test'
        cacheMaxSize = 4

        def __init__(self, arg):
            if isinstance(arg, (int, float)):
                time.sleep(arg)

    @pytest.mark.singular
    def testCachesInfo(self):
        cachesClear()
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        assert cachesInfo()['test']['used'] == 0
        assert 'tileCache' not in cachesInfo()
        self.ExampleWithMetaclass('test')
        assert cachesInfo()['test']['used'] == 1
        config.setConfig('cache_backend', 'python')
        getTileCache()
        assert 'tileCache' in cachesInfo()
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'memcached')
        getTileCache()
        # memcached shows an items record as well
        assert 'items' in cachesInfo()['tileCache']

    @pytest.mark.singular
    def testCachesKeyLock(self):
        cachesClear()
        assert cachesInfo()['test']['used'] == 0
        starttime = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(self.ExampleWithMetaclass, [3, 3, 2])
        endtime = time.time()
        # This really should be close to 3
        assert endtime - starttime < 6
        assert cachesInfo()['test']['used'] == 2

    @pytest.mark.singular
    def testCachesClear(self):
        cachesClear()
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'python')
        self.ExampleWithMetaclass('test')
        getTileCache()
        assert cachesInfo()['test']['used'] == 1
        cachesClear()
        assert cachesInfo()['test']['used'] == 0
