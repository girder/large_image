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

import cachetools
import hashlib
import pylibmc
import time

from .. import config


class MemCache(cachetools.Cache):
    """Use memcached as the backing cache."""

    def __init__(self, url='127.0.0.1', username=None, password=None,
                 getsizeof=None, mustBeAvailable=False):
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
        self._client = pylibmc.Client(
            url, binary=True, username=username, password=password,
            behaviors=behaviors)
        if mustBeAvailable:
            # Try to set a value; this will throw an error if the server is
            # unreachable, so we don't bother trying to use it.
            self._client['large_image_cache_test'] = time.time()
        self.lastError = {}
        self.throttleErrors = 10  # seconds between logging errors

    def __repr__(self):
        return "Memcache doesn't list its keys"

    def __iter__(self):
        # return invalid iter
        return None

    def __len__(self):
        # return invalid length
        return -1

    def __contains__(self, key):
        # cache never contains key
        return None

    def __delitem__(self, key):
        hashedKey = hashlib.sha256(key.encode()).hexdigest()
        del self._client[hashedKey]

    def logError(self, err, func, msg):
        """
        Log errors, but throttle them so as not to spam the logs.

        :param err: error to log.
        :param func: function to use for logging.  This is something like
            logprint.exception or logger.error.
        :param msg: the message to log.
        """
        curtime = time.time()
        key = (err, func)
        if (curtime - self.lastError.get(key, {}).get('time', 0) > self.throttleErrors):
            skipped = self.lastError.get(key, {}).get('skipped', 0)
            if skipped:
                msg += '  (%d similar messages)' % skipped
            self.lastError[key] = {'time': curtime, 'skipped': 0}
            func(msg)
        else:
            self.lastError[key]['skipped'] += 1

    def __getitem__(self, key):
        hashedKey = hashlib.sha256(key.encode()).hexdigest()
        try:
            return self._client[hashedKey]
        except KeyError:
            return self.__missing__(key)
        except pylibmc.ServerDown:
            self.logError(pylibmc.ServerDown, config.getConfig('logprint').info,
                          'Memcached ServerDown')
            return self.__missing__(key)
        except pylibmc.Error:
            self.logError(pylibmc.Error, config.getConfig('logprint').exception,
                          'pylibmc exception')
            return self.__missing__(key)

    def __setitem__(self, key, value):
        hashedKey = hashlib.sha256(key.encode()).hexdigest()
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
                exc.__class__, config.getConfig('logprint').error,
                '%s: Failed to save value %s (size %r) with key %s' % (
                    exc.__class__.__name__, valueRepr, valueSize, hashedKey))
        except pylibmc.ServerDown:
            self.logError(pylibmc.ServerDown, config.getConfig('logprint').info,
                          'Memcached ServerDown')
        except pylibmc.TooBig:
            pass
        except pylibmc.Error as exc:
            # memcached won't cache items larger than 1 Mb, but this returns a
            # 'SUCCESS' error.  Raise other errors.
            if 'SUCCESS' not in repr(exc.args):
                self.logError(pylibmc.Error, config.getConfig('logprint').exception,
                              'pylibmc exception')
