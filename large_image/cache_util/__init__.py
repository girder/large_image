#############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#############################################################################

import atexit
from typing import Any, Callable

from .cache import (CacheProperties, LruCacheMetaclass, getTileCache,
                    isTileCacheSetup, methodcache, strhash)
from .cachefactory import CacheFactory, pickAvailableCache

MemCache: Any
RedisCache: Any
try:
    from .memcache import MemCache
except ImportError:
    MemCache = None
try:
    from .rediscache import RedisCache
except ImportError:
    RedisCache = None

_cacheClearFuncs: list[Callable] = []


@atexit.register
def cachesClearExceptTile(*args, **kwargs) -> None:
    """
    Clear the tilesource caches and the load model cache.  Note that this does
    not clear memcached (which could be done with tileCache._client.flush_all,
    but that can affect programs other than this one).
    """
    for name in LruCacheMetaclass.namedCaches:
        with LruCacheMetaclass.namedCaches[name][1]:
            LruCacheMetaclass.namedCaches[name][0].clear()
    for func in _cacheClearFuncs:
        func()


def cachesClear(*args, **kwargs) -> None:
    """
    Clear the tilesource caches, the load model cache, and the tile cache.
    """
    cachesClearExceptTile()
    if isTileCacheSetup():
        tileCache, tileLock = getTileCache()
        try:
            if tileLock:
                with tileLock:
                    tileCache.clear()
            else:
                tileCache.clear()
        except Exception:
            pass


def cachesInfo(*args, **kwargs) -> dict[str, dict[str, int]]:
    """
    Report on each cache.

    :returns: a dictionary with the cache names as the keys and values that
        include 'maxsize' and 'used', if known.
    """
    info = {}
    for name in LruCacheMetaclass.namedCaches:
        with LruCacheMetaclass.namedCaches[name][1]:
            cache = LruCacheMetaclass.namedCaches[name][0]
            info[name] = {
                'maxsize': cache.maxsize,
                'used': cache.currsize,
            }
    if isTileCacheSetup():
        tileCache, tileLock = getTileCache()
        try:
            if tileLock:
                with tileLock:
                    info['tileCache'] = {
                        'maxsize': tileCache.maxsize,
                        'used': tileCache.currsize,
                        'items': getattr(tileCache, 'curritems' if hasattr(
                            tileCache, 'curritems') else 'currsize', None),
                    }
            else:
                info['tileCache'] = {
                    'maxsize': tileCache.maxsize,
                    'used': tileCache.currsize,
                    'items': getattr(tileCache, 'curritems' if hasattr(
                        tileCache, 'curritems') else 'currsize', None),
                }
        except Exception:
            pass
    return info


__all__ = ('CacheFactory', 'getTileCache', 'isTileCacheSetup', 'MemCache', 'RedisCache',
           'strhash', 'LruCacheMetaclass', 'pickAvailableCache', 'methodcache',
           'CacheProperties')
