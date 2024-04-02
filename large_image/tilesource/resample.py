from enum import Enum
from typing import Dict

import numpy as np
from PIL import Image


class ResampleMethod(Enum):
    PIL_NEAREST = Image.Resampling.NEAREST  # 0
    PIL_LANCZOS = Image.Resampling.LANCZOS  # 1
    PIL_BILINEAR = Image.Resampling.BILINEAR  # 2
    PIL_BICUBIC = Image.Resampling.BICUBIC  # 3
    PIL_BOX = Image.Resampling.BOX  # 4
    PIL_HAMMING = Image.Resampling.HAMMING  # 5
    PIL_MAX_ENUM = 5
    NP_MEAN = 6
    NP_MEDIAN = 7
    NP_MODE = 8
    NP_MAX = 9
    NP_MIN = 10
    NP_NEAREST = 11
    NP_MAX_CROSSBAND = 12
    NP_MIN_CROSSBAND = 13


def pilResize(
    tile: np.ndarray,
    new_shape: Dict,
    resample_method: ResampleMethod,
) -> np.ndarray:
    # Only NEAREST works for 16 bit images
    img = Image.fromarray(tile)
    resized_img = img.resize(
        (new_shape['width'], new_shape['height']),
        resample=resample_method.value,
    )
    result = np.array(resized_img).astype(tile.dtype)
    return result


def numpyResize(
    tile: np.ndarray,
    new_shape: Dict,
    resample_method: ResampleMethod,
) -> np.ndarray:
    if resample_method == ResampleMethod.NP_NEAREST:
        return tile[::2, ::2]
    else:
        subarrays = np.asarray(
            [
                tile[0::2, 0::2],
                tile[1::2, 0::2],
                tile[0::2, 1::2],
                tile[1::2, 1::2],
            ],
        )
        if resample_method == ResampleMethod.NP_MEAN:
            return np.mean(subarrays, axis=0).astype(tile.dtype)
        elif resample_method == ResampleMethod.NP_MEDIAN:
            return np.median(subarrays, axis=0).astype(tile.dtype)
        elif resample_method == ResampleMethod.NP_MODE:
            result_shape = subarrays[0].shape
            result = np.empty(result_shape)
            subarrays = subarrays.transpose(1, 2, 0, 3)
            for y in range(result_shape[0]):
                for x in range(result_shape[1]):
                    vals, counts = np.unique(subarrays[y, x], axis=0, return_counts=True)
                    mode = vals[np.argmax(counts)]
                    result[y, x] = mode
            return result
        elif resample_method == ResampleMethod.NP_MAX:
            summed = np.sum(subarrays, axis=3)
            indexes = np.argmax(summed, axis=0)
            indexes = np.repeat(indexes[:, :, np.newaxis], tile.shape[2], axis=2)
            return np.choose(indexes, subarrays).astype(tile.dtype)
        elif resample_method == ResampleMethod.NP_MIN:
            summed = np.sum(subarrays, axis=3)
            indexes = np.argmin(summed, axis=0)
            indexes = np.repeat(indexes[:, :, np.newaxis], tile.shape[2], axis=2)
            return np.choose(indexes, subarrays).astype(tile.dtype)
        elif resample_method == ResampleMethod.NP_MAX_CROSSBAND:
            return np.max(subarrays, axis=0).astype(tile.dtype)
        elif resample_method == ResampleMethod.NP_MIN_CROSSBAND:
            return np.min(subarrays, axis=0).astype(tile.dtype)


def downsampleTileHalfRes(
    tile: np.ndarray,
    resample_method: ResampleMethod,
) -> np.ndarray:

    resize_function = (
        pilResize
        if resample_method.value <= ResampleMethod.PIL_MAX_ENUM.value
        else numpyResize
    )
    new_shape = {
        'height': int(tile.shape[0] / 2),
        'width': int(tile.shape[1] / 2),
        'bands': 1,
    }
    if len(tile.shape) > 2:
        new_shape['bands'] = tile.shape[-1]
    if new_shape['bands'] > 4:
        result = np.empty(
            (new_shape['height'], new_shape['width'], new_shape['bands']),
            dtype=tile.dtype,
        )
        for band_index in range(new_shape['bands']):
            result[(..., band_index)] = resize_function(
                tile[(..., band_index)],
                new_shape,
                resample_method,
            )
        return result
    else:
        return resize_function(tile, new_shape, resample_method)
