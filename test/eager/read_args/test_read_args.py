from test.datastore import datastore

# Should still work even if one tile provided
import large_image
from large_image.tilesource.eager_utils.eager_read_args import gen_read_args_for_tiles
from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions

test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')

source = large_image.open(test_file)

slide_dimensions = calculate_slide_dimensions(source)

n_possible_tiles = slide_dimensions['tile_target_range_x'] * slide_dimensions['tile_target_range_y']

read_args = gen_read_args_for_tiles(
    n_possible_tiles,
    slide_dimensions,
    tiles=[[0, 0]],
    chunk_mult=2,
)

print(read_args)
