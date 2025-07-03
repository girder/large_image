import hashlib
import threading
import time
from typing import Any, Callable, Optional, TypeVar

import cachetools

_VT = TypeVar('_VT')


class BaseCache(cachetools.Cache):
    """Base interface to cachetools.Cache for use with large-image."""

    def __init__(
            self, maxsize: float,
            getsizeof: Optional[Callable[[_VT], float]] = None,
            **kwargs) -> None:
        super().__init__(maxsize=maxsize, getsizeof=getsizeof, **kwargs)
        self.lastError: dict[tuple[Any, Callable], dict[str, Any]] = {}
        self.throttleErrors = 10  # seconds between logging errors

    def logError(self, err: Any, func: Callable, msg: str) -> None:
        """
        Log errors, but throttle them so as not to spam the logs.

        :param err: error to log.
        :param func: function to use for logging.  This is something like
            logprint.exception or logger.error.
        :param msg: the message to log.
        """
        curtime = time.time()
        key = (err, func)
        if curtime - self.lastError.get(key, {}).get('time', 0) > self.throttleErrors:
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

    def __len__(self) -> int:
        raise NotImplementedError

    def __contains__(self, item) -> bool:
        raise NotImplementedError

    def __delitem__(self, key):
        raise NotImplementedError

    def _hashKey(self, key) -> str:
        return hashlib.sha256(key.encode()).hexdigest()

    def __getitem__(self, key):
        # hashedKey = self._hashKey(key)
        raise NotImplementedError

    def __setitem__(self, key, value):
        # hashedKey = self._hashKey(key)
        raise NotImplementedError

    @property
    def curritems(self) -> int:
        raise NotImplementedError

    @property
    def currsize(self) -> int:
        raise NotImplementedError

    @property
    def maxsize(self) -> int:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError

    @staticmethod
    def getCache() -> tuple[Optional['BaseCache'], threading.Lock]:
        # return cache, cacheLock
        raise NotImplementedError
