import numpy as np


def test_gen_read_args_for_single_tile(datastore_svs_source):
    from large_image.tilesource.eager_utils.eager_read_args import gen_read_args_for_tiles
    from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions

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
    from large_image.tilesource.eager_utils.eager_read_args import gen_read_args_for_tiles
    from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions

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
