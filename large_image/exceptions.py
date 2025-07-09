import errno
from typing import Any


class TileGeneralError(Exception):
    pass


class TileSourceError(TileGeneralError):
    pass


class TileSourceAssetstoreError(TileSourceError):
    pass


class TileSourceRangeError(TileSourceError):
    pass


class TileSourceXYZRangeError(TileSourceRangeError):
    pass


class TileSourceInefficientError(TileSourceError):
    pass


class TileSourceMalformedError(TileSourceError):
    pass


class TileSourceFileNotFoundError(TileSourceError, FileNotFoundError):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(errno.ENOENT, *args, **kwargs)


class TileCacheError(TileGeneralError):
    pass


class TileCacheConfigurationError(TileCacheError):
    pass


def _improveJsonschemaValidationError(exp):
    try:
        error_freq: dict[str, Any] = {}
        for err in exp.context:
            key = err.schema_path[0]
            error_freq.setdefault(key, [])
            error_freq[key].append(err)
        min_error = min(error_freq.values(), key=lambda k: (len(k), k[0].schema_path))[0]
        for key in dir(min_error):
            if not key.startswith('_'):
                try:
                    setattr(exp, key, getattr(min_error, key))
                except Exception:
                    pass
    except Exception:
        pass


TileGeneralException = TileGeneralError
TileSourceException = TileSourceError
TileSourceAssetstoreException = TileSourceAssetstoreError
