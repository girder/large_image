"""Read argument planning helpers for eager tile and region batches."""

from typing import Any, Dict, List, Optional, Union

import numpy as np
from pykdtree.kdtree import KDTree


def gen_read_args_complete_grid(sorted_tiles: np.ndarray, chunk_mult: int):
    # todo: add documentation
    # Calculate group indices using grid structure
    """Group tile read arguments for a complete rectangular grid.

    :param sorted_tiles: Tile read argument array sorted by tile row and column.
    :param chunk_mult: Width and height, in tiles, of each grouped read chunk.
    :returns: A list of numpy arrays, one per read chunk.
    """
    group_rows = sorted_tiles[:, 0] // chunk_mult
    group_cols = sorted_tiles[:, 1] // chunk_mult

    # Create compound group identifier
    group_ids = group_rows * (np.max(group_cols) + 1) + group_cols

    # Sort by group ID while preserving row-major order
    sort_idx = np.lexsort((sorted_tiles[:, 1], group_ids))
    sorted_tiles = sorted_tiles[sort_idx]
    group_ids = group_ids[sort_idx]

    # Split into chunks using group boundaries
    split_indices = np.where(np.diff(group_ids) != 0)[0] + 1
    chunks = np.split(sorted_tiles, split_indices)
    chunks = [np.array(chunk) for chunk in chunks]

    return chunks


def sparse_chunks(
    sorted_in: np.ndarray,
    used: np.ndarray,
    points: np.ndarray,
    tree: KDTree,
    chunks: List,
    chunk_size: int,
    k_mod: int = 1,
):
    # Use while loop to handle cases where many desired regions are close/overlapping
    """Build read chunks for sparse or incomplete tile and region grids.

    :param sorted_in: Sorted tile or region read argument array.
    :param used: Boolean mask tracking rows already assigned to a chunk.
    :param points: Coordinate points used for nearest-neighbor grouping.
    :param tree: KD-tree built from points.
    :param chunks: Existing list of chunks to append to.
    :param chunk_size: Target number of read arguments per chunk.
    :param k_mod: Multiplier used when widening nearest-neighbor searches.
    :returns: The updated list of read argument chunks.
    """
    usage_count = 0
    while usage_count < sorted_in.shape[0]:
        chunks = chunks_from_kd_tree(sorted_in, used, points, tree, chunks, chunk_size, k_mod)
        usage_count = np.sum(used)

        if chunk_size > 1:
            chunk_size -= 1

        k_mod += 1

    return chunks


def gen_read_args_incomplete_grid(sorted_in: np.ndarray, chunk_size: int):
    """Generate read argument chunks for a sparse or incomplete grid.

    :param sorted_in: Sorted tile or region read argument array.
    :param chunk_size: Target number of read arguments per chunk.
    :returns: A list of numpy arrays, one per read chunk.
    """
    points = sorted_in[:, :2].astype(float)
    used = np.zeros(sorted_in.shape[0], dtype=bool)
    chunks = []

    ok_chunk_size = int(chunk_size)

    tree = KDTree(points)
    k_mod = 1
    chunks = sparse_chunks(sorted_in, used, points, tree, chunks, ok_chunk_size, k_mod)

    return chunks


def chunks_from_kd_tree(
    sorted_in: np.ndarray,
    used: np.ndarray,
    points: np.ndarray,
    tree: KDTree,
    chunks: list,
    chunk_size: int,
    k_mod: int = 1,
):
    """Append unused nearest-neighbor read arguments to sparse chunks.

    :param sorted_in: Sorted tile or region read argument array.
    :param used: Boolean mask tracking rows already assigned to a chunk.
    :param points: Coordinate points used for nearest-neighbor grouping.
    :param tree: KD-tree built from points.
    :param chunks: Existing list of chunks to append to.
    :param chunk_size: Target number of read arguments per chunk.
    :param k_mod: Multiplier used when widening nearest-neighbor searches.
    :returns: The updated list of read argument chunks.
    """
    # version for grouped by tiles
    chunk = []

    for i in range(sorted_in.shape[0]):
        if not used[i]:
            query_points = points[i: i + 1]
            _, neighbors = tree.query(query_points, k=chunk_size * k_mod)

            if not isinstance(neighbors, np.ndarray):
                neighbors = np.array(neighbors)

            # Always include the target point in the neighbors
            check = np.argwhere(neighbors[0] == i)
            if check.shape[0] == 0:
                possible_neighbors = np.append(np.array(i), neighbors[0])
            else:
                possible_neighbors = neighbors[0]

            # Fix for case where the amount of read arguments is less the pykdtree k
            # parameter (chunk_size * k_mod)
            possible_neighbors = possible_neighbors[possible_neighbors < sorted_in.shape[0]]

            not_used_neighbors = np.logical_not(used[possible_neighbors])
            values_neighbors = sorted_in[possible_neighbors]
            chunk = values_neighbors[not_used_neighbors]
            used_update_idxs = possible_neighbors[not_used_neighbors]

            if chunk.shape[0] > 0:
                used[used_update_idxs] = True
                # chunk = chunk.tolist()

                chunks.append(chunk)

    return chunks


