"""Image padding and color conversion helpers for eager reads."""

import math
from typing import Any

import numpy as np


def padding(array: np.ndarray, xx: int, yy: int):
    """Pad a two-dimensional or image array to a requested size.

    :param array: Input array to pad.
    :param xx: Desired output height.
    :param yy: Desired output width.
    :returns: The padded array.
    """
    h = array.shape[0]
    w = array.shape[1]
    array.shape[2]

    a = (xx - h) // 2
    aa = xx - a - h

    b = (yy - w) // 2
    bb = yy - b - w

    return np.pad(array, pad_width=((a, aa), (b, bb), (0, 0)), mode='constant')


def rgba2rgb(img_rgba: np.ndarray, background: tuple = (255, 255, 255)):
    """Convert an RGBA image to RGB by compositing over a background color.

    :param img_rgba: Input RGB or RGBA image as a numpy array.
    :param background: RGB background color used for transparent pixels.
    :returns: An RGB numpy array.
    """
    row, col, ch = img_rgba.shape

    if ch == 3:
        return img_rgba

    assert ch == 4, 'RGBA image has 4 channels.'

    rgb = np.zeros((row, col, 3), dtype=np.float32)
    r, g, b, a = img_rgba[:, :, 0], img_rgba[:, :, 1], img_rgba[:, :, 2], img_rgba[:, :, 3]

    a = np.asarray(a, dtype=np.float32) / 255.0

    R, G, B = background

    rgb[:, :, 0] = r * a + (1.0 - a) * R
    rgb[:, :, 1] = g * a + (1.0 - a) * G
    rgb[:, :, 2] = b * a + (1.0 - a) * B

    return np.asarray(rgb, dtype=np.uint8)


def pad_color(image: np.ndarray, top: int, bottom: int, left: int, right: int, color: tuple):
    """Pad an image with a constant RGB color.

    :param image: Image array in HWC layout.
    :param top: Number of rows to add above the image.
    :param bottom: Number of rows to add below the image.
    :param left: Number of columns to add before the image.
    :param right: Number of columns to add after the image.
    :param color: RGB color tuple used for the padded pixels.
    :returns: The padded image array.
    """
    r = np.pad(
        image[:, :, 0], ((top, bottom), (left, right)), mode='constant', constant_values=color[0],
    )
    g = np.pad(
        image[:, :, 1], ((top, bottom), (left, right)), mode='constant', constant_values=color[1],
    )
    b = np.pad(
        image[:, :, 2], ((top, bottom), (left, right)), mode='constant', constant_values=color[2],
    )
    return np.stack((r, g, b), axis=-1)


def pad_tile(tile: np.ndarray, w: int, h: int, pad_mode: str, pad_fill_mode: str):
    """Pad a tile to a target width and height.

    :param tile: Tile image in HWC layout.
    :param w: Desired output width.
    :param h: Desired output height.
    :param pad_mode: Padding placement mode, either 'equal' or 'right_bottom'.
    :param pad_fill_mode: Fill mode passed to return_constant_color.
    :returns: A tile padded to the requested size.
    """
    out = tile.copy()

    constant_color = return_constant_color(tile, pad_fill_mode)

    # Based on pad mode choose how padding will be applied to image top, bottom, left and right
    if pad_mode == 'wsi_edge':
        msg = "pad_mode 'wsi_edge' is not implemented for tile padding."
        raise NotImplementedError(msg)
    if pad_mode == 'equal':
        top, bottom, left, right = return_needed_padding_equal(tile, w, h)
        out = pad_color(out, top, bottom, left, right, constant_color)
    elif pad_mode == 'right_bottom':
        top, bottom, left, right = return_needed_padding_right_bottom(tile, w, h)
        out = pad_color(out, top, bottom, left, right, constant_color)
    else:
        msg = "Invalid pad_mode value. Must be 'wsi_edge' or 'equal'."
        raise ValueError(msg)

    return out


