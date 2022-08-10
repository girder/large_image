import copy
import functools
import threading

try:
    import resource
except ImportError:
    resource = None

from .. import config
from .cachefactory import CacheFactory, pickAvailableCache

_tileCache = None
_tileLock = None

_cacheLockKeyToken = '_cacheLock_key'


# If we have a resource module, ask to use as many file handles as the hard
# limit allows, then calculate how may tile sources we can have open based on
# the actual limit.
MaximumTileSources = 10
if resource:
    try:
        SoftNoFile, HardNoFile = resource.getrlimit(resource.RLIMIT_NOFILE)
        resource.setrlimit(resource.RLIMIT_NOFILE, (HardNoFile, HardNoFile))
        SoftNoFile, HardNoFile = resource.getrlimit(resource.RLIMIT_NOFILE)
        # Reserve some file handles for general use, and expect that tile
        # sources could use many handles each.  This is conservative, since
        # running out of file handles breaks the program in general.
        MaximumTileSources = max(3, (SoftNoFile - 10) / 20)
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
    }
}


def strhash(*args, **kwargs):
    """
    Generate a string hash value for an arbitrary set of args and kwargs.  This
    relies on the repr of each element.

    :param args: arbitrary tuple of args.
    :param kwargs: arbitrary dictionary of kwargs.
    :returns: hashed string of the arguments.
    """
    if kwargs:
        return '%r,%r' % (args, sorted(kwargs.items()))
    return '%r' % (args, )


def methodcache(key=None):
    """
    Decorator to wrap a function with a memoizing callable that saves results
    in self.cache.  This is largely taken from cachetools, but uses a cache
    from self.cache rather than a passed value.  If self.cache_lock is
    present and not none, a lock is used.

    :param key: if a function, use that for the key, otherwise use self.wrapKey.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            k = key(*args, **kwargs) if key else self.wrapKey(*args, **kwargs)
            if hasattr(self, '_classkey'):
                k = self._classkey + ' ' + k
            lock = getattr(self, 'cache_lock', None)
            try:
                if lock:
                    with self.cache_lock:
                        return self.cache[k]
                else:
                    return self.cache[k]
            except KeyError:
                pass  # key not found
            except ValueError:
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
                config.getConfig('logger').debug(
                    'Had a cache KeyError while trying to store a value to key %r' % (k))
            return v
        return wrapper
    return decorator


class LruCacheMetaclass(type):
    """
    """
    namedCaches = {}
    classCaches = {}

    def __new__(metacls, name, bases, namespace, **kwargs):  # noqa - N804
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
            metacls, name, bases, namespace)
        if not cacheName:
            cacheName = cls

        if LruCacheMetaclass.namedCaches.get(cacheName) is None:
            cache, cacheLock = CacheFactory().getCache(
                numItems=maxSize,
                cacheName=cacheName,
                inProcess=True,
            )
            LruCacheMetaclass.namedCaches[cacheName] = (cache, cacheLock)
            config.getConfig('logger').debug(
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

    def __call__(cls, *args, **kwargs):  # noqa - N805

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
            # This conditionally copies a non-styled class and add a style.
            if kwargs.get('style') and hasattr(cls, '_setStyle'):
                subkwargs = kwargs.copy()
                subkwargs.pop('style')
                subresult = cls(*args, **subkwargs)
                result = copy.copy(subresult)
                result._setStyle(kwargs['style'])
                result._classkey = key
                with cacheLock:
                    cache[key] = result
                    return result
            try:
                instance = super().__call__(*args, **kwargs)
            except Exception as exc:
                with cacheLock:
                    try:
                        del cache[key]
                    except Exception:
                        pass
                raise exc
            instance._classkey = key
            with cacheLock:
                cache[key] = instance
        return instance


def getTileCache():
    """
    Get the preferred tile cache and lock.

    :returns: tileCache and tileLock.
    """
    global _tileCache, _tileLock

    if _tileCache is None:
        # Decide whether to use Memcached or cachetools
        _tileCache, _tileLock = CacheFactory().getCache(cacheName='tileCache')
    return _tileCache, _tileLock


def isTileCacheSetup():
    """
    Return True if the tile cache has been created.

    :returns: True if _tileCache is not None.
    """
    return _tileCache is not None
