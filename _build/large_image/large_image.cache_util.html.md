# large_image.cache_util package

## Submodules

## large_image.cache_util.base module

### *class* large_image.cache_util.base.BaseCache(maxsize: float, getsizeof: Callable[[\_VT], float] | None = None, \*\*kwargs)

Bases: `Cache`

Base interface to cachetools.Cache for use with large-image.

#### clear() → None.  Remove all items from D.

#### *property* curritems *: int*

#### *property* currsize *: int*

The current size of the cache.

#### *static* getCache() → tuple[[BaseCache](#large_image.cache_util.base.BaseCache) | None, allocate_lock]

#### logError(err: Any, func: Callable, msg: str) → None

Log errors, but throttle them so as not to spam the logs.

* **Parameters:**
  * **err** – error to log.
  * **func** – function to use for logging.  This is something like
    logprint.exception or logger.error.
  * **msg** – the message to log.

#### *property* maxsize *: int*

The maximum size of the cache.

## large_image.cache_util.cache module

### *class* large_image.cache_util.cache.LruCacheMetaclass(name, bases, namespace, \*\*kwargs)

Bases: `type`

#### classCaches *: dict[type, Any]* *= {}*

#### namedCaches *: dict[str, Any]* *= {}*

### large_image.cache_util.cache.getTileCache() → tuple[cachetools.Cache, threading.Lock | None]

Get the preferred tile cache and lock.

* **Returns:**
  tileCache and tileLock.

### large_image.cache_util.cache.isTileCacheSetup() → bool

Return True if the tile cache has been created.

* **Returns:**
  True if \_tileCache is not None.

### large_image.cache_util.cache.methodcache(key: Callable | None = None) → Callable

Decorator to wrap a function with a memoizing callable that saves results
in self.cache.  This is largely taken from cachetools, but uses a cache
from self.cache rather than a passed value.  If self.cache_lock is
present and not none, a lock is used.

* **Parameters:**
  **key** – if a function, use that for the key, otherwise use self.wrapKey.

### large_image.cache_util.cache.strhash(\*args, \*\*kwargs) → str

Generate a string hash value for an arbitrary set of args and kwargs.  This
relies on the repr of each element.

* **Parameters:**
  * **args** – arbitrary tuple of args.
  * **kwargs** – arbitrary dictionary of kwargs.
* **Returns:**
  hashed string of the arguments.

## large_image.cache_util.cachefactory module

### *class* large_image.cache_util.cachefactory.CacheFactory

Bases: `object`

#### getCache(numItems: int | None = None, cacheName: str | None = None, inProcess: bool = False) → tuple[cachetools.Cache, threading.Lock | None]

#### getCacheSize(numItems: int | None, cacheName: str | None = None) → int

#### logged *= False*

### large_image.cache_util.cachefactory.getFirstAvailableCache() → tuple[cachetools.Cache | None, threading.Lock | None]

### large_image.cache_util.cachefactory.loadCaches(entryPointName: str = 'large_image.cache', sourceDict: dict[str, type[Cache]] = {}) → None

Load all caches from entrypoints and add them to the
availableCaches dictionary.

* **Parameters:**
  * **entryPointName** – the name of the entry points to load.
  * **sourceDict** – a dictionary to populate with the loaded caches.

### large_image.cache_util.cachefactory.pickAvailableCache(sizeEach: int, portion: int = 8, maxItems: int | None = None, cacheName: str | None = None) → int

Given an estimated size of an item, return how many of those items would
fit in a fixed portion of the available virtual memory.

* **Parameters:**
  * **sizeEach** – the expected size of an item that could be cached.
  * **portion** – the inverse fraction of the memory which can be used.
  * **maxItems** – if specified, the number of items is never more than this
    value.
  * **cacheName** – if specified, the portion can be affected by the
    configuration.
* **Returns:**
  the number of items that should be cached.  Always at least two,
  unless maxItems is less.

## large_image.cache_util.memcache module

### *class* large_image.cache_util.memcache.MemCache(url: str | list[str] = '127.0.0.1', username: str | None = None, password: str | None = None, getsizeof: Callable[[\_VT], float] | None = None, mustBeAvailable: bool = False)