def check_edge_condition(
    base_size_x: int, base_size_y: int, sorted_in: np.ndarray, edge: bool = False,
):
    """Optionally discard read arguments that cross image boundaries.

    :param base_size_x: Base image width in pixels.
    :param base_size_y: Base image height in pixels.
    :param sorted_in: Sorted tile or region read argument array.
    :param edge: If True, discard entries that extend beyond the base image.
    :returns: A tuple of filtered read arguments and the number discarded.
    """
    if edge:
        condition = (
            (sorted_in[:, 7] < base_size_x) &
            (sorted_in[:, 5] < base_size_y) &
            (sorted_in[:, 6] >= 0) &
            (sorted_in[:, 4] >= 0)
        )
        sorted_out = sorted_in[condition]
        diff_from_edge = np.sum(~condition)
    else:
        sorted_out = sorted_in
        diff_from_edge = 0

    return sorted_out, diff_from_edge


def gen_read_args_for_regions(
    slide_dimensions: dict,
    regions: Union[list, np.ndarray],
    edge: bool = False,
    chunk_mult: int = 2,
):
    # todo: update documentation
    # todo: version for grouping regions by tile
    """Generate grouped read arguments for explicit output regions.

    :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
    :param regions: Regions in top, left, height, width order.
    :param edge: If True, discard regions that extend beyond the base image.
    :param chunk_mult: Chunk side length multiplier; chunk size is chunk_mult squared.
    :returns: A list of numpy arrays containing grouped region read arguments.
    """
    chunk_size = chunk_mult**2

    if isinstance(regions, list):
        regions = np.array(regions)

    if len(regions.shape) == 1:
        regions = np.expand_dims(regions, axis=0)

    # Calculate y_bottom, x_region, center_y and center_x
    yb = regions[:, 0] + regions[:, 2]
    xr = regions[:, 1] + regions[:, 3]
    center_y = (regions[:, 0] + yb) / 2
    center_x = (regions[:, 1] + xr) / 2
    org_tile_x = np.floor(center_x / slide_dimensions['base_tile_width'])
    org_tile_y = np.floor(center_y / slide_dimensions['base_tile_height'])

    # tile = np.column_stack((org_tile_y, org_tile_x))
    #
    # range_x = np.arange(0, slide_dimensions['base_tile_range_x'])
    # range_y = np.arange(0, slide_dimensions['base_tile_range_y'])
    #
    # x, y = np.meshgrid(range_x, range_y)
    #
    # possible_tiles = np.stack((x.flatten(), y.flatten()), axis=-1)

    mm_y = np.full(regions.shape[0], slide_dimensions['target_mm_y'])
    mm_x = np.full(regions.shape[0], slide_dimensions['target_mm_x'])

    # Regions of form (center_y, center_x, top, bottom, left, right)
    regions = np.column_stack(
        (
            org_tile_y,
            org_tile_x,
            center_y,
            center_x,
            regions[:, 0],
            yb,
            regions[:, 1],
            xr,
            mm_y,
            mm_x,
        ),
    ).astype(np.float32)
    # Distance from 0, 0
    dist = (center_y**2 + center_x**2) ** 0.5
    # Sort regions by distance from 0, 0
    idx = np.argsort(dist)
    sorted_regions = regions[idx]

    # Use new sorted regions to determine if edges should b thrown out
    sorted_regions, diff_from_edge = check_edge_condition(
        slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], sorted_regions, edge,
    )

    # Determine if the grid is complete or incomplete even in the case of edges being removed
    chunks = gen_read_args_incomplete_grid(sorted_regions, chunk_size)

    return chunks


