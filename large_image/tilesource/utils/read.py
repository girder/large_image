import numpy as np
import math
from pykdtree.kdtree import KDTree

def gen_read_args_complete_grid(sorted_tiles, chunk_mult):
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

def dense_chunks(sorted_in, used, points, chunks, chunk_size):
    tile_dict = {}
    tiles_count = []

    for i in range(sorted_in.shape[0]):
        if not used[i]:
            same_tiles = np.argwhere((points[:,0] == points[i,0]) & (points[:,1] == points[:,1])).flatten()
            tile_dict[f'{sorted_in[i, 0]}_{sorted_in[i, 1]}'] = sorted_in[same_tiles]
            tiles_count.append(same_tiles.shape[0])
            used[same_tiles] = True

    tiles_count = np.array(tiles_count)
    m = np.mean(tiles_count)
    me = np.median(tiles_count)
    s = np.std(tiles_count)
    ma = np.max(tiles_count)

    for k in tile_dict.keys():
        if tile_dict[k].shape[0] > chunk_size:
            chunk_clusters = np.array_split(tile_dict[k], chunk_size)
            for cluster in chunk_clusters:
                c = cluster.tolist()
                if len(c) > 0:
                    chunks.append(c)
        else:
            c = tile_dict[k].tolist()
            if len(c) > 0:
                chunks.append(c)

    return chunks

def sparse_chunks(sorted_in, used, points, tree, chunks, chunk_size, ok_chunk_size, k_mod):
    # Use while loop to handle cases where many desired regions are close/overlapping
    usage_count = 0
    while(usage_count < sorted_in.shape[0]):
        chunks = chunks_from_kd_tree(sorted_in, used, points, tree, chunks, chunk_size, ok_chunk_size, k_mod)
        usage_count = np.sum(used)

        if ok_chunk_size > 1:
            ok_chunk_size -= 1

        k_mod += 1

    return chunks

def gen_read_args_incomplete_grid(sorted_in, chunk_size):
    # todo: add documentation
    # todo: version for grouped by tiles
    # Spatial indexing for proximity-based grouping
    points = sorted_in[:, :2].astype(float)
    used = np.zeros(sorted_in.shape[0], dtype=bool)
    chunks = []

    tree = KDTree(points)
    k_mod = 1
    chunks = sparse_chunks(sorted_in, used, points, tree, chunks, chunk_size, k_mod)

    return chunks

def chunks_from_kd_tree(sorted_in, used, points, tree, chunks, chunk_size, k_mod=1):
    # todo: add documentation
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

def check_edge_condition(base_size_x, base_size_y, sorted_in, edge=False):
    '''
    :param base_size_x: The base image's size in the x dimension
    :param base_size_y: The base image's size in the y dimension
    :param sorted_in: The sorted regions or tiles to check for edges

    :return:
    '''
    if edge:
        condition = (sorted_in[:, 7] < base_size_x) & (sorted_in[:, 5] < base_size_y) & (sorted_in[:, 6] >= 0) & (sorted_in[:, 4] >= 0)
        sorted_out = sorted_in[condition]
        diff_from_edge = np.sum(~condition)
    else:
        sorted_out = sorted_in
        diff_from_edge = 0

    return sorted_out, diff_from_edge

def gen_read_args_for_regions(slide_dimensions, regions: np.ndarray, edge=False, chunk_mult=2):
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


def gen_read_args_for_tiles(n_possible_tiles, slide_dimensions, tiles, edge=False, chunk_mult=2):
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