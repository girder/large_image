import numpy as np

from large_image.tilesource.eager_utils.eager_read_args import (
    default_region_coords_and_target_scale_from_read_args,
    gen_read_args_for_tiles)
from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions


def test_gen_read_args_for_single_tile(datastore_svs_source):
    slide_dimensions = calculate_slide_dimensions(datastore_svs_source)
    n_possible_tiles = (
        slide_dimensions['tile_target_range_x'] * slide_dimensions['tile_target_range_y']
    )

    read_args = gen_read_args_for_tiles(
        n_possible_tiles,
        slide_dimensions,
        tiles=[[0, 0]],
        chunk_mult=2,
    )

    assert len(read_args) == 1
    assert read_args[0].shape == (1, 10)
    np.testing.assert_array_equal(read_args[0][0, 2:4], [0, 0])


def test_gen_read_args_edge_filters_tiles_outside_base_image(datastore_svs_source):
    slide_dimensions = calculate_slide_dimensions(datastore_svs_source)
    n_possible_tiles = (
        slide_dimensions['tile_target_range_x'] * slide_dimensions['tile_target_range_y']
    )
    out_of_bounds_col = slide_dimensions['tile_target_range_x']

    read_args = gen_read_args_for_tiles(
        n_possible_tiles,
        slide_dimensions,
        tiles=[[0, 0], [0, out_of_bounds_col]],
        edge=True,
        chunk_mult=2,
    )

    rows = np.concatenate(read_args)
    assert rows.shape[0] == 1
    np.testing.assert_array_equal(rows[0, 2:4], [0, 0])


def test_default_region_coords_and_target_scale_from_read_args():
    read_args = np.array(
        [
            [0, 0, 0, 0, 11, 29, 7, 31, 0.25, 0.50],
            [1, 2, 3, 4, 13, 37, 19, 43, 0.30, 0.60],
        ],
        dtype=np.float32,
    )
    slide_dimensions = {
        'tile_size': (64, 32),
        'scale_mode': 'mm',
        'target_mm_x': 0.50,
        'target_mm_y': 0.25,
        'conv_mm_x': 2.0,
        'conv_mm_y': 4.0,
    }

    (
        xlt,
        ytt,
        xrt,
        ybt,
        mm_x,
        mm_y,
        tile_size_dict,
        scale_dict,
        conv_mm_x,
        conv_mm_y,
    ) = default_region_coords_and_target_scale_from_read_args(read_args, slide_dimensions)

    np.testing.assert_array_equal(xlt, read_args[:, 6])
    np.testing.assert_array_equal(ytt, read_args[:, 4])
    np.testing.assert_array_equal(xrt, read_args[:, 7])
    np.testing.assert_array_equal(ybt, read_args[:, 5])
    np.testing.assert_array_equal(mm_x, read_args[:, 9])
    np.testing.assert_array_equal(mm_y, read_args[:, 8])
    assert tile_size_dict == {'width': 64, 'height': 32}
    assert scale_dict == {'mm_x': 0.50, 'mm_y': 0.25}
    assert conv_mm_x == 2.0
    assert conv_mm_y == 4.0

    slide_dimensions['_tile_size'] = {'width': 128, 'height': 256}
    slide_dimensions['_target_scale'] = {'magnification': 20}

    result = default_region_coords_and_target_scale_from_read_args(
        read_args,
        slide_dimensions,
        include_mm=False,
    )

    assert result[4] is None
    assert result[5] is None
    assert result[6] == {'width': 128, 'height': 256}
    assert result[7] == {'magnification': 20}
