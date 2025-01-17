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
    NP_MAX_COLOR = 12
    NP_MIN_COLOR = 13


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
    if tile.shape[0] % 2 != 0:
        tile = np.append(tile, np.expand_dims(tile[-1], axis=0), axis=0)
    if tile.shape[1] % 2 != 0:
        tile = np.append(tile, np.expand_dims(tile[:, -1], axis=1), axis=1)

    pixel_selection = None
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
    if resample_method == ResampleMethod.NP_MEDIAN:
        return np.median(subarrays, axis=0).astype(tile.dtype)
    if resample_method == ResampleMethod.NP_MAX:
        return np.max(subarrays, axis=0).astype(tile.dtype)
    if resample_method == ResampleMethod.NP_MIN:
        return np.min(subarrays, axis=0).astype(tile.dtype)
    if resample_method == ResampleMethod.NP_MAX_COLOR:
        summed = np.sum(subarrays, axis=3)
        pixel_selection = np.argmax(summed, axis=0)
    elif resample_method == ResampleMethod.NP_MIN_COLOR:
        summed = np.sum(subarrays, axis=3)
        pixel_selection = np.argmin(summed, axis=0)
    elif resample_method == ResampleMethod.NP_MODE:
        # if a pixel occurs twice in a set of four, it is a mode
        # if no mode, default to pixel 0. check for minimal matches 1=2, 1=3, 2=3
        pixel_selection = np.where(
            (
                (subarrays[1] == subarrays[2]).all(axis=2) |
                (subarrays[1] == subarrays[3]).all(axis=2)
            ),
            1, np.where(
                (subarrays[2] == subarrays[3]).all(axis=2),
                2, 0,
            ),
        )

    if pixel_selection is not None:
        if len(tile.shape) > 2:
            pixel_selection = np.expand_dims(pixel_selection, axis=2)
            pixel_selection = np.repeat(pixel_selection, tile.shape[2], axis=2)
        return np.choose(pixel_selection, subarrays).astype(tile.dtype)
    msg = f'Unknown resample method {resample_method}.'
    raise ValueError(msg)


def downsampleTileHalfRes(
    tile: np.ndarray,
    resample_method: ResampleMethod,
) -> np.ndarray:
    new_shape = {
        'height': (tile.shape[0] + 1) // 2,
        'width': (tile.shape[1] + 1) // 2,
        'bands': 1,
    }
    if len(tile.shape) > 2:
        new_shape['bands'] = tile.shape[-1]
    if resample_method.value <= ResampleMethod.PIL_MAX_ENUM.value:
        if new_shape['bands'] > 4:
            result = np.empty(
                (new_shape['height'], new_shape['width'], new_shape['bands']),
                dtype=tile.dtype,
            )
            for band_index in range(new_shape['bands']):
                result[(..., band_index)] = pilResize(
                    tile[(..., band_index)],
                    new_shape,
                    resample_method,
                )
            return result
        return pilResize(tile, new_shape, resample_method)
    return numpyResize(tile, new_shape, resample_method)
