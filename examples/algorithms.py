from scipy import ndimage
import numpy as np


def rgb2gray(rgb):
    return np.dot(rgb[..., :3], [0.2989, 0.5870, 0.1140])


def erode(data):
    gray = rgb2gray(data)
    binary = 1.0 * ((gray > 50) & (gray < 200))
    eroded = ndimage.binary_erosion(
        binary,
        structure=np.ones((30, 30)),
        border_value=1,
    )
    data[eroded == 0] = 0
    data[:, :, 3] = 255
    return data
