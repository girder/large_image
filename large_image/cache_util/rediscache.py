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

import pickle
import threading
import time
from collections.abc import Callable, Iterable, Sized
from typing import Any, Optional, TypeVar, cast

from typing_extensions import Buffer

from .. import config
from .base import BaseCache

_VT = TypeVar('_VT')


class RedisCache(BaseCache):
    """Use redis as the backing cache."""

    def __init__(
            self, url: str | list[str] = '127.0.0.1:6379',
            username: str | None = None, password: str | None = None,
            getsizeof: Callable[[_VT], float] | None = None,
            mustBeAvailable: bool = False) -> None:
        import redis
        from redis.client import Redis

        self.redis = redis
        self._redisCls = Redis
        super().__init__(0, getsizeof=getsizeof)
        self._cache_key_prefix = 'large_image_'
        self._clientParams = (f'redis://{url}', dict(
            username=username, password=password, db=0, retry_on_timeout=1))
        self._client: Redis = Redis.from_url(self._clientParams[0], **self._clientParams[1])
        if mustBeAvailable:
            # Try to ping server; this will throw an error if the server is
            # unreachable, so we don't bother trying to use it.
            self._client.ping()

    def __repr__(self) -> str:
        return "Redis doesn't list its keys"

    def __iter__(self):
        # return invalid iter
        return None

    def __len__(self) -> int:
        # return invalid length
        keys = self._client.keys(f'{self._cache_key_prefix}*')
        return len(cast(Sized, keys))

    def __contains__(self, key) -> bool:
        # cache never contains key
        _key = self._cache_key_prefix + self._hashKey(key)
        return bool(self._client.exists(_key))

    def __delitem__(self, key: str) -> None:
        if not self.__contains__(key):
            raise KeyError
        _key = self._cache_key_prefix + self._hashKey(key)
        self._client.delete(_key)

    def __getitem__(self, key: str) -> Any:
        _key = self._cache_key_prefix + self._hashKey(key)
        try:
            # must determine if tke key exists , otherwise cache_test can not be passed.
            if not self.__contains__(key):
                raise KeyError
            return pickle.loads(cast(Buffer, self._client.get(_key)))
        except KeyError:
            return self.__missing__(key)
        except self.redis.ConnectionError:
            self.logError(self.redis.ConnectionError, config.getLogger('logprint').info,
                          'redis ConnectionError')
            self._reconnect()
            return self.__missing__(key)
        except self.redis.RedisError:
            self.logError(self.redis.RedisError, config.getLogger('logprint').exception,
                          'redis RedisError')
            return self.__missing__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        _key = self._cache_key_prefix + self._hashKey(key)
        try:
            self._client.set(_key, pickle.dumps(value))
        except (TypeError, KeyError) as exc:
            valueSize = value.shape if hasattr(value, 'shape') else (
                value.size if hasattr(value, 'size') else (
                    len(value) if hasattr(value, '__len__') else None))
            valueRepr = repr(value)
            if len(valueRepr) > 500:
                valueRepr = valueRepr[:500] + '...'
            self.logError(
                exc.__class__, config.getLogger('logprint').error,
                '%s: Failed to save value (size %r) with key %s' % (
                    exc.__class__.__name__, valueSize, key))
        except self.redis.ConnectionError:
            self.logError(self.redis.ConnectionError, config.getLogger('logprint').info,
                          'redis ConnectionError')
            self._reconnect()

    @property
    def curritems(self) -> int:
        return cast(int, self._client.dbsize())

    @property
    def currsize(self) -> int:
        return self._getStat('used_memory')

    @property
    def maxsize(self) -> int:
        maxmemory = self._getStat('maxmemory')
        if maxmemory:
            return maxmemory
        return self._getStat('total_system_memory')

    def _reconnect(self) -> None:
        try:
            self._lastReconnectBackoff = getattr(self, '_lastReconnectBackoff', 2)
            if time.time() - getattr(self, '_lastReconnect', 0) > self._lastReconnectBackoff:
                config.getLogger('logprint').info('Trying to reconnect to redis server')
                self._client = self._redisCls.from_url(self._clientParams[0],
                                                       **self._clientParams[1])
                self._lastReconnectBackoff = min(self._lastReconnectBackoff + 1, 30)
                self._lastReconnect = time.time()
        except Exception:
            pass

    def _getStat(self, key: str) -> int:
        try:
            stats = self._client.info()
            value = cast(dict, stats)[key]
        except Exception:
            return 0
        return value

    def clear(self) -> None:
        keys = self._client.keys(f'{self._cache_key_prefix}*')
        if keys:
            self._client.delete(*list(cast(Iterable[Any], keys)))

    @staticmethod
    def getCache() -> tuple[Optional['RedisCache'], threading.Lock]:
        cacheLock = threading.Lock()

        # check if credentials and location exist, otherwise assume
        # location is 127.0.0.1 (localhost) with no password
        url = config.getConfig('cache_redis_url')
        if not url:
            url = '127.0.0.1:6379'
        redisUsername = config.getConfig('cache_redis_username')
        if not redisUsername:
            redisUsername = None
        redisPassword = config.getConfig('cache_redis_password')
        if not redisPassword:
            redisPassword = None
        try:
            cache = RedisCache(url, redisUsername, redisPassword,
                               mustBeAvailable=True)
        except Exception:
            config.getLogger().info('Cannot use redis for caching.')
            cache = None
        return cache, cacheLock
