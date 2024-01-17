# This module contains functions for use in styles

from types import SimpleNamespace
from typing import List, Optional, Tuple, Union

import numpy as np

from .utilities import _imageToNumpy, _imageToPIL


def maskPixelValues(
        image: np.ndarray, context: SimpleNamespace,
        values: List[Union[int, List[int], Tuple[int, ...]]],
        negative: Optional[int] = None, positive: Optional[int] = None) -> np.ndarray:
    """
    This is a style utility function that returns a black-and-white 8-bit image
    where the image is white if the pixel of the source image is in a list of
    values and black otherwise.  The values is a list where each entry can
    either be a tuple the same length as the band dimension of the output image
    or a single value which is handled as 0xBBGGRR.

    :param image: a numpy array of Y, X, Bands.
    :param context: the style context.  context.image is the source image
    :param values: an array of values, each of which is either an array of the
        same number of bands as the source image or a single value of the form
        0xBBGGRR assuming uint8 data.
    :param negative: None to use [0, 0, 0, 255], or an RGBA uint8 value for
        pixels not in the value list.
    :param positive: None to use [255, 255, 255, 0], or an RGBA uint8 value for
        pixels in the value list.
    :returns: an RGBA numpy image which is exactly black or transparent white.
    """
    src = context.image
    mask = np.full(src.shape[:2], False)
    for val in values:
        vallist: List[float]
        if not isinstance(val, (list, tuple)):
            if src.shape[-1] == 1:
                vallist = [val]
            else:
                vallist = [val % 256, val // 256 % 256, val // 65536 % 256]
        else:
            vallist = list(val)
        vallist = (vallist + [255] * src.shape[2])[:src.shape[2]]
        match = np.array(vallist)
        mask = mask | (src == match).all(axis=-1)
    image[mask != True] = negative or [0, 0, 0, 255]  # noqa E712
    image[mask] = positive or [255, 255, 255, 0]
    image = image.astype(np.uint8)
    return image


def medianFilter(
        image: np.ndarray, context: Optional[SimpleNamespace] = None,
        kernel: int = 5, weight: float = 1.0) -> np.ndarray:
    """
    This is a style utility function that applies a median rank filter to the
    image to sharpen it.

    :param image: a numpy array of Y, X, Bands.
    :param context: the style context.  context.image is the source image
    :param kernel: the filter kernel size.
    :param weight: the weight of the difference between the image and the
        filtered image that is used to add into the image.  0 is no effect/
    :returns: an numpy image which is the filtered version of the source.
    """
    import PIL.ImageFilter

    filt = PIL.ImageFilter.MedianFilter(kernel)
    if len(image.shape) != 3:
        pilimg = _imageToPIL(image)
    elif image.shape[2] >= 3:
        pilimg = _imageToPIL(image[:, :, :3])
    else:
        pilimg = _imageToPIL(image[:, :, :1])
    fimg = _imageToNumpy(pilimg.filter(filt))[0]
    mul: float = 0
    clip = 0
    if image.dtype == np.uint8 or (
            image.dtype.kind == 'f' and 1 < np.max(image) < 256 and np.min(image) >= 0):
        mul = 1
        clip = 255
    elif image.dtype == np.uint16 or (
            image.dtype.kind == 'f' and 1 < np.max(image) < 65536 and np.min(image) >= 0):
        mul = 257
        clip = 65535
    elif image.dtype == np.uint32:
        mul = (2 ** 32 - 1) / 255
        clip = 2 ** 32 - 1
    elif image.dtype.kind == 'f':
        mul = 1
    if mul:
        pimg: np.ndarray = image.astype(float)
        if len(pimg.shape) == 2:
            pimg = np.resize(pimg, (pimg.shape[0], pimg.shape[1], 1))
        pimg = pimg[:, :, :fimg.shape[2]]  # type: ignore[index,misc]
        dimg = (pimg - fimg.astype(float) * mul) * weight
        pimg = pimg[:, :, :fimg.shape[2]] + dimg  # type: ignore[index,misc]
        if clip:
            pimg = pimg.clip(0, clip)
        if len(image.shape) != 3:
            image[:, :] = np.resize(pimg.astype(image.dtype), (pimg.shape[0], pimg.shape[1]))
        else:
            image[:, :, :fimg.shape[2]] = pimg.astype(image.dtype)
    return image
