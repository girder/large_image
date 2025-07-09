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

import math
import threading
from importlib.metadata import entry_points
from typing import Optional, cast

import cachetools

from .. import config
from ..exceptions import TileCacheError
from .memcache import MemCache
from .rediscache import RedisCache

# DO NOT MANUALLY ADD ANYTHING TO `_availableCaches`
#  use entrypoints and let loadCaches fill in `_availableCaches`
_availableCaches: dict[str, type[cachetools.Cache]] = {}


def loadCaches(
        entryPointName: str = 'large_image.cache',
        sourceDict: dict[str, type[cachetools.Cache]] = _availableCaches) -> None:
    """
    Load all caches from entrypoints and add them to the
    availableCaches dictionary.

    :param entryPointName: the name of the entry points to load.
    :param sourceDict: a dictionary to populate with the loaded caches.
    """
    if len(_availableCaches):
        return
    epoints = entry_points()
    # Python 3.10 uses select and deprecates dictionary interface
    epointList = epoints.select(group=entryPointName) if hasattr(
        epoints, 'select') else epoints.get(entryPointName, [])
    for entryPoint in epointList:
        try:
            cacheClass = entryPoint.load()
            sourceDict[entryPoint.name.lower()] = cacheClass
            config.getLogger('logprint').debug(f'Loaded cache {entryPoint.name}')
        except Exception:
            config.getLogger('logprint').exception(
                f'Failed to load cache {entryPoint.name}',
            )
    # Load memcached last for now
    if MemCache is not None:
        # TODO: put this in an entry point for a new package
        _availableCaches['memcached'] = MemCache
    if RedisCache is not None:
        _availableCaches['redis'] = RedisCache
    # NOTE: `python` cache is viewed as a fallback and isn't listed in `availableCaches`


def pickAvailableCache(
        sizeEach: int, portion: int = 8, maxItems: Optional[int] = None,
        cacheName: Optional[str] = None) -> int:
    """
    Given an estimated size of an item, return how many of those items would
    fit in a fixed portion of the available virtual memory.

    :param sizeEach: the expected size of an item that could be cached.
    :param portion: the inverse fraction of the memory which can be used.
    :param maxItems: if specified, the number of items is never more than this
        value.
    :param cacheName: if specified, the portion can be affected by the
        configuration.
    :return: the number of items that should be cached.  Always at least two,
        unless maxItems is less.
    """
    if cacheName:
        portion = max(portion, int(config.getConfig(
            f'cache_{cacheName}_memory_portion', portion)))
        configMaxItems = int(config.getConfig(f'cache_{cacheName}_maximum', 0))
        if configMaxItems > 0:
            maxItems = configMaxItems
    # Estimate usage based on (1 / portion) of the total virtual memory.
    memory = config.total_memory()
    numItems = max(int(math.floor(memory / portion / sizeEach)), 2)
    if maxItems:
        numItems = min(numItems, maxItems)
    return numItems


def getFirstAvailableCache() -> tuple[Optional[cachetools.Cache], Optional[threading.Lock]]:
    cacheBackend = config.getConfig('cache_backend', None)
    if cacheBackend is not None:
        msg = 'cache_backend already set'
        raise ValueError(msg)
    loadCaches()
    cache, cacheLock = None, None
    for cacheBackend in _availableCaches:
        try:
            cache, cacheLock = cast(
                tuple[cachetools.Cache, Optional[threading.Lock]],
                _availableCaches[cacheBackend].getCache())  # type: ignore
            break
        except TileCacheError:
            continue
    if cache is not None:
        config.getLogger('logprint').debug(
            f'Automatically setting `{cacheBackend}` as cache_backend from availableCaches',
        )
        config.setConfig('cache_backend', cacheBackend)
    return cache, cacheLock


class CacheFactory:
    logged = False

    def getCacheSize(self, numItems: Optional[int], cacheName: Optional[str] = None) -> int:
        if numItems is None:
            defaultPortion = 32
            try:
                portion = int(config.getConfig('cache_python_memory_portion', 0))
                if cacheName:
                    portion = max(portion, int(config.getConfig(
                        f'cache_{cacheName}_memory_portion', portion)))
                portion = max(portion or defaultPortion, 3)
            except ValueError:
                portion = defaultPortion
            numItems = pickAvailableCache(256**2 * 4 * 2, portion)
        if cacheName:
            try:
                maxItems = int(config.getConfig(f'cache_{cacheName}_maximum', 0))
                if maxItems > 0:
                    numItems = min(numItems, max(maxItems, 3))
            except ValueError:
                pass
        return numItems

    def getCache(
            self, numItems: Optional[int] = None,
            cacheName: Optional[str] = None,
            inProcess: bool = False) -> tuple[cachetools.Cache, Optional[threading.Lock]]:
        loadCaches()

        # Default to `python` cache for inProcess
        cacheBackend = config.getConfig('cache_backend', 'python' if inProcess else None)

        if isinstance(cacheBackend, str):
            cacheBackend = cacheBackend.lower()

        cache = None
        if not inProcess and cacheBackend in _availableCaches:
            cache, cacheLock = _availableCaches[cacheBackend].getCache()  # type: ignore
        elif not inProcess and cacheBackend is None:
            cache, cacheLock = getFirstAvailableCache()

        if cache is None:  # fallback backend or inProcess
            cacheBackend = 'python'
            cache = cachetools.LRUCache(self.getCacheSize(numItems, cacheName=cacheName))
            cacheLock = threading.Lock()

        if not inProcess and not CacheFactory.logged:
            config.getLogger('logprint').debug(f'Using {cacheBackend} for large_image caching')
            CacheFactory.logged = True

        return cache, cacheLock