Bases: [`BaseCache`](#large_image.cache_util.base.BaseCache)

Use memcached as the backing cache.

#### clear() → None.  Remove all items from D.

#### *property* curritems *: int*

#### *property* currsize *: int*

The current size of the cache.

#### *static* getCache() → tuple[[MemCache](#large_image.cache_util.memcache.MemCache) | None, allocate_lock]

#### *property* maxsize *: int*

The maximum size of the cache.

## large_image.cache_util.rediscache module

### *class* large_image.cache_util.rediscache.RedisCache(url: str | list[str] = '127.0.0.1:6379', username: str | None = None, password: str | None = None, getsizeof: Callable[[\_VT], float] | None = None, mustBeAvailable: bool = False)

Bases: [`BaseCache`](#large_image.cache_util.base.BaseCache)

Use redis as the backing cache.

For compatibility reasons, this can take a list of urls, but if passed,
only the first value of the list is used.

#### clear() → None.  Remove all items from D.

#### *property* curritems *: int*

#### *property* currsize *: int*

The current size of the cache.

#### *static* getCache() → tuple[[RedisCache](#large_image.cache_util.rediscache.RedisCache) | None, allocate_lock]

#### *property* maxsize *: int*

The maximum size of the cache.

## Module contents

### *class* large_image.cache_util.CacheFactory

Bases: `object`

#### getCache(numItems: int | None = None, cacheName: str | None = None, inProcess: bool = False) → tuple[cachetools.Cache, threading.Lock | None]

#### getCacheSize(numItems: int | None, cacheName: str | None = None) → int

#### logged *= False*

### *class* large_image.cache_util.LruCacheMetaclass(name, bases, namespace, \*\*kwargs)

Bases: `type`

#### classCaches *: dict[type, Any]* *= {}*

#### namedCaches *: dict[str, Any]* *= {}*

### *class* large_image.cache_util.MemCache(url: str | list[str] = '127.0.0.1', username: str | None = None, password: str | None = None, getsizeof: Callable[[\_VT], float] | None = None, mustBeAvailable: bool = False)

Bases: [`BaseCache`](#large_image.cache_util.base.BaseCache)

Use memcached as the backing cache.

#### clear() → None.  Remove all items from D.

#### *property* curritems *: int*

#### *property* currsize *: int*

The current size of the cache.

#### *static* getCache() → tuple[[MemCache](#large_image.cache_util.memcache.MemCache) | None, allocate_lock]

#### *property* maxsize *: int*

The maximum size of the cache.

### *class* large_image.cache_util.RedisCache(url: str | list[str] = '127.0.0.1:6379', username: str | None = None, password: str | None = None, getsizeof: Callable[[\_VT], float] | None = None, mustBeAvailable: bool = False)

Bases: [`BaseCache`](#large_image.cache_util.base.BaseCache)

Use redis as the backing cache.

For compatibility reasons, this can take a list of urls, but if passed,
only the first value of the list is used.

#### clear() → None.  Remove all items from D.

#### *property* curritems *: int*

#### *property* currsize *: int*

The current size of the cache.

#### *static* getCache() → tuple[[RedisCache](#large_image.cache_util.rediscache.RedisCache) | None, allocate_lock]

#### *property* maxsize *: int*

The maximum size of the cache.

### large_image.cache_util.getTileCache() → tuple[cachetools.Cache, threading.Lock | None]

Get the preferred tile cache and lock.

* **Returns:**
  tileCache and tileLock.

### large_image.cache_util.isTileCacheSetup() → bool

Return True if the tile cache has been created.

* **Returns:**
  True if \_tileCache is not None.

### large_image.cache_util.methodcache(key: Callable | None = None) → Callable

Decorator to wrap a function with a memoizing callable that saves results
in self.cache.  This is largely taken from cachetools, but uses a cache
from self.cache rather than a passed value.  If self.cache_lock is
present and not none, a lock is used.

* **Parameters:**
  **key** – if a function, use that for the key, otherwise use self.wrapKey.

### large_image.cache_util.pickAvailableCache(sizeEach: int, portion: int = 8, maxItems: int | None = None, cacheName: str | None = None) → int

Given an estimated size of an item, return how many of those items would
fit in a fixed portion of the available virtual memory.

* **Parameters:**
  * **sizeEach** – the expected size of an item that could be cached.
  * **portion** – the inverse fraction of the memory which can be used.
  * **maxItems** – if specified, the number of items is never more than this
    value.
  * **cacheName** – if specified, the portion can be affected by the
    configuration.
* **Returns:**
  the number of items that should be cached.  Always at least two,
  unless maxItems is less.

### large_image.cache_util.strhash(\*args, \*\*kwargs) → str

Generate a string hash value for an arbitrary set of args and kwargs.  This
relies on the repr of each element.

* **Parameters:**
  * **args** – arbitrary tuple of args.
  * **kwargs** – arbitrary dictionary of kwargs.
* **Returns:**
  hashed string of the arguments.
