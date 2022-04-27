import errno


class TileGeneralError(Exception):
    pass


class TileSourceError(TileGeneralError):
    pass


class TileSourceAssetstoreError(TileSourceError):
    pass


class TileSourceXYZRangeError(TileSourceError):
    pass


class TileSourceInefficientError(TileSourceError):
    pass


class TileSourceFileNotFoundError(TileSourceError, FileNotFoundError):
    def __init__(self, *args, **kwargs):
        return super().__init__(errno.ENOENT, *args, **kwargs)


TileGeneralException = TileGeneralError
TileSourceException = TileSourceError
TileSourceAssetstoreException = TileSourceAssetstoreError
