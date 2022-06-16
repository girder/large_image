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
from collections import OrderedDict

import cachetools

try:
    import psutil
except ImportError:
    psutil = None

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points

from .. import config

try:
    from .memcache import MemCache
except ImportError:
    MemCache = None

availableCaches = OrderedDict()


def loadCaches(entryPointName='large_image.cache', sourceDict=availableCaches):
    """
    Load all caches from entrypoints and add them to the
    availableCaches dictionary.

    :param entryPointName: the name of the entry points to load.
    :param sourceDict: a dictionary to populate with the loaded caches.
    """
    epoints = entry_points()
    if entryPointName in epoints:
        for entryPoint in epoints[entryPointName]:
            try:
                cacheClass = entryPoint.load()
                sourceDict[entryPoint.name.lower()] = cacheClass
                config.getConfig('logprint').debug('Loaded cache %s' % entryPoint.name)
            except Exception:
                config.getConfig('logprint').exception(
                    'Failed to load cache %s' % entryPoint.name)
    # Load memcached last for now
    if MemCache is not None:
        # TODO: put this in an entry point for a new package
        availableCaches['memcached'] = MemCache
    # NOTE: `python` cache is viewed as a fallback and isn't listed in `availableCaches`


def pickAvailableCache(sizeEach, portion=8, maxItems=None, cacheName=None):
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
    if psutil:
        memory = psutil.virtual_memory().total
    else:
        memory = 1024 ** 3
    numItems = max(int(math.floor(memory / portion / sizeEach)), 2)
    if maxItems:
        numItems = min(numItems, maxItems)
    return numItems


class CacheFactory:
    logged = False

    def getCacheSize(self, numItems, cacheName=None):
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

    def getCache(self, numItems=None, cacheName=None):
        loadCaches()
        # memcached is the fallback default, if available.
        cacheBackend = config.getConfig('cache_backend', None)

        if cacheBackend is None and len(availableCaches):
            cacheBackend = next(iter(availableCaches))
            config.getConfig('logprint').info('Automatically setting `%s` as cache_backend from availableCaches' % cacheBackend)
            config.setConfig('cache_backend', cacheBackend)

        if cacheBackend:
            cacheBackend = str(cacheBackend).lower()

        cache = None
        # TODO: why have this numItems check?
        if numItems is None and cacheBackend in availableCaches:
            cache, cacheLock = availableCaches[cacheBackend].getCache()

        if cache is None:  # fallback backend
            cacheBackend = 'python'
            cache = cachetools.LRUCache(self.getCacheSize(numItems, cacheName=cacheName))
            cacheLock = threading.Lock()
        if numItems is None and not CacheFactory.logged:
            config.getConfig('logprint').info('Using %s for large_image caching' % cacheBackend)
            CacheFactory.logged = True
        return cache, cacheLock