def gen_read_args_for_tiles(
    n_possible_tiles: int,
    slide_dimensions: dict,
    tiles: Union[list, np.ndarray],
    edge: bool = False,
    chunk_mult: int = 2,
    region: Optional[Dict[str, Any]] = None,
):
    """Generate grouped read arguments for output tiles.

    :param n_possible_tiles: Number of tiles in the full target grid.
    :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
    :param tiles: Tile indexes in row, column order.
    :param edge: If True, discard tiles that extend beyond the base image.
    :param chunk_mult: Chunk side length multiplier; chunk size is chunk_mult squared.
    :param region: Optional region used to clip tile coordinates to region bounds.
    :returns: A list of numpy arrays containing grouped tile read arguments.
    """
    chunk_size = chunk_mult**2

    # Sort tiles by row and column to maintain order
    sorted_tiles = sorted(tiles, key=lambda x: (x[0], x[1]))
    sorted_tiles = np.array(sorted_tiles, dtype=np.float32)

    # Make sure sorted tiles the right shape
    if len(sorted_tiles.shape) == 1:
        sorted_tiles = np.expand_dims(sorted_tiles, axis=0)

    # Calculate coordinates in the original image
    # Use rounding to avoid floating point precision issues
    sx = np.round(
        sorted_tiles[:, 1] * slide_dimensions['tile_width_before_scaling'] +
        slide_dimensions['region_left'],
        decimals=0,
    )
    spx = np.round(sx + slide_dimensions['tile_width_before_scaling'], decimals=0)
    sy = np.round(
        sorted_tiles[:, 0] * slide_dimensions['tile_height_before_scaling'] +
        slide_dimensions['region_top'],
        decimals=0,
    )
    spy = np.round(sy + slide_dimensions['tile_height_before_scaling'], decimals=0)

    mm_x = np.full(sorted_tiles.shape[0], slide_dimensions['target_mm_x'])
    mm_y = np.full(sorted_tiles.shape[0], slide_dimensions['target_mm_y'])

    if region is not None:
        spx[spx > slide_dimensions['region_right']] = slide_dimensions['region_right']
        spy[spy > slide_dimensions['region_bottom']] = slide_dimensions['region_bottom']

    # Get tile with the most relevant region
    center_x = (sx + spx) / 2
    center_y = (sy + spy) / 2
    org_tile_x = np.floor(center_x / slide_dimensions['base_tile_width'])
    org_tile_y = np.floor(center_y / slide_dimensions['base_tile_height'])

    # Combine into the sorted_tiles array
    sorted_tiles = np.column_stack(
        (org_tile_y, org_tile_x, sorted_tiles, sy, spy, sx, spx, mm_y, mm_x),
    ).astype(np.float32)

    # Keep track of whether edges are thrown out, if thrown out they can still form a complete grid
    diff_from_edge = 0

    # If edge is True, remove tiles that are out of bounds of the original image
    sorted_tiles, diff_from_edge = check_edge_condition(
        slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], sorted_tiles, edge,
    )

    # Determine if the grid is complete or incomplete even in the case of edges being removed
    if (sorted_tiles.shape[0] + diff_from_edge) == n_possible_tiles:
        chunks = gen_read_args_complete_grid(sorted_tiles, chunk_mult)
    else:
        chunks = gen_read_args_incomplete_grid(sorted_tiles, chunk_size)

    return chunks


def default_region_coords_and_target_scale_from_read_args(
    read_kwargs: np.ndarray,
    slide_dimensions: dict,
    include_mm: bool = True,
):
    """Extract read coordinates and target scale from read arguments.

    :param read_kwargs: Read argument array produced by eager read argument generators.
    :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
    :param include_mm: If True, include per-read mm scale columns in the output.
    :returns: Coordinates, mm metadata, tile size, target scale, and conversion factors.
    """
    xlt = read_kwargs[:, 6]
    ytt = read_kwargs[:, 4]
    xrt = read_kwargs[:, 7]
    ybt = read_kwargs[:, 5]

    if include_mm:
        mm_x = read_kwargs[:, 9]
        mm_y = read_kwargs[:, 8]
    else:
        mm_x = None
        mm_y = None

    scale_dict = slide_dimensions.get('_target_scale')
    tile_size_dict = slide_dimensions.get('_tile_size')

    if tile_size_dict is None:
        tile_size_dict = dict(
            width=slide_dimensions['tile_size'][0], height=slide_dimensions['tile_size'][1],
        )

    if scale_dict is None:
        if slide_dimensions['scale_mode'] == 'mm':
            scale_dict = dict(
                mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y'],
            )
        elif slide_dimensions['scale_mode'] == 'mag':
            scale_dict = dict(magnification=slide_dimensions['target_magnification'])
        else:
            msg = 'Invalid scale mode'
            raise ValueError(msg)

    return (
        xlt,
        ytt,
        xrt,
        ybt,
        mm_x,
        mm_y,
        tile_size_dict,
        scale_dict,
        slide_dimensions['conv_mm_x'],
        slide_dimensions['conv_mm_y'],
    )
