from enum import Enum

from PIL.Image import Resampling

# TODO: move this module to large_image/tilesource if the
# implementation does not include any zarr-specific functions
# and type it! if it is moved


def resample_mean(data):
    print('resample mean', data)


def resample_median(data):
    print('resample median', data)


def resample_mode(data):
    print('resample mode', data)


def resample_max(data):
    print('resample max', data)


def resample_min(data):
    print('resample min', data)


def resample_nearest(data):
    print('resample nearest', data)


class ResampleMethod(Enum):
    MEAN = resample_mean
    MEDIAN = resample_median
    MODE = resample_mode
    MAX = resample_max
    MIN = resample_min
    NEAREST = resample_nearest
    PIL_BICUBIC = Resampling.BICUBIC
    PIL_BILINEAR = Resampling.BILINEAR
    PIL_BOX = Resampling.BOX
    PIL_HAMMING = Resampling.HAMMING
    PIL_LANCZOS = Resampling.LANCZOS
    PIL_NEAREST = Resampling.NEAREST
