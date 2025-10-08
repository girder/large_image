import numpy as np
from pykdtree.kdtree import KDTree
from typing import Union, List

def gen_read_args_complete_grid(sorted_tiles: np.ndarray, chunk_mult: int):
    # todo: add documentation
    # Calculate group indices using grid structure
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
    chunks = [list(chunk) for chunk in chunks]

    return chunks

def sparse_chunks(sorted_in: np.ndarray, used: np.ndarray, points: np.ndarray, tree: KDTree, chunks: List, chunk_size: int, k_mod: int = 1):
    # Use while loop to handle cases where many desired regions are close/overlapping
    usage_count = 0
    while(usage_count < sorted_in.shape[0]):
        chunks = chunks_from_kd_tree(sorted_in, used, points, tree, chunks, chunk_size, k_mod)
        usage_count = np.sum(used)

        if chunk_size > 1:
            chunk_size -= 1

        k_mod += 1

    return chunks

def gen_read_args_incomplete_grid(sorted_in: np.ndarray, chunk_size: int):
    """A function that generates read arguments for an incomplete grid.

    :param sorted_in: _description_
    :type sorted_in: np.ndarray
    :param chunk_size: _description_
    :type chunk_size: int
    :returns: A list of chunks.
    :rtype: list
    """

    points = sorted_in[:, :2].astype(float)
    used = np.zeros(sorted_in.shape[0], dtype=bool)
    chunks = []

    ok_chunk_size = int(chunk_size)

    tree = KDTree(points)
    k_mod = 1
    chunks = sparse_chunks(sorted_in, used, points, tree, chunks, ok_chunk_size, k_mod)

    return chunks

def chunks_from_kd_tree(sorted_in: np.ndarray, used: np.ndarray, points: np.ndarray, tree: KDTree, chunks: list, chunk_size: int, k_mod: int = 1):
    """A function that generates chunks from a kd tree.

    :param sorted_in: The sorted regions or tiles to check for edges
    :type sorted_in: np.ndarray
    :param used: The used regions or tiles
    :type used: np.ndarray
    :param points: The points to check for edges
    :type points: np.ndarray
    :param tree: The kd tree
    :type tree: KDTree
    :param chunks: The chunks to generate
    :type chunks: list
    :param chunk_size: The chunk size
    :type chunk_size: int
    :param k_mod: The k mod
    :type k_mod: int
    :returns: A sorted list of chunks.
    :rtype: _type_
    """

    # version for grouped by tiles
    chunk = []

    for i in range(sorted_in.shape[0]):
        if not used[i]:
            query_points = points[i:i + 1]
            _, neighbors = tree.query(query_points, k=chunk_size * k_mod)

            if not isinstance(neighbors, np.ndarray):
                neighbors = np.array(neighbors)

            # Always include the target point in the neighbors
            check = np.argwhere(neighbors[0] == i)
            if check.shape[0] == 0:
                possible_neighbors = np.append(np.array(i), neighbors[0])
            else:
                possible_neighbors = neighbors[0]

            not_used_neighbors = np.logical_not(used[possible_neighbors])
            values_neighbors = sorted_in[possible_neighbors]
            chunk = values_neighbors[not_used_neighbors]
            used_update_idxs = possible_neighbors[not_used_neighbors]

            if chunk.shape[0] > 0:
                used[used_update_idxs] = True
                chunk = chunk.tolist()

                chunks.append(chunk)

    return chunks

def check_edge_condition(base_size_x: int, base_size_y: int, sorted_in: np.ndarray, edge: bool = False):
    '''
    :param base_size_x: The base image's size in the x dimension
    :param base_size_y: The base image's size in the y dimension
    :param sorted_in: The sorted regions or tiles to check for edges

    :returns: A soreted list of chunks.
    '''
    if edge:
        condition = (sorted_in[:, 7] < base_size_x) & (sorted_in[:, 5] < base_size_y) & (sorted_in[:, 6] >= 0) & (sorted_in[:, 4] >= 0)
        sorted_out = sorted_in[condition]
        diff_from_edge = np.sum(~condition)
    else:
        sorted_out = sorted_in
        diff_from_edge = 0

    return sorted_out, diff_from_edge

