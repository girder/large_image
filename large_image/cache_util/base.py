import hashlib
import threading
import time
from typing import Tuple

import cachetools


class BaseCache(cachetools.Cache):
    """Base interface to cachetools.Cache for use with large-image."""

    def __init__(self, *args, getsizeof=None, **kwargs):
        super().__init__(*args, getsizeof=getsizeof, **kwargs)
        self.lastError = {}
        self.throttleErrors = 10  # seconds between logging errors

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

    def __repr__(self):
        raise NotImplementedError

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __contains__(self, key):
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def _hashKey(self, key):
        return hashlib.sha256(key.encode()).hexdigest()

    def __getitem__(self, key):
        # hashedKey = self._hashKey(key)
        raise NotImplementedError

    def __setitem__(self, key, value):
        # hashedKey = self._hashKey(key)
        raise NotImplementedError

    @property
    def curritems(self):
        raise NotImplementedError

    @property
    def currsize(self):
        raise NotImplementedError

    @property
    def maxsize(self):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

    @staticmethod
    def getCache() -> Tuple['BaseCache', threading.Lock]:
        # return cache, cacheLock
        raise NotImplementedError
