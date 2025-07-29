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

import copy
import threading
import time
from typing import Any, Callable, Optional, TypeVar, Union

from .. import config
from .base import BaseCache

_VT = TypeVar('_VT')


class MemCache(BaseCache):
    """Use memcached as the backing cache."""

    def __init__(
            self, url: Union[str, list[str]] = '127.0.0.1',
            username: Optional[str] = None, password: Optional[str] = None,
            getsizeof: Optional[Callable[[_VT], float]] = None,
            mustBeAvailable: bool = False) -> None:
        import pylibmc

        self.pylibmc = pylibmc
        super().__init__(0, getsizeof=getsizeof)
        if isinstance(url, str):
            url = [url]
        # pylibmc used to connect to memcached client.  Set failover behavior.
        # See http://sendapatch.se/projects/pylibmc/behaviors.html
        behaviors = {
            'tcp_nodelay': True,
            'ketama': True,
            'no_block': True,
            'retry_timeout': 1,
            'dead_timeout': 10,
        }
        # Adding remove_failed prevents recovering in a single memcached server
        # instance, so only do it if there are multiple servers
        if len(url) > 1:
            behaviors['remove_failed'] = 1
        # name mangling to override 'private variable' __data in cache
        self._clientParams = (url, dict(
            binary=True, username=username, password=password, behaviors=behaviors))
        self._client = pylibmc.Client(self._clientParams[0], **self._clientParams[1])
        if mustBeAvailable:
            # Try to set a value; this will throw an error if the server is
            # unreachable, so we don't bother trying to use it.
            self._client['large_image_cache_test'] = time.time()

    def __repr__(self) -> str:
        return "Memcache doesn't list its keys"

    def __iter__(self):
        # return invalid iter
        return None

    def __len__(self) -> int:
        # return invalid length
        return -1

    def __contains__(self, item: object) -> bool:
        # cache never contains key
        return False

    def __delitem__(self, key: str) -> None:
        hashedKey = self._hashKey(key)
        del self._client[hashedKey]

    def __getitem__(self, key: str) -> Any:
        hashedKey = self._hashKey(key)
        try:
            return self._client[hashedKey]
        except KeyError:
            return self.__missing__(key)
        except self.pylibmc.ServerDown:
            self.logError(self.pylibmc.ServerDown, config.getLogger('logprint').info,
                          'Memcached ServerDown')
            self._reconnect()
            return self.__missing__(key)
        except self.pylibmc.Error:
            self.logError(self.pylibmc.Error, config.getLogger('logprint').exception,
                          'pylibmc exception')
            return self.__missing__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        hashedKey = self._hashKey(key)
        try:
            self._client[hashedKey] = value
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
                    exc.__class__.__name__, valueSize, hashedKey))
        except self.pylibmc.ServerDown:
            self.logError(self.pylibmc.ServerDown, config.getLogger('logprint').info,
                          'Memcached ServerDown')
            self._reconnect()
        except self.pylibmc.TooBig:
            pass
        except self.pylibmc.Error as exc:
            # memcached won't cache items larger than 1 Mb (or a configured
            # size), but this returns a 'SUCCESS' error.  Raise other errors.
            if 'SUCCESS' not in repr(exc.args):
                self.logError(self.pylibmc.Error, config.getLogger('logprint').exception,
                              'pylibmc exception')

    @property
    def curritems(self) -> int:
        return self._getStat('curr_items')

    @property
    def currsize(self) -> int:
        return self._getStat('bytes')

    @property
    def maxsize(self) -> int:
        return self._getStat('limit_maxbytes')

    def _reconnect(self) -> None:
        try:
            self._lastReconnectBackoff = getattr(self, '_lastReconnectBackoff', 2)
            if time.time() - getattr(self, '_lastReconnect', 0) > self._lastReconnectBackoff:
                config.getLogger('logprint').info('Trying to reconnect to memcached server')
                self._client = self.pylibmc.Client(self._clientParams[0], **self._clientParams[1])
                self._lastReconnectBackoff = min(self._lastReconnectBackoff + 1, 30)
                self._lastReconnect = time.time()
        except Exception:
            pass

    def _blockingClient(self) -> Any:
        params = copy.deepcopy(self._clientParams)
        params[1]['behaviors']['no_block'] = False  # type: ignore
        return self.pylibmc.Client(params[0], **params[1])

    def _getStat(self, key: str) -> int:
        try:
            stats = self._blockingClient().get_stats()
            value = sum(int(s[key]) for server, s in stats)
        except Exception:
            return 0
        return value

    def clear(self) -> None:
        self._client.flush_all()

    @staticmethod
    def getCache() -> tuple[Optional['MemCache'], threading.Lock]:
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
            config.getLogger().info('Cannot use memcached for caching.')
            cache = None
        return cache, cacheLock
