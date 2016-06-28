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
    from girder.utility import config
except ImportError:
    pass

from .memcache import MemCache
from cachetools import LRUCache

try:
    import psutil
except ImportError:
    psutil = None


def pickAvailableCache(sizeEach):
    """
    Given an estimated size of an item, return how many of those items would
    fit in a fixed portion of the available virtual memory.

    :param sizeEach: the expected size of an item that could be cached.
    :return: the number of items that should be cached.  Always at least two.
    """
    # Estimate usage based on (1 / portion) of the total virtual memory.  Each
    # class has its own cache, and many methods have their own class, so make
    # this conservative.
    portion = 16
    if psutil:
        memory = psutil.virtual_memory().total
    else:
        memory = 1024 ** 3
    numItems = max(int(math.floor(memory / portion / sizeEach)), 2)
    return numItems


class CacheFactory():

    def getCache(self):

        if config:
            curConfig = config.getConfig()
            if 'large_image' in curConfig:
                cacheBackEnd = curConfig['large_image']['cache_backend']
                # use memcached
                if cacheBackEnd.lower() == 'memcached':
                    print 'using memcached'
                    # lock needed because pylibmc(memcached client)
                    # is not threadsafe
                    tileCacheLock = threading.Lock()

                    # check if credentials and location exist for girder
                    # otherwise assume location is localhost with no password
                    url = curConfig['large_image']['cache_memcached_url']
                    if url is '':
                        url = 'localhost'

                    memcachedUsername = curConfig['large_image']['cache'
                                                                 '_memcached_'
                                                                 'username']

                    memcachedPassword = curConfig['large_'
                                                  'image']['cache_memcached_'
                                                           'password']
                    if memcachedUsername == '':
                        memcachedUsername = None

                    if memcachedPassword == '':
                        memcachedPassword = None

                    tileCache = MemCache(url, memcachedUsername,
                                         memcachedPassword)

                    return tileCache, tileCacheLock

        tileCache = LRUCache(pickAvailableCache(256**2*4))
        return tileCache, None
