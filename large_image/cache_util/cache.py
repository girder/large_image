import functools
import pickle
import threading
import uuid
from typing import Any, Callable, Optional, TypeVar

import cachetools
from typing_extensions import ParamSpec

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

import contextlib

from .. import config
from .cachefactory import CacheFactory, pickAvailableCache

P = ParamSpec('P')
T = TypeVar('T')

_tileCache: Optional[cachetools.Cache] = None
_tileLock: Optional[threading.Lock] = None

_cacheLockKeyToken = '_cacheLock_key'

# If we have a resource module, ask to use as many file handles as the hard
# limit allows, then calculate how may tile sources we can have open based on
# the actual limit.
MaximumTileSources = 10
if HAS_RESOURCE:
    try:
        SoftNoFile, HardNoFile = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (HardNoFile, HardNoFile))
        SoftNoFile, HardNoFile = resource.getrlimit(resource.RLIMIT_NOFILE)
        # Reserve some file handles for general use, and expect that tile
        # sources could use many handles each.  This is conservative, since
        # running out of file handles breaks the program in general.
        MaximumTileSources = max(3, (SoftNoFile - 10) // 20)
    except Exception:
        pass


CacheProperties = {
    'tilesource': {
        # Cache size is based on what the class needs, which does not include
        # individual tiles
        'itemExpectedSize': 24 * 1024 ** 2,
        'maxItems': MaximumTileSources,
        # The cache timeout is not currently being used, but it is set here in
        # case we ever choose to implement it.
        'cacheTimeout': 300,
    },
}


def strhash(*args, **kwargs) -> str:
    """
    Generate a string hash value for an arbitrary set of args and kwargs.  This
    relies on the repr of each element.

    :param args: arbitrary tuple of args.
    :param kwargs: arbitrary dictionary of kwargs.
    :returns: hashed string of the arguments.
    """
    if kwargs:
        return '%r,%r' % (args, sorted(kwargs.items()))
    return repr(args)


def methodcache(key: Optional[Callable] = None) -> Callable:  # noqa
    """
    Decorator to wrap a function with a memoizing callable that saves results
    in self.cache.  This is largely taken from cachetools, but uses a cache
    from self.cache rather than a passed value.  If self.cache_lock is
    present and not none, a lock is used.

    :param key: if a function, use that for the key, otherwise use self.wrapKey.
    """
    def decorator(func: Callable[P, T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
            k = key(*args, **kwargs) if key else self.wrapKey(*args, **kwargs)
            lock = getattr(self, 'cache_lock', None)
            ck = getattr(self, '_classkey', None)
            if lock:
                with self.cache_lock:
                    if hasattr(self, '_classkeyLock'):
                        if self._classkeyLock.acquire(blocking=False):
                            self._classkeyLock.release()
                        else:
                            ck = getattr(self, '_unlocked_classkey', ck)
            if ck:
                k = ck + ' ' + k
            try:
                if lock:
                    with self.cache_lock:
                        return self.cache[k]
                else:
                    return self.cache[k]
            except KeyError:
                pass  # key not found
            except (ValueError, pickle.UnpicklingError, ModuleNotFoundError):
                # this can happen if a different version of python wrote the record
                pass
            v = func(self, *args, **kwargs)
            try:
                if lock:
                    with self.cache_lock:
                        self.cache[k] = v
                else:
                    self.cache[k] = v
            except ValueError:
                pass  # value too large
            except (KeyError, RuntimeError):
                # the key was refused for some reason
                config.getLogger().debug(
                    'Had a cache KeyError while trying to store a value to key %r' % (k))
            return v
        return wrapper
    return decorator


class LruCacheMetaclass(type):
    namedCaches: dict[str, Any] = {}
    classCaches: dict[type, Any] = {}

    def __new__(mcs, name, bases, namespace, **kwargs):
        # Get metaclass parameters by finding and removing them from the class
        # namespace (necessary for Python 2), or preferentially as metaclass
        # arguments (only in Python 3).
        cacheName = namespace.get('cacheName', None)
        cacheName = kwargs.get('cacheName', cacheName)

        maxSize = CacheProperties.get(cacheName, {}).get('cacheMaxSize', None)
        if (maxSize is None and cacheName in CacheProperties and
                'maxItems' in CacheProperties[cacheName] and
                CacheProperties[cacheName].get('itemExpectedSize')):
            maxSize = pickAvailableCache(
                CacheProperties[cacheName]['itemExpectedSize'],
                maxItems=CacheProperties[cacheName]['maxItems'],
                cacheName=cacheName)
        maxSize = namespace.pop('cacheMaxSize', maxSize)
        maxSize = kwargs.get('cacheMaxSize', maxSize)
        if maxSize is None:
            raise TypeError('Usage of the LruCacheMetaclass requires a '
                            '"cacheMaxSize" attribute on the class %s.' % name)

        timeout = CacheProperties.get(cacheName, {}).get('cacheTimeout', None)
        timeout = namespace.pop('cacheTimeout', timeout)
        timeout = kwargs.get('cacheTimeout', timeout)

        cls = super().__new__(
            mcs, name, bases, namespace)
        if not cacheName:
            cacheName = cls

        if LruCacheMetaclass.namedCaches.get(cacheName) is None:
            cache, cacheLock = CacheFactory().getCache(
                numItems=maxSize,
                cacheName=cacheName,
                inProcess=True,
            )
            LruCacheMetaclass.namedCaches[cacheName] = (cache, cacheLock)
            config.getLogger().debug(
                'Created LRU Cache for %r with %d maximum size' % (cacheName, cache.maxsize))
        else:
            (cache, cacheLock) = LruCacheMetaclass.namedCaches[cacheName]

        # Don't store the cache in cls.__dict__, because we don't want it to be
        # part of the attribute lookup hierarchy
        # TODO: consider putting it in cls.__dict__, to inspect statistics
        # cls is hashable though, so use it to lookup the cache, in case an
        # identically-named class gets redefined
        LruCacheMetaclass.classCaches[cls] = (cache, cacheLock)

        return cls

    def __call__(cls, *args, **kwargs) -> Any:  # - N805
        if kwargs.get('noCache') or (
                kwargs.get('noCache') is None and config.getConfig('cache_sources') is False):
            instance = super().__call__(*args, **kwargs)
            # for pickling
            instance._initValues = (args, kwargs.copy())
            instance._classkey = str(uuid.uuid4())
            instance._noCache = True
            if kwargs.get('style') != getattr(cls, '_unstyledStyle', None):
                subkwargs = kwargs.copy()
                subkwargs['style'] = getattr(cls, '_unstyledStyle', None)
                instance._unstyledInstance = subresult = cls(*args, **subkwargs)
            return instance
        cache, cacheLock = LruCacheMetaclass.classCaches[cls]

        if hasattr(cls, 'getLRUHash'):
            key = cls.getLRUHash(*args, **kwargs)
        else:
            key = strhash(args[0], kwargs)
        key = cls.__name__ + ' ' + key
        with cacheLock:
            try:
                result = cache[key]
                if (not isinstance(result, tuple) or len(result) != 2 or
                        result[0] != _cacheLockKeyToken):
                    return result
                cacheLockForKey = result[1]
            except KeyError:
                # By passing and handling the cache miss outside of the
                # exception, any exceptions while trying to populate the cache
                # will not be reported in the cache exception context.
                cacheLockForKey = threading.Lock()
                cache[key] = (_cacheLockKeyToken, cacheLockForKey)
        with cacheLockForKey:
            with cacheLock:
                try:
                    result = cache[key]
                    if (not isinstance(result, tuple) or len(result) != 2 or
                            result[0] != _cacheLockKeyToken):
                        return result
                except KeyError:
                    pass
            try:
                # This conditionally copies a non-styled class and adds a style.
                if (kwargs.get('style') and hasattr(cls, '_setStyle') and
                        kwargs.get('style') != getattr(cls, '_unstyledStyle', None)):
                    subkwargs = kwargs.copy()
                    subkwargs['style'] = getattr(cls, '_unstyledStyle', None)
                    subresult = cls(*args, **subkwargs)
                    result = subresult.__class__.__new__(subresult.__class__)
                    with subresult._sourceLock:
                        result.__dict__ = subresult.__dict__.copy()
                        result._sourceLock = threading.RLock()
                    result._classkey = key
                    # for pickling
                    result._initValues = (args, kwargs.copy())
                    result._unstyledInstance = subresult
                    result._derivedSource = True
                    # Has to be after setting the _unstyledInstance
                    result._setStyle(kwargs['style'])
                    with cacheLock:
                        cache[key] = result
                        return result
                instance = super().__call__(*args, **kwargs)
                # for pickling
                instance._initValues = (args, kwargs.copy())
            except Exception as exc:
                with cacheLock, contextlib.suppress(Exception):
                    del cache[key]
                raise exc
            instance._classkey = key
            if kwargs.get('style') != getattr(cls, '_unstyledStyle', None):
                subkwargs = kwargs.copy()
                subkwargs['style'] = getattr(cls, '_unstyledStyle', None)
                instance._unstyledInstance = subresult = cls(*args, **subkwargs)
                instance._derivedSource = True
            with cacheLock:
                cache[key] = instance
        return instance


def getTileCache() -> tuple[cachetools.Cache, Optional[threading.Lock]]:
    """
    Get the preferred tile cache and lock.

    :returns: tileCache and tileLock.
    """
    global _tileCache, _tileLock

    if _tileCache is None:
        # Decide whether to use Memcached or cachetools
        _tileCache, _tileLock = CacheFactory().getCache(cacheName='tileCache')
    return _tileCache, _tileLock


def isTileCacheSetup() -> bool:
    """
    Return True if the tile cache has been created.

    :returns: True if _tileCache is not None.
    """
    return _tileCache is not None
