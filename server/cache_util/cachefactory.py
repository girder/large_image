#!/usr/bin/env python
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
# attempt to import girder config
try:
    from girder import logprint
    from girder.utility import config
except ImportError:
    import logging as logprint
    config = None

try:
    from .memcache import MemCache
except ImportError:
    MemCache = None
from cachetools import LRUCache

try:
    import psutil
except ImportError:
    psutil = None


def pickAvailableCache(sizeEach, portion=8):
    """
    Given an estimated size of an item, return how many of those items would
    fit in a fixed portion of the available virtual memory.

    :param sizeEach: the expected size of an item that could be cached.
    :param portion: the inverse fraction of the memory which can be used.
    :return: the number of items that should be cached.  Always at least two.
    """
    # Estimate usage based on (1 / portion) of the total virtual memory.
    if psutil:
        memory = psutil.virtual_memory().total
    else:
        memory = 1024 ** 3
    numItems = max(int(math.floor(memory / portion / sizeEach)), 2)
    return numItems


class CacheFactory():
    def getCache(self):
        defaultConfig = {}
        if config:
            curConfig = config.getConfig().get('large_image', defaultConfig)
        else:
            curConfig = defaultConfig
        cacheBackend = curConfig.get('cache_backend')
        if cacheBackend:
            cacheBackend = str(cacheBackend).lower()
        if cacheBackend == 'memcached' and MemCache:
            # lock needed because pylibmc(memcached client) is not threadsafe
            tileCacheLock = threading.Lock()

            # check if credentials and location exist for girder otherwise
            # assume location is 127.0.0.1 (localhost) with no password
            url = curConfig.get('cache_memcached_url')
            if not url:
                url = '127.0.0.1'
            memcachedUsername = curConfig.get('cache_memcached_username')
            if not memcachedUsername:
                memcachedUsername = None
            memcachedPassword = curConfig.get('cache_memcached_password')
            if not memcachedPassword:
                memcachedPassword = None

            tileCache = MemCache(url, memcachedUsername, memcachedPassword)
        else:  # fallback backend
            cacheBackend = 'python'
            try:
                portion = int(curConfig.get('cache_python_memory_portion', 8))
                if portion < 3:
                    portion = 3
            except ValueError:
                portion = 16
            tileCache = LRUCache(pickAvailableCache(256**2 * 4, portion))
            tileCacheLock = None
        logprint.info('Using %s for large_image caching' % cacheBackend)
        return tileCache, tileCacheLock
