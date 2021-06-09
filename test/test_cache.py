import cachetools
import pytest
import threading

import large_image.cache_util.cache
from large_image import config
from large_image.cache_util import cached, strhash, Cache, MemCache, \
    methodcache, LruCacheMetaclass, cachesInfo, cachesClear, getTileCache


class Fib:
    def num(self, k):
        if k > 2:
            return self.num(k - 1) + self.num(k - 2)
        else:
            return 1


def cache_test(specific_cache, maxNum=100):
    temp = Fib()
    temp.num = cached(cache=specific_cache, key=strhash)(temp.num)
    temp.num(maxNum)
    if maxNum >= 3:
        assert temp.num(3) == 2
    if maxNum >= 100:
        assert temp.num(100) == 354224848179261915075


def testLRUCacheTools():
    cache_test(Cache(1000))


def testCacheMemcached():
    cache_test(MemCache())


def testCheckCacheMemcached():
    cache = MemCache()

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


def testGetTileCachePython():
    large_image.cache_util.cache._tileCache = None
    large_image.cache_util.cache._tileLock = None
    config.setConfig('cache_backend', 'python')
    tileCache, tileLock = getTileCache()
    assert isinstance(tileCache, cachetools.LRUCache)


def testGetTileCacheMemcached():
    large_image.cache_util.cache._tileCache = None
    large_image.cache_util.cache._tileLock = None
    config.setConfig('cache_backend', 'memcached')
    tileCache, tileLock = getTileCache()
    assert isinstance(tileCache, MemCache)


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
            pass

    def testCachesInfo(self):
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

    def testCachesClear(self):
        large_image.cache_util.cache._tileCache = None
        large_image.cache_util.cache._tileLock = None
        config.setConfig('cache_backend', 'python')
        self.ExampleWithMetaclass('test')
        getTileCache()
        assert cachesInfo()['test']['used'] == 1
        cachesClear()
        assert cachesInfo()['test']['used'] == 0
