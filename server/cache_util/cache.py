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

import six
from cachetools import LRUCache, Cache, hashkey

from .cachefactory import CacheFactory


def strhash(*args, **kwargs):
    return str(hashkey(*args, **kwargs))


def methodcache(key=None, lock=None):
    """
    Decorator to wrap a function with a memoizing callable that saves results
    in self.cache.  This is largely taken from cachetools, but uses a cache
    from self.cache rather than a passed value.

    :param key: if a function, use that for the key, otherwise use self.wrapKey.
    :param lock: if True, use self.cache_lock for a lock, otherwise don't use a
        lock.
    """
    def decorator(func):
        if lock is None:
            @six.wraps(func)
            def wrapper(self, *args, **kwargs):
                k = key(*args, **kwargs) if key else self.wrapKey(*args, **kwargs)
                try:
                    return self.cache[k]
                except KeyError:
                    pass  # key not found
                v = func(self, *args, **kwargs)
                try:
                    self.cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
        else:
            @six.wraps(func)
            def wrapper(self, *args, **kwargs):
                k = key(*args, **kwargs) if key else self.wrapKey(*args, **kwargs)
                try:
                    with self.cache_lock:
                        return self.cache[k]
                except KeyError:
                    pass  # key not found
                v = func(self, *args, **kwargs)
                try:
                    with self.cache_lock:
                        self.cache[k] = v
                except ValueError:
                    pass  # value too large
                return v
        return wrapper
    return decorator


class LruCacheMetaclass(type):
    """
    """
    caches = {}

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

        if hasattr(cls, 'getLRUHash'):
            key = cls.getLRUHash(*args, **kwargs)
        else:
            key = strhash(args[0], kwargs)
        try:
            instance = cache[key]
        except KeyError:

            instance = super(LruCacheMetaclass, cls).__call__(*args, **kwargs)
            cache[key] = instance

        return instance

# Decide whether to use Memcached or cachetools

tileCache, tileLock = CacheFactory().getCache()
