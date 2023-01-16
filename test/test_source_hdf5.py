import pathlib
import random
import tempfile

import numpy
import pytest

import large_image
from large_image.cache_util import cachesClear

possible_axes = {
    'x': [1, 10],
    'y': [1, 10],
    'c': [1, 100],
    'z': [1, 100],
    't': [1, 100],
    'p': [1, 100],
    'q': [1, 100],
    's': [3, 3],
}

include_axes = {
    'c': False,
    'z': False,
    't': False,
    'p': False,
    'q': False,
}

possible_data_ranges = [
    [0, 1, 2, float],
    [0, 1, 2, numpy.float16],
    [0, 1, 2, numpy.float32],
    [0, 1, 2, numpy.float64],
    [0, 2**8, -1, numpy.uint8],
    [0, 2**8, -1, float],
    [0, 2**8, -1, int],
    [0, 2**16, -2, numpy.uint16],
    [0, 2**16, -2, float],
    [0, 2**32, -4, int],
    [-2**7, 2**7, -1, numpy.int8],
    [-2**7, 2**7, -1, float],
    [-2**7, 2**7, -1, int],
    [-2**15, 2**15, -2, numpy.int16],
    [-2**15, 2**15, -2, float],
    [-2**15, 2**15, -2, int],
    [-2**31, 2**31, -4, numpy.int32],
    [-2**31, 2**31, -4, float],
    [-2**31, 2**31, -4, int],
    [-1, 1, 2, float],
    [-1, 1, 2, numpy.float16],
    [-1, 1, 2, numpy.float32],
    [-1, 1, 2, numpy.float64],
]

max_tile_size = 100
tile_overlap_ratio = 0.5


# https://stackoverflow.com/questions/18915378/rounding-to-significant-figures-in-numpy
def signif(x, minval, maxval, digits):
    if x == 0:
        return 0
    return max(min(round(x, digits), max(1, maxval - 1)), minval)


def get_dims(x, y, s, max=False):
    tile_shape = [x, y]
    for axis_name, include in include_axes.items():
        if include:
            axis_min_max = possible_axes[axis_name]
            if max:
                tile_shape.append(axis_min_max[1])
            else:
                tile_shape.append(random.randint(*axis_min_max))
    # s is last axis
    tile_shape.append(s)
    return tile_shape


def random_tile(data_range):
    tile_shape = get_dims(
        random.randint(1, max_tile_size),
        random.randint(1, max_tile_size),
        random.randint(*possible_axes['s']),
        include_axes
    )
    tile = numpy.random.rand(*tile_shape)
    tile *= (data_range[1] - data_range[0])
    tile += data_range[0]
    tile = tile.astype(data_range[3])  # apply dtype
    mask = numpy.random.randint(2, size=tile_shape[:-1])
    return (tile, mask)


def frame_with_zeros(data, desired_size, start_location=None):
    if len(desired_size) == 0:
        return data
    if not start_location or len(start_location) == 0:
        start_location = [0]
    framed = [
        frame_with_zeros(
            data[x - start_location[0]],
            desired_size[1:],
            start_location=start_location[1:]
        )
        if (  # frame with zeros if x>=start and x<start+length
            x >= start_location[0] and
            x < data.shape[0] + start_location[0]
        )  # fill with zeros otherwise
        else numpy.zeros(desired_size[1:])
        for x in range(desired_size[0])
    ]
    return numpy.array(framed)


@pytest.mark.parametrize('data_range', possible_data_ranges)
def testImageGeneration(data_range):
    source = large_image.new()
    tile_grid = [
        int(random.randint(*possible_axes['x'])),
        int(random.randint(*possible_axes['y']))
    ]
    if data_range is None:
        data_range = random.choice(possible_data_ranges)

    # create comparison matrix at max size and fill with zeros
    expected_shape = get_dims(
        tile_grid[1] * max_tile_size, tile_grid[0] * max_tile_size, 4, True
    )
    expected = numpy.ndarray(expected_shape)
    expected.fill(0)
    max_x, max_y = 0, 0

    print(
        f'placing {tile_grid[0] * tile_grid[1]} random tiles in available space: {expected_shape}')
    print('tile overlap ratio:', tile_overlap_ratio)
    print('data range:', data_range)
    for x in range(tile_grid[0]):
        for y in range(tile_grid[1]):
            start_location = [
                int(x * max_tile_size * tile_overlap_ratio),
                int(y * max_tile_size * tile_overlap_ratio)
            ]
            tile, mask = random_tile(data_range)
            tile_shape = tile.shape
            source.addTile(tile, *start_location, mask=mask)
            max_x = max(max_x, start_location[1] + tile_shape[0])
            max_y = max(max_y, start_location[0] + tile_shape[1])

            framed_tile = numpy.array(frame_with_zeros(
                tile,
                expected.shape,
                start_location=start_location[::-1]
            ))
            framed_mask = numpy.array(frame_with_zeros(
                mask.repeat(tile_shape[-1], -1).reshape(tile_shape),
                expected.shape,
                start_location=start_location[::-1]
            ))

            numpy.putmask(expected, framed_mask, framed_tile)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # TODO: make destination use mdf5 extension
        destination = pathlib.Path(tmp_dir, 'sample.tiff')
        source.write(destination, lossy=False)
        result, _ = source.getRegion(format='numpy')

    # trim unused space from expected
    expected = expected[:max_x, :max_y]

    # round to specified precision
    precision_vector = numpy.vectorize(signif)
    expected = precision_vector(expected, data_range[0], data_range[1], data_range[2])
    result = precision_vector(result, data_range[0], data_range[1], data_range[2])

    # ignore alpha values for now
    expected = expected.take(indices=range(0, -1), axis=-1)
    result = result.take(indices=range(0, -1), axis=-1)

    # For debugging
    # difference = numpy.subtract(result, expected)
    # print(difference)
    # print(expected[numpy.nonzero(difference)])
    # print(result[numpy.nonzero(difference)])

    assert numpy.array_equal(result, expected)
    # resultFromFile, _ = large_image.open(destination).getRegion(format='numpy')
    # print(resultFromFile.shape, result.shape)
    # assert numpy.array_equal(result, resultFromFile)
    print(f'Success; result matrix {result.shape} equals expected matrix {expected.shape}.')

    source = None
    cachesClear()


if __name__ == '__main__':
    testImageGeneration(None)
