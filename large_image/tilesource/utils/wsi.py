import math
import large_image
from large_image import constants
import numpy as np
from ..utils.image import rgba2rgb, padding

def get_smallest_bounding_box(roi):
    '''

    :param points: numpy array featuring points from an annotation given coordinates from an entire slide
    :return: ROI from the whole slide image (x1, y1), (x2, y2)
    '''
    points = np.array(roi['points'])[:, :2]
    roi_x1, roi_y1 = points.min(axis=0)
    roi_x2, roi_y2 = points.max(axis=0)
    return (roi_x1, roi_y1), (roi_x2, roi_y2)

def return_tile_slides_meeting_area_threshold(mask, slide_dim, tiles, area_threshold=0.25, threshold_mask=100):
    '''
    A function that uses a mask generated from a whole slide image thumbnail to determine which tiles have enough content
    for being included in a set of evaluated tiles given a list of all possible tiles at a specific desired scaling.
    :param mask: An mask image derived from the whole slide image thumbnail
    :param slide_dim: A slide dimensions dictionary defining the image properties of a desired image and its' output
    :param area_threshold: A threshold of area to consider a tile useful.
    :param threshold_mask: A intensity of the pixel value in the image mask to determine if a tile is useful or not
    :return: Returns tiles in the form [(y, x)] where y is the row in the image and x is the column
    '''

    return_tiles = []

    if np.max(mask) == 1:
        threshold_mask = 0

    for tile in tiles:
        mask_patch = get_patch_from_mask_for_tile(mask, slide_dim['base_size_x'], slide_dim['base_size_y'], slide_dim['tile_width_before_scaling'], slide_dim['tile_height_before_scaling'], tile)
        if np.sum(mask_patch > threshold_mask) > np.size(mask_patch) * area_threshold:
            return_tiles.append(tile)

    return return_tiles

def return_relevant_tile_indexes_for_slide_dim(range_x: int, range_y: int, overlap: float=0):
    '''
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    and returns a list of possible tiles given a desired output scaling.
    :param range_x: The range of the x dimension of the image
    :param range_y: The range of the y dimension of the image
    :param overlap: The amount of overlap between tiles.  A float from 0 to 1.0
    :return: a list of tiles in the form of [(y, x)]
    '''
    slide_tiles = []

    if overlap < 0. or overlap >= 1.0:
        raise ValueError("Valid overlap range: 0 <= overlap < 1.0")

    offset = 1 - overlap

    range_x = np.arange(0, range_x, offset)
    range_y = np.arange(0, range_y, offset)

    # tiles in form y (column), x (row)
    for i in range_x:
        for j in range_y:
            slide_tiles.append((j, i))

    return slide_tiles

def get_patch_from_mask_for_tile(mask: np.ndarray, base_size_x: int, base_size_y: int, tile_width_before_scaling: int, tile_height_before_scaling: int, tile: list):
    tile_y, tile_x = tile

    mask_size_x = mask.shape[1]
    mask_size_y = mask.shape[0]

    conv_x_base_to_mask = mask_size_x / base_size_x
    conv_y_base_to_mask = mask_size_y / base_size_y

    bound_x1 = math.floor(conv_x_base_to_mask * tile_x * tile_width_before_scaling)
    bound_x2 = math.ceil(conv_x_base_to_mask * (tile_x + 1) * tile_width_before_scaling)

    bound_y1 = math.floor(conv_y_base_to_mask * tile_y * tile_height_before_scaling)
    bound_y2 = math.ceil(conv_y_base_to_mask * (tile_y + 1) * tile_height_before_scaling)

    patch_mask = mask[bound_y1:bound_y2,bound_x1:bound_x2]

    return patch_mask

def get_base_mm_from_meta(source_meta):
    mm_x = None
    mm_y = None

    if 'mm_x' in source_meta and source_meta['mm_x'] is not None:
        mm_x = source_meta['mm_x']
    if 'mm_y' in source_meta and source_meta['mm_y'] is not None:
        mm_y = source_meta['mm_y']

    if mm_x is None or mm_y is None:
        raise Exception("Tile source does not define pixel size in mm")
    else:
        return (mm_x, mm_y)