def return_constant_color(image: np.ndarray, pad_fill_mode: Any):
    # Determine the color that will be used for paadding
    """Resolve the RGB color used for padding.

    :param image: Source image used by data-dependent fill modes.
    :param pad_fill_mode: Fill mode, RGB tuple, or scalar channel value.
    :returns: An RGB color tuple.
    """
    if image.shape[0] == 0 or image.shape[1] == 0:
        return (0, 0, 0)

    if isinstance(pad_fill_mode, str):
        if pad_fill_mode == 'mean_color':
            mean_pixel = np.floor(np.mean(image, axis=(0, 1))).astype(np.uint8)
            constant_color = (mean_pixel[0], mean_pixel[1], mean_pixel[2])
        elif pad_fill_mode == 'default':
            constant_color = (0, 0, 0)
        elif pad_fill_mode == 'white':
            constant_color = (255, 255, 255)
        elif pad_fill_mode == 'max':
            max_pixel = np.max(image)
            constant_color = (max_pixel, max_pixel, max_pixel)
        return constant_color
    if isinstance(pad_fill_mode, int):
        constant_color = (pad_fill_mode, pad_fill_mode, pad_fill_mode)
    elif isinstance(pad_fill_mode, tuple):
        constant_color = pad_fill_mode
    elif isinstance(pad_fill_mode, list):
        constant_color = pad_fill_mode
    else:
        msg = "Invalid pad_fill_mode.  Must be 'default', 'max', int or tuple."
        raise ValueError(msg)

    return constant_color


def return_needed_padding_wsi_edge(
    image: np.ndarray, w: int, h: int, t_dist: int, b_dist: int, l_dist: int, r_dist: int,
):
    """Calculate padding amounts that preserve whole-slide-image edge alignment.

    :param image: Image array to pad.
    :param w: Desired output width.
    :param h: Desired output height.
    :param t_dist: Distance from the image top edge.
    :param b_dist: Distance from the image bottom edge.
    :param l_dist: Distance from the image left edge.
    :param r_dist: Distance from the image right edge.
    :returns: Padding as top, bottom, left, and right pixel counts.
    """
    x_pad = w - image.shape[1]
    y_pad = h - image.shape[0]

    top = 0
    bottom = 0
    left = 0
    right = 0

    if image.shape[1] != w and l_dist < r_dist and x_pad > 0:
        left = x_pad
    if image.shape[1] != w and l_dist > r_dist and x_pad > 0:
        right = x_pad
    if image.shape[0] != h and t_dist < b_dist and y_pad > 0:
        top = y_pad
    if image.shape[0] != h and t_dist > b_dist and y_pad > 0:
        bottom = y_pad

    return top, bottom, left, right


def return_needed_padding_right_bottom(image: np.ndarray, w: int, h: int):
    """Calculate padding that extends only the right and bottom edges.

    :param image: Image array to pad.
    :param w: Desired output width.
    :param h: Desired output height.
    :returns: Padding as top, bottom, left, and right pixel counts.
    """
    x_pad = w - image.shape[1]
    y_pad = h - image.shape[0]

    left = 0
    right = 0
    top = 0
    bottom = 0

    if image.shape[1] != w:
        right = x_pad
    if image.shape[0] != h:
        bottom = y_pad

    return top, bottom, left, right


def return_needed_padding_equal(image: np.ndarray, w: int, h: int):
    """Calculate symmetric padding for a target tile size.

    :param image: Image array to pad.
    :param w: Desired output width.
    :param h: Desired output height.
    :returns: Padding as top, bottom, left, and right pixel counts.
    """
    x_pad = w - image.shape[1]
    y_pad = h - image.shape[0]

    left = 0
    right = 0
    top = 0
    bottom = 0

    if image.shape[1] != w:
        if x_pad % 2 != 0:
            left = math.floor(x_pad / 2)
            right = math.ceil(x_pad / 2)
        else:
            left = x_pad // 2
            right = x_pad // 2
    if image.shape[0] != h:
        if y_pad % 2 != 0:
            top = math.floor(y_pad / 2)
            bottom = math.ceil(y_pad / 2)
        else:
            top = y_pad // 2
            bottom = y_pad // 2

    return top, bottom, left, right


