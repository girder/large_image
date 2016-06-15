#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################

import math

import six

from cachetools import LRUCache, Cache, hashkey
from cachetools.memcache import MemCache
import threading

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


def defaultCacheKeyFunc(args, kwargs):
    return (args, frozenset(six.viewitems(kwargs)))


class LruCacheMetaclass(type):
    """
    """
    caches = dict()

    def __new__(metacls, name, bases, namespace, **kwargs):  # noqa - N804
        # Get metaclass parameters by finding and removing them from the class
        # namespace (necessary for Python 2), or preferentially as metaclass
        # arguments (only in Python 3).

        maxSize = namespace.pop('cacheMaxSize', None)
        maxSize = kwargs.get('cacheMaxSize', maxSize)
        if maxSize is None:
            raise TypeError('Usage of the LruCacheMetaclass requires a '
                            '"cacheMaxSize" attribute on the class.')

        timeout = namespace.pop('cacheTimeout', None)
        timeout = kwargs.get('cacheTimeout', timeout)

        keyFunc = namespace.pop('cacheKeyFunc', None)
        keyFunc = kwargs.get('cacheKeyFunc', keyFunc)
        # The @staticmethod wrapper stored the original function in __func__,
        # and we need to use that as our keyFunc
        if (hasattr(keyFunc, '__func__') and
                hasattr(keyFunc.__func__, '__call__')):
            keyFunc = keyFunc.__func__
        if not keyFunc:
            keyFunc = defaultCacheKeyFunc

        # TODO: use functools.lru_cache if's available in Python 3?
        cache = LRUCache(Cache(maxSize))

        cls = super(LruCacheMetaclass, metacls).__new__(
            metacls, name, bases, namespace)

        # Don't store the cache in cls.__dict__, because we don't want it to be
        # part of the attribute lookup hierarchy
        # TODO: consider putting it in cls.__dict__, to inspect statistics
        # cls is hashable though, so use it to lookup the cache, in case an
        # identically-named class gets redefined
        LruCacheMetaclass.caches[cls] = cache

        return cls

    def __call__(cls, *args, **kwargs):  # noqa - N805
        cache = LruCacheMetaclass.caches[cls]
        instance = None
        key = hashkey(args[0]["_id"])
        try:
            instance = cache[key]
        except KeyError:

            instance = super(LruCacheMetaclass, cls).__call__(*args, **kwargs)
            cache[key] = instance

        return instance


UseMemCached = True
tile_cache = None
tile_cache_lock = None
if UseMemCached:
    tile_cache = MemCache()
    # lock needed because pylibmc(memcached client) is not threadsafe
    tile_cache_lock = threading.Lock()
else:
    tile_cache = Cache(pickAvailableCache(256 ** 2 * 4))
