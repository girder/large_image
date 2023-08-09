class TiffError(Exception):
    pass


class InvalidOperationTiffError(TiffError):
    """
    An exception caused by the user making an invalid request of a TIFF file.
    """


class IOTiffError(TiffError):
    """
    An exception caused by an internal failure, due to an invalid file or other
    error.
    """


class IOOpenTiffError(IOTiffError):
    """
    An exception caused by an internal failure where the file cannot be opened
    by the main library.
    """


class ValidationTiffError(TiffError):
    """
    An exception caused by the TIFF reader not being able to support a given
    file.
    """