def gen_read_args_for_regions(slide_dimensions: dict, regions: Union[list, np.ndarray], edge: bool = False, chunk_mult: int = 2):
    # todo: update documentation
    # todo: version for grouping regions by tile
    '''
    :param org_wsi_size_x: The original base image's size in the x dimension
    :param org_wsi_size_y: The original base image's size in the y dimension
    :param regions: A numpy array of regions to read defined as top, left, height, and width
    :return: read_args: A list of lists containing the chunked arguments for reading tiles in the form
    of center_y, center_x, top, bottom, left, right
    '''

    chunk_size = chunk_mult ** 2

    if isinstance(regions, list):
        regions = np.array(regions)

    if len(regions.shape) == 1:
        regions = np.expand_dims(regions, axis=0)

    # Calculate y_bottom, x_region, center_y and center_x
    yb = regions[:, 0] + regions[:, 2]
    xr = regions[:, 1] + regions[:, 3]
    center_y = (regions[:,0] + yb) / 2
    center_x = (regions[:,1] + xr) / 2
    org_tile_x = np.floor(center_x / slide_dimensions['base_tile_width'])
    org_tile_y = np.floor(center_y /slide_dimensions['base_tile_height'])

    # tile = np.column_stack((org_tile_y, org_tile_x))
    #
    # range_x = np.arange(0, slide_dimensions['base_tile_range_x'])
    # range_y = np.arange(0, slide_dimensions['base_tile_range_y'])
    #
    # x, y = np.meshgrid(range_x, range_y)
    #
    # possible_tiles = np.stack((x.flatten(), y.flatten()), axis=-1)

    # Regions of form (center_y, center_x, top, bottom, left, right)
    regions = np.column_stack((org_tile_y, org_tile_x, center_y, center_x, regions[:, 0], yb, regions[:, 1], xr))
    # Distance from 0, 0
    dist = center_y ** 2 + center_x ** 2 / 2
    # Sort regions by distance from 0, 0
    idx = np.argsort(dist)
    sorted_regions = regions[idx]

    # Use new sorted regions to determine if edges should b thrown out
    sorted_regions, diff_from_edge  = check_edge_condition(slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], sorted_regions, edge)

    # Determine if the grid is complete or incomplete even in the case of edges being removed
    chunks = gen_read_args_incomplete_grid(sorted_regions, chunk_size)

    return chunks


def gen_read_args_for_tiles(n_possible_tiles: int, slide_dimensions: dict, tiles: Union[list, np.ndarray], edge: bool = False, chunk_mult: int = 2):
    '''
    # todo: update documentation
    :param n_possible_tiles: The number of possible tiles in a complete grid made using the slide dimensions
    :param slide_dimensions: A dictionary containing slide dimensions
    :param tiles: A listing of tiles to read defined as (column, row)
    :param edge: A boolean indicating whether to throw out tiles that are out of bounds. False = keep all tiles is default.
    :param chunk_mult: A multiplier for the chunk size. Default is 2 which equals a chunk size of 4.
    :return: read_args: A list of lists containing the chunked arguments for reading tiles in the form
    of center_y, center_x, top, bottom, left, right
    '''

    chunk_size = chunk_mult ** 2

    # Sort tiles by row and column to maintain order
    sorted_tiles = sorted(tiles, key=lambda x: (x[0], x[1]))
    sorted_tiles = np.array(sorted_tiles, dtype=np.float32)

    # Make sure sorted tiles the right shape
    if len(sorted_tiles.shape) == 1:
        sorted_tiles = np.expand_dims(sorted_tiles, axis=0)

    # Calculate coordinates in the original image
    sx = sorted_tiles[:, 1] * slide_dimensions['tile_width_before_scaling']
    spx = sx + slide_dimensions['tile_width_before_scaling']
    sy = sorted_tiles[:, 0] * slide_dimensions['tile_height_before_scaling']
    spy = sy + slide_dimensions['tile_height_before_scaling']
    
    # Get tile with the most relevant region
    center_x = (sx + spx) / 2
    center_y = (sy + spy) / 2
    org_tile_x = np.floor(center_x / slide_dimensions['base_tile_width'])
    org_tile_y = np.floor(center_y / slide_dimensions['base_tile_height'])
    

    # Combine into the sorted_tiles array
    sorted_tiles = np.column_stack((org_tile_y, org_tile_x, sorted_tiles, sy, spy, sx, spx))

    # Keep track of whether edges are thrown out, if thrown out they can still form a complete grid
    diff_from_edge = 0

    # If edge is True, remove tiles that are out of bounds of the original image
    sorted_tiles, diff_from_edge = check_edge_condition(slide_dimensions['base_size_x'], slide_dimensions['base_size_y'], sorted_tiles, edge)

    # Determine if the grid is complete or incomplete even in the case of edges being removed
    if (sorted_tiles.shape[0] + diff_from_edge) == n_possible_tiles:
        chunks = gen_read_args_complete_grid(sorted_tiles, chunk_mult)
    else:
        chunks = gen_read_args_incomplete_grid(sorted_tiles, chunk_size)

    return chunks