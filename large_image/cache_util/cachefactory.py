# -*- coding: utf-8 -*-

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


import threading
import math
try:
    import psutil
except ImportError:
    psutil = None
from cachetools import LRUCache

from .. import config
try:
    from .memcache import MemCache
except ImportError:
    MemCache = None


def pickAvailableCache(sizeEach, portion=8, maxItems=None):
    """
    Given an estimated size of an item, return how many of those items would
    fit in a fixed portion of the available virtual memory.

    :param sizeEach: the expected size of an item that could be cached.
    :param portion: the inverse fraction of the memory which can be used.
    :param maxItems: if specified, the number of items is never more than this
        value.
    :return: the number of items that should be cached.  Always at least two,
        unless maxItems is less.
    """
    # Estimate usage based on (1 / portion) of the total virtual memory.
    if psutil:
        memory = psutil.virtual_memory().total
    else:
        memory = 1024 ** 3
    numItems = max(int(math.floor(memory / portion / sizeEach)), 2)
    if maxItems:
        numItems = min(numItems, maxItems)
    return numItems


class CacheFactory(object):
    logged = False

    def getCacheSize(self, numItems):
        if numItems is None:
            defaultPortion = 32
            try:
                portion = int(config.getConfig('cache_python_memory_portion', defaultPortion))
                if portion < 3:
                    portion = 3
            except ValueError:
                portion = defaultPortion
            numItems = pickAvailableCache(256**2 * 4 * 2, portion)
        return numItems

    def getCache(self, numItems=None):
        # memcached is the fallback default, if available.
        cacheBackend = config.getConfig('cache_backend', 'python')
        if cacheBackend:
            cacheBackend = str(cacheBackend).lower()
        cache = None
        if cacheBackend == 'memcached' and MemCache and numItems is None:
            # lock needed because pylibmc(memcached client) is not threadsafe
            cacheLock = threading.Lock()

            # check if credentials and location exist, otherwise assume
            # location is 127.0.0.1 (localhost) with no password
            url = config.getConfig('cache_memcached_url')
            if not url:
                url = '127.0.0.1'
            memcachedUsername = config.getConfig('cache_memcached_username')
            if not memcachedUsername:
                memcachedUsername = None
            memcachedPassword = config.getConfig('cache_memcached_password')
            if not memcachedPassword:
                memcachedPassword = None
            try:
                cache = MemCache(url, memcachedUsername, memcachedPassword,
                                 mustBeAvailable=True)
            except Exception:
                config.getConfig('logger').info('Cannot use memcached for caching.')
                cache = None
        if cache is None:  # fallback backend
            cacheBackend = 'python'
            cache = LRUCache(self.getCacheSize(numItems))
            cacheLock = threading.Lock()
        if numItems is None and not CacheFactory.logged:
            config.getConfig('logprint').info('Using %s for large_image caching' % cacheBackend)
            CacheFactory.logged = True
        return cache, cacheLock
