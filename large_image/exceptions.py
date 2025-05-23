import errno


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


TileGeneralException = TileGeneralError
TileSourceException = TileSourceError
TileSourceAssetstoreException = TileSourceAssetstoreError