def return_target_scaling_feature(feature):
    out = None
    if isinstance(feature, str):
        out = float(feature)
    elif isinstance(feature, int):
        out = float(feature)
    elif isinstance(feature, float):
        out = float(feature)
    return out

def generate_assumptions_for_x_y_given_mag(x, y, z):
    if z is None:
        raise Exception("Unable to assume using magnification is not defined")
    # Prefer scaling using base dimensions
    else:
        if x is None:
            x = 0.00025 * z / 40
        if y is None:
            y = 0.00025 * z / 40

        if x is None or y is None or z is None:
            raise Exception("Assumption for dimensions failed")

    return x, y, z

def get_scaling_values_from_meta(source_meta, mode, target_scale):
    '''
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    :param source_meta: A large image source metadata.
    :param mode: The mode used for scaling. Should be either 'mag' or 'mm'.
    :param target_scale: The desired target scale as an int for magnification in 'mag' mode or a tuple of (x, y) in 'mm' mode.
    :return: A dictionary defining scaling.
    '''
    if mode is not None:
        mode = mode.lower()
        mode_split = mode.split('.')
        mode = mode_split[0]
        mode_modifier = None

    if len(mode_split) > 1:
        mode_modifier = mode_split[1]

    # Define none for both target (i, j, k) and base (x, y, z) values
    i, j, k, x, y, z = None, None, None, None, None, None

    if mode == 'mag':
        if target_scale is None:
            k = source_meta['magnification']
            z = source_meta['magnification']
            i, j = get_base_mm_from_meta(source_meta)
            x, y = i, j
        elif isinstance(target_scale, int) or isinstance(target_scale, float):
            k = return_target_scaling_feature(target_scale)
            z = source_meta['magnification']

            if k is None:
                raise Exception("Unable to determine a target magnification with the provided value")

            try:
                x, y = get_base_mm_from_meta(source_meta)
                i = x * (z / k)
                j = y * (z / k)
            except:
                raise UserWarning("Unable to define scaling from mm to mag")


        if k is None:
            raise Exception("Not a valid scale for the selected mode")

    if mode == 'mm':
        if target_scale is None:
            z = source_meta['magnification']
            k = source_meta['magnification']
            i, j = get_base_mm_from_meta(source_meta)
        elif isinstance(target_scale, tuple) and len(target_scale) == 2:
            i, j = target_scale
            i = return_target_scaling_feature(i)
            j = return_target_scaling_feature(j)
            z = source_meta['magnification']
            x, y = get_base_mm_from_meta(source_meta)
            zoom_x = z * (x / i)
            zoom_y = z * (y / j)
            if zoom_x != zoom_y:
                raise UserWarning(
                    "Pixel dimensions for x and y are not the same. X = {}, Y = {}, Zoom X = {}, Zoom Y = {}"
                    .format(x, y, zoom_x, zoom_y)
                    )
            else:
                k = zoom_x

            if mode_modifier == 'assume' and x is None and y is None:
                x, y, z = generate_assumptions_for_x_y_given_mag(x, y, z)

        else:
            raise Exception("Scale for mm mode must be a tuple of (x, y)")

        if i is None or j is None:
            raise Exception("Not a valid scale for the selected mode")

    out = {
        'base_mm_x': x,
        'base_mm_y': y,
        'base_mag': z,
        'target_mm_x': i,
        'target_mm_y': j,
        'target_mag': k
    }

    return out

