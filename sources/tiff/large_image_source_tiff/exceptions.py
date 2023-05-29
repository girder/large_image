class TiffError(Exception):
    pass


class InvalidOperationTiffError(TiffError):
    """
    An exception caused by the user making an invalid request of a TIFF file.
    """

    pass


class IOTiffError(TiffError):
    """
    An exception caused by an internal failure, due to an invalid file or other
    error.
    """

    pass


class IOOpenTiffError(IOTiffError):
    """
    An exception caused by an internal failure where the file cannot be opened
    by the main library.
    """

    pass


class ValidationTiffError(TiffError):
    """
    An exception caused by the TIFF reader not being able to support a given
    file.
    """

    pass
