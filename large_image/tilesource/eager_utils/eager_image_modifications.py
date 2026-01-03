import math
import numpy as np

def padding(array: np.ndarray, xx: int, yy: int):
    """
    :param array: numpy array
    :param xx: desired height
    :param yy: desirex width
    :return: padded array
    """

    h = array.shape[0]
    w = array.shape[1]
    c = array.shape[2]

    a = (xx - h) // 2
    aa = xx - a - h

    b = (yy - w) // 2
    bb = yy - b - w

    return np.pad(array, pad_width=((a, aa), (b, bb), (0, 0)), mode='constant')

def rgba2rgb(img_rgba: np.ndarray, background: tuple = (255, 255, 255)):
    """A function that converts a rgba image to a rgb image.
    :param img_rgba: The rgba image
    :type img_rgba: np.ndarray
    :param background: The background color
    :type background: tuple
    :returns: The rgb image
    :rtype: np.ndarray
    """
    row, col, ch = img_rgba.shape

    if ch == 3:
        return img_rgba

    assert ch == 4, 'RGBA image has 4 channels.'

    rgb = np.zeros( (row, col, 3), dtype=np.float32 )
    r, g, b, a = img_rgba[:, :, 0], img_rgba[:, :, 1], img_rgba[:, :, 2], img_rgba[:, :, 3]

    a = np.asarray( a, dtype=np.float32 ) / 255.0

    R, G, B = background

    rgb[:,:,0] = r * a + (1.0 - a) * R
    rgb[:,:,1] = g * a + (1.0 - a) * G
    rgb[:,:,2] = b * a + (1.0 - a) * B

    return np.asarray(rgb, dtype=np.uint8)

def pad_color(image: np.ndarray, top: int, bottom: int, left: int, right: int, color: tuple):
    r = np.pad(image[:,:,0], ((top, bottom), (left, right)), mode='constant', constant_values=color[0])
    g = np.pad(image[:,:,1], ((top, bottom), (left, right)), mode='constant', constant_values=color[1])
    b = np.pad(image[:,:,2], ((top, bottom), (left, right)), mode='constant', constant_values=color[2])
    return np.stack((r, g, b), axis=-1)

def pad_tile(tile: np.ndarray, w: int, h: int, pad_mode: str, pad_fill_mode: str):
    out = tile.copy()

    constant_color = return_constant_color(tile, pad_fill_mode)

    # Based on pad mode choose how padding will be applied to image top, bottom, left and right
    if pad_mode == 'wsi_edge':
        raise NotImplementedError("pad_mode 'wsi_edge' is not implemented for tile padding.")
    elif pad_mode == 'equal':
        top, bottom, left, right = return_needed_padding_equal(tile, w, h)
        out = pad_color(out, top, bottom, left, right, constant_color)
    else:
        raise ValueError("Invalid pad_mode value. Must be 'wsi_edge' or 'equal'.")

    return out

def return_constant_color(image: np.ndarray, pad_fill_mode: str):
    # Determine the color that will be used for paadding
    if image.shape[0] == 0 or image.shape[1] == 0:
        return (0, 0, 0)
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
    elif isinstance(pad_fill_mode, int):
        constant_color = (pad_fill_mode, pad_fill_mode, pad_fill_mode)
    elif isinstance(pad_fill_mode, tuple):
        constant_color = pad_fill_mode
    else:
        raise ValueError("Invalid pad_fill_mode.  Must be 'default', 'max', int or tuple.")

    return constant_color

def return_needed_padding_wsi_edge(image: np.ndarray, w: int, h: int, t_dist: int, b_dist: int, l_dist: int, r_dist: int):
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

def return_needed_padding_equal(image: np.ndarray, w: int, h: int):
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


def pad_chunk_if_necessary(base_size_x: int,  base_size_y: int, chunk: np.ndarray, xlt: np.ndarray, xrt: np.ndarray, ytt: np.ndarray, ybt: np.ndarray, w: int, h: int, pad_mode: str = 'wsi_edge', pad_fill_mode: str = 'default'):
    if chunk.shape[0] != h or chunk.shape[1] != w:
        out = chunk.copy()

        constant_color = return_constant_color(chunk, pad_fill_mode)

        l_dist = np.abs(np.min(xlt).astype(np.int64))
        t_dist = np.abs(np.min(ytt).astype(np.int64))
        r_dist = np.abs(base_size_x - np.max(xrt).astype(np.int64))
        b_dist = np.abs(base_size_y - np.max(ybt).astype(np.int64))

        # Based on pad mode choose how padding will be applied to image top, bottom, left and right
        if pad_mode == 'wsi_edge':
            top, bottom, left, right = return_needed_padding_wsi_edge(chunk, w, h, t_dist, b_dist, l_dist, r_dist)
            out = pad_color(out, top, bottom, left, right, constant_color)
        elif pad_mode == 'equal':
            top, bottom, left, right = return_needed_padding_equal(chunk, w, h)
            out = pad_color(out, top, bottom, left, right, constant_color)
        else:
            raise ValueError("Invalid pad_mode value. Must be 'wsi_edge' or 'equal'.")

        return out
    else:
        return chunk

def pad_region_chunk(chunk: np.ndarray, xlo: list, yto: list, wo: list, ho: list):
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