def calculate_slide_dimensions(source, mode='mag', target_scale=None, tile_size=None):
    '''
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    :param source: A large image tile source.
    :param mode: The magnification mode used for scaling.
    :param target_scale: The target scale for the image in 'mm' or 'mag' mode. For 'mag' mode should be integer.  For 'mm' mode should be a tuple of (x, y).
    :param tile_size: A tuple of (x, y) defining the tile size in pixels.
    :return: A slide dimensions dictionary that can be used for scaling any tile/region created using the source/iterator.
    '''
    # Use base scale pixel size to calculate conversion to get a region of a target size
    # todo: use large image convert scale to replace as many values here as possible
    slide_dimensions = {}

    source_meta = source.getMetadata()

    slide_dimensions['mode'] = mode
    slide_dimensions['base_magnification'] = source_meta['magnification']

    scaling_values = get_scaling_values_from_meta(source_meta, mode, target_scale)
    slide_dimensions['target_magnification'] = scaling_values['target_mag']
    slide_dimensions['base_size_x'] = source_meta['sizeX']
    slide_dimensions['base_size_y'] = source_meta['sizeY']

    # slide dimensions should also include sizes of original sizes
    slide_dimensions['base_tile_width'] = source_meta['tileWidth']
    slide_dimensions['base_tile_height'] = source_meta['tileHeight']

    # base tiles
    slide_dimensions['base_tile_range_x'] = math.ceil(source_meta['sizeX'] / source_meta['tileWidth'])
    slide_dimensions['base_tile_range_y'] = math.ceil(source_meta['sizeY'] / source_meta['tileHeight'])

    if 'target_mm_x' in scaling_values and scaling_values['target_mm_x'] is not None:
        slide_dimensions['target_mm_x'] = scaling_values['target_mm_x']
        slide_dimensions['base_mm_x'] = scaling_values['base_mm_x']
    else:
        raise Exception("Unable to generate scale dimensions for the selected mode. Failure in the x dimension")

    if 'target_mm_y' in scaling_values and scaling_values['target_mm_y'] is not None:
        slide_dimensions['target_mm_y'] = scaling_values['target_mm_y']
        slide_dimensions['base_mm_y'] = scaling_values['base_mm_y']
    else:
        raise Exception("Unable to generate scale dimensions for the selected mode. Failure in the y dimension")

    if mode == 'mag':
        convert_scale_px = source.convertRegionScale(
            sourceRegion=dict(left=0, top=0, width=slide_dimensions['base_size_x'], height=slide_dimensions['base_size_y'], units='base_pixels'),
            targetScale=dict(magnification=slide_dimensions['target_magnification']),
            targetUnits='mag_pixels'
        )

        convert_scale_mm = source.convertRegionScale(
            sourceRegion=dict(left=0, top=0, width=slide_dimensions['base_size_x'], height=slide_dimensions['base_size_y'], units='base_pixels'),
            targetScale=dict(magnification=slide_dimensions['target_magnification']),
            targetUnits='mm'
        )

    elif mode == 'mm':
        convert_scale_px = source.convertRegionScale(
            sourceRegion=dict(left=0, top=0, width=slide_dimensions['base_size_x'], height=slide_dimensions['base_size_y'], units='base_pixels'),
            targetScale=dict(mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y']),
            targetUnits='mag_pixels'
        )

        convert_scale_mm = source.convertRegionScale(
            sourceRegion=dict(left=0, top=0, width=slide_dimensions['base_size_x'], height=slide_dimensions['base_size_y'], units='base_pixels'),
            targetScale=dict(mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y']),
            targetUnits='mm'
        )

    else:
        raise ValueError("Mode is not valid for creating slide dimensions")

    if tile_size is None:
        tile_size = (source_meta['tileWidth'], source_meta['tileHeight'])

    slide_dimensions['conv_mm_x'] = slide_dimensions['target_mm_x'] / slide_dimensions['base_mm_x']
    slide_dimensions['conv_mm_y'] = slide_dimensions['target_mm_y'] / slide_dimensions['base_mm_y']

    slide_dimensions['tile_width_before_scaling'] = math.ceil(slide_dimensions['conv_mm_x'] * tile_size[0])
    slide_dimensions['tile_height_before_scaling'] = math.ceil(slide_dimensions['conv_mm_y'] * tile_size[1])

    slide_dimensions['base_size_x_mm'] = convert_scale_mm['width']
    slide_dimensions['base_size_y_mm'] = convert_scale_mm['height']

    # use convert scale to get output size, make sure to use ceil to avoid missing pixels on outer edges bottom and right
    slide_dimensions['target_width'] = convert_scale_px['width']
    slide_dimensions['target_height'] = convert_scale_px['height']


    slide_dimensions['tile_target_range_x'] = math.ceil(source_meta['sizeX'] / slide_dimensions['tile_width_before_scaling'])
    slide_dimensions['tile_target_range_y'] = math.ceil(source_meta['sizeY'] / slide_dimensions['tile_height_before_scaling'])
    slide_dimensions['tile_size'] = tile_size

    return slide_dimensions