def remove_unnecessary_image_information(
    slide_dimensions: dict,
    chunk: np.ndarray,
    xlt: np.ndarray,
    xrt: np.ndarray,
    ytt: np.ndarray,
    ybt: np.ndarray,
    pad_fill_mode: str,
):
    """Fill chunk pixels that extend beyond the selected slide region.

    :param slide_dimensions: Slide dimension metadata for the selected region.
    :param chunk: Chunk image array to update in place.
    :param xlt: Left coordinates for requested tiles or regions.
    :param xrt: Right coordinates for requested tiles or regions.
    :param ytt: Top coordinates for requested tiles or regions.
    :param ybt: Bottom coordinates for requested tiles or regions.
    :param pad_fill_mode: Fill mode passed to return_constant_color.
    :returns: None; chunk is modified in place.
    """
    if np.any(xrt > slide_dimensions['region_right']):
        constant_color = return_constant_color(chunk, pad_fill_mode)
        diff_r = np.min((slide_dimensions['region_right'] - xrt).astype(np.int64))
        chunk[:, diff_r:, :] = constant_color
    if np.any(ybt > slide_dimensions['region_bottom']):
        constant_color = return_constant_color(chunk, pad_fill_mode)
        diff_b = np.min((slide_dimensions['region_bottom'] - ybt).astype(np.int64))
        chunk[diff_b:, :, :] = constant_color

    return chunk


def pad_chunk_if_necessary(
    slide_dimensions: dict,
    chunk: np.ndarray,
    xlt: np.ndarray,
    xrt: np.ndarray,
    ytt: np.ndarray,
    ybt: np.ndarray,
    w: int,
    h: int,
    pad_mode: str = 'wsi_edge',
    pad_fill_mode: str = 'default',
):
    """Pad a chunk when it is smaller than the requested read window.

    :param slide_dimensions: Slide dimension metadata for the selected region.
    :param chunk: Chunk image array returned by the tile source.
    :param xlt: Left coordinates for requested tiles or regions.
    :param xrt: Right coordinates for requested tiles or regions.
    :param ytt: Top coordinates for requested tiles or regions.
    :param ybt: Bottom coordinates for requested tiles or regions.
    :param w: Desired output width.
    :param h: Desired output height.
    :param pad_mode: Padding placement mode.
    :param pad_fill_mode: Fill mode passed to return_constant_color.
    :returns: The padded chunk, or the original chunk if padding is unnecessary.
    """
    if chunk.shape[1] != w or chunk.shape[0] != h:
        out = chunk.copy()

        constant_color = return_constant_color(chunk, pad_fill_mode)

        l_dist = np.abs(np.min(xlt).astype(np.int64))
        t_dist = np.abs(np.min(ytt).astype(np.int64))

        r_dist = np.abs(slide_dimensions['region_right'] - np.max(xrt).astype(np.int64))
        b_dist = np.abs(slide_dimensions['region_bottom'] - np.max(ybt).astype(np.int64))

        # Based on pad mode choose how padding will be applied to image top, bottom, left and right
        if pad_mode == 'wsi_edge':
            top, bottom, left, right = return_needed_padding_wsi_edge(
                chunk, w, h, t_dist, b_dist, l_dist, r_dist,
            )
            out = pad_color(out, top, bottom, left, right, constant_color)
        elif pad_mode == 'equal':
            top, bottom, left, right = return_needed_padding_equal(chunk, w, h)
            out = pad_color(out, top, bottom, left, right, constant_color)
        else:
            msg = "Invalid pad_mode value. Must be 'wsi_edge' or 'equal'."
            raise ValueError(msg)

        return out

    return chunk


def pad_region_chunk(chunk: np.ndarray, xlo: list, yto: list, wo: list, ho: list):
    """Pad a region chunk to cover the requested region coordinates.

    :param chunk: Chunk image array returned by the tile source.
    :param xlo: Left offsets within the chunk.
    :param yto: Top offsets within the chunk.
    :param wo: Right offsets within the chunk.
    :param ho: Bottom offsets within the chunk.
    :returns: The padded chunk.
    """
    w = max(xlo) + max(wo)
    h = max(xlo) + max(ho)

    x_pad = w - chunk.shape[1]
    y_pad = h - chunk.shape[0]

    if x_pad < 0:
        x_pad = 0

    if y_pad < 0:
        y_pad = 0

    chunk = np.pad(chunk, ((0, y_pad), (0, x_pad), (0, 0)), mode='constant')

    return chunk
