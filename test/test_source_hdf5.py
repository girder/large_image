import pathlib
import random
import tempfile

import numpy

import large_image

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
    [0, 1],
    [0, 255],
    [0, 65535],
    [-1, 1]
]

max_tile_size = 100
tile_overlap_ratio = 0.5


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
    mask = numpy.random.randint(2, size=tile_shape[:-1])
    return (tile, mask)


def frame_with_zeros(data, desired_size, start_location=[]):
    if len(desired_size) == 0:
        return data
    if len(start_location) == 0:
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


def testImageGeneration():
    source = large_image.new()
    tile_grid = [
        int(random.randint(*possible_axes['x'])),
        int(random.randint(*possible_axes['y']))
    ]
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
    for x in range(tile_grid[0]):
        for y in range(tile_grid[1]):
            start_location = [
                int(x * max_tile_size * tile_overlap_ratio),
                int(y * max_tile_size * tile_overlap_ratio)
            ]
            tile, mask = random_tile(data_range)
            tile_shape = tile.shape
            source.addTile(tile, *start_location, mask=mask)

            tile.transpose(1, 0, *range(2, len(tile.shape)))
            mask.transpose(1, 0, *range(2, len(mask.shape)))
            start_location.reverse()

            # print(f'add {tile_shape} data at {start_location} with mask')
            # print(mask)
            far_x = start_location[0] + tile_shape[0]
            far_y = start_location[1] + tile_shape[1]
            if far_x > max_x:
                max_x = far_x
            if far_y > max_y:
                max_y = far_y

            framed_tile = numpy.array(frame_with_zeros(
                tile,
                expected.shape,
                start_location=start_location
            ))
            framed_mask = numpy.array(frame_with_zeros(
                mask.repeat(tile_shape[-1], -1).reshape(tile_shape),
                expected.shape,
                start_location=start_location
            ))

            numpy.putmask(expected, framed_mask, framed_tile)

    # if color is not all zeros, apply full alpha value to it
    expected = numpy.apply_along_axis(
        lambda color: [*color[:3], 255] if color.any() else color, -1,
        expected
    )
    # trim unused space
    expected = expected[:max_x, :max_y]

    with tempfile.TemporaryDirectory() as tmp_dir:
        # TODO: make destination use mdf5 extension
        destination = pathlib.Path(tmp_dir, 'sample.tiff')
        source.write(destination, lossy=False)
        result, _ = source.getRegion(format='numpy')
        result.transpose(1, 0, *range(2, len(result.shape)))

        result = result.round(2)
        expected = expected.round(2)

        assert numpy.array_equal(result, expected)
        print(f'Success; result matrix {result.shape} equals expected matrix {expected.shape}.')


testImageGeneration()
