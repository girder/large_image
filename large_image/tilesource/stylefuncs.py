# This module contains functions for use in styles

import numpy


def maskPixelValues(image, context, values=None, negative=None, positive=None):
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
    mask = numpy.full(src.shape[:2], False)
    for val in values:
        if not isinstance(val, (list, tuple)):
            if src.shape[-1] == 1:
                val = [val]
            else:
                val = [val % 256, val // 256 % 256, val // 65536 % 256]
        val = (list(val) + [255] * src.shape[2])[:src.shape[2]]
        match = numpy.array(val)
        mask = mask | (src == match).all(axis=-1)
    image[mask != True] = negative or [0, 0, 0, 255]  # noqa E712
    image[mask] = positive or [255, 255, 255, 0]
    image = image.astype(numpy.uint8)
    return image
