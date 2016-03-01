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

import functools

import six
import repoze.lru
# Import _MARKER into the global namespace for slightly faster lookup
from repoze.lru import _MARKER


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
        cacheType = \
            repoze.lru.LRUCache \
            if timeout is None else \
            functools.partial(repoze.lru.ExpiringLRUCache,
                              default_timeout=timeout)
        cache = cacheType(maxSize)
        cache.keyFunc = keyFunc

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

        key = cache.keyFunc(args, kwargs)

        instance = cache.get(key, _MARKER)
        if instance is _MARKER:
            instance = super(LruCacheMetaclass, cls).__call__(*args, **kwargs)
            cache.put(key, instance)

        return instance


class instanceLruCache(object):  # noqa - N801
    """
    """
    def __init__(self, maxSize, timeout=None, keyFunc=None):
        self.maxSize = maxSize
        self.cacheType = \
            repoze.lru.LRUCache \
            if timeout is None else \
            functools.partial(repoze.lru.ExpiringLRUCache,
                              default_timeout=timeout)
        self.keyFunc = keyFunc if keyFunc else defaultCacheKeyFunc

    def __call__(self, func):
        def wrapper(instance, *args, **kwargs):
            # instance methods are hashable, but we shouldn't use the instance
            # method as the cache identifier / name because the Python language
            # states:
            #   Note that the transformation from function object to instance
            #   method object happens each time the attribute is retrieved from
            #   the instance. In some cases, a fruitful optimization is to
            #   assign the attribute to a local variable and call that local
            #   variable.
            # so we are not be guaranteed to get the same instance method object
            # back each time, and the instance method __hash__ function might
            # use object identity as an input
            cacheName = '__cache_%s' % func.__name__

            cache = instance.__dict__.setdefault(
                cacheName, self.cacheType(self.maxSize))

            key = self.keyFunc(args, kwargs)

            value = cache.get(key, _MARKER)
            if value is _MARKER:
                value = func(instance, *args, **kwargs)
                cache.put(key, value)

            return value

        return functools.update_wrapper(wrapper, func)
