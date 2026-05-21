import math
import warnings
from typing import Any, Dict, List, Optional, Union

import numpy as np


from ..base import TileSource


def get_smallest_bounding_box(roi):
    """

    :param points: numpy array featuring points from an annotation given coordinates from an entire slide
    :return: ROI from the whole slide image (x1, y1), (x2, y2)
    """
    points = np.array(roi['points'])[:, :2]
    roi_x1, roi_y1 = points.min(axis=0)
    roi_x2, roi_y2 = points.max(axis=0)
    return (roi_x1, roi_y1), (roi_x2, roi_y2)


def return_tile_slides_meeting_area_threshold(
        mask: np.ndarray, slide_dim: dict, tiles: Union[List, np.ndarray], area_threshold: float = 0.25, threshold_mask: float = 100):
    """
    A function that uses a mask generated from a whole slide image thumbnail to determine which tiles have enough content
    for being included in a set of evaluated tiles given a list of all possible tiles at a specific desired scaling.
    :param mask: An mask image derived from the whole slide image thumbnail
    :param slide_dim: A slide dimensions dictionary defining the image properties of a desired image and its' output
    :param area_threshold: A threshold of area to consider a tile useful.
    :param threshold_mask: A intensity of the pixel value in the image mask to determine if a tile is useful or not
    :return: Returns tiles in the form [(y, x)] where y is the row in the image and x is the column
    """
    return_tiles = []

    if np.max(mask) == 1:
        threshold_mask = 0

    for tile in tiles:
        mask_patch = get_patch_from_mask_for_tile(mask, slide_dim, tile)
        if np.sum(mask_patch > threshold_mask) > np.size(mask_patch) * area_threshold:
            return_tiles.append(tile)

    if len(return_tiles) == 0:
        raise ValueError(
            'No tiles found in the mask that meets parameters. Please ensure your mask is for the entire whole slide image and your scale and region parameters are correct.')

    return return_tiles


def return_relevant_tile_indexes_for_slide_dim(
        slide_dimensions: dict, tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]] = None):
    """
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    and returns a list of possible tiles given a desired output scaling.
    :param range_x: The range of the x dimension of the image
    :param range_y: The range of the y dimension of the image
    :param overlap: The amount of overlap between tiles.  A float from 0 to 1.0 or an integer corresponding to the number of
    pixels of overlap for the target tile size.  A minimum overlap is 0 pixels.
    :return: a list of tiles in the form of [(y, x)]
    """
    range_x = slide_dimensions['tile_target_range_x']
    range_y = slide_dimensions['tile_target_range_y']

    if tile_overlap is not None and 'x' in tile_overlap:
        if isinstance(tile_overlap['x'], int):
            overlap_x = tile_overlap['x'] / slide_dimensions['tile_size'][0]
        elif isinstance(tile_overlap['x'], float):
            overlap_x = tile_overlap['x']
            if overlap_x >= 1:
                raise ValueError('Tile overlap must be less than the tile size')
        else:
            raise ValueError('Tile overlap must be an integer or float')
    else:
        overlap_x = 0

    if tile_overlap is not None and 'y' in tile_overlap:
        if isinstance(tile_overlap['y'], int):
            overlap_y = tile_overlap['y'] / slide_dimensions['tile_size'][1]
            if overlap_y >= 1:
                raise ValueError('Tile overlap must be less than the tile size')
        elif isinstance(tile_overlap['y'], float):
            overlap_y = tile_overlap['y']
        else:
            raise ValueError('Tile overlap must be an integer or float')
    else:
        overlap_y = 0

    offset_x = 1 - overlap_x
    offset_y = 1 - overlap_y

    range_x = np.arange(0, range_x, offset_x)
    range_y = np.arange(0, range_y, offset_y)

    def cartesian2(x, y):
        prod = np.empty([len(x), len(y), 2], dtype=float)
        for i, s in enumerate(np.ix_(x, y)):
            prod[..., i] = s
        return np.fliplr(prod.reshape(-1, 2))

    # tiles in form y (column), x (row)
    return cartesian2(range_x, range_y)


def get_patch_from_mask_for_tile(mask: np.ndarray, slide_dimensions: dict, tile: list):
    """
    A function that returns a patch from the mask for a given tile.
    :param mask: The mask for the entire whole slide image.
    :param slide_dimensions: The slide dimensions dictionary determined by calculate_slide_dimensions.
    :param tile: The tile in the form of (y, x).
    :returns: The appropriate patch from the mask.
    """
    # todo: needs update for region
    tile_y, tile_x = tile

    mask_size_x = mask.shape[1]
    mask_size_y = mask.shape[0]

    conv_x_base_to_mask = mask_size_x / slide_dimensions['base_size_x']
    conv_y_base_to_mask = mask_size_y / slide_dimensions['base_size_y']

    bound_x1 = round(conv_x_base_to_mask *
                     tile_x *
                     slide_dimensions['tile_width_before_scaling'] +
                     (slide_dimensions['region_left'] *
                      conv_x_base_to_mask))
    bound_x2 = round(conv_x_base_to_mask *
                     (tile_x +
                      1) *
                     slide_dimensions['tile_width_before_scaling'] +
                     (slide_dimensions['region_left'] *
                      conv_x_base_to_mask))

    bound_y1 = round(conv_y_base_to_mask *
                     tile_y *
                     slide_dimensions['tile_height_before_scaling'] +
                     (slide_dimensions['region_top'] *
                      conv_y_base_to_mask))
    bound_y2 = round(conv_y_base_to_mask *
                     (tile_y +
                      1) *
                     slide_dimensions['tile_height_before_scaling'] +
                     (slide_dimensions['region_top'] *
                      conv_y_base_to_mask))

    patch_mask = mask[bound_y1:bound_y2, bound_x1:bound_x2]

    return patch_mask


def get_base_mm_from_meta(source_meta):
    """
    A function that returns the base mm from the source metadata.
    :param source_meta: The source metadata.
    :returns: The base mm.
    """
    mm_x = None
    mm_y = None

    if 'mm_x' in source_meta and source_meta['mm_x'] is not None:
        mm_x = source_meta['mm_x']
    if 'mm_y' in source_meta and source_meta['mm_y'] is not None:
        mm_y = source_meta['mm_y']

    if mm_x is None or mm_y is None:
        raise Exception('Tile source does not define pixel size in mm')
    return (mm_x, mm_y)


def return_target_scaling_feature(feature):
    """
    A function that returns the target scaling feature.
    :param feature: The feature.
    :returns: The target scaling feature.
    """
    out = None
    if isinstance(feature, str):
        out = float(feature)
    elif isinstance(feature, int):
        out = float(feature)
    elif isinstance(feature, float):
        out = float(feature)
    return out


def generate_assumptions_for_x_y_given_mag(x, y, z):
    """
    A function that generates assumptions for the x and y dimensions given a magnification.
    :param x: The x dimension.
    :param y: The y dimension.
    :param z: The magnification.
    :returns: The x and y dimensions.
    """
    if z is None:
        raise Exception('Unable to assume using magnification is not defined')
    # Prefer scaling using base dimensions
    if x is None:
        x = 0.00025 * z / 40
    if y is None:
        y = 0.00025 * z / 40

    if x is None or y is None or z is None:
        raise Exception('Assumption for dimensions failed')

    return x, y, z


def get_scaling_values_from_meta(source_meta: dict, scale: Optional[Dict[str, Any]] = None):
    """
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    :param source_meta: A large image source metadata.
    :param mode: The mode used for scaling. Should be either 'mag' or 'mm'.
    :param target_scale: The desired target scale as an int for magnification in 'mag' mode or a tuple of (x, y) in 'mm' mode.
    :returns: A dictionary defining scaling.
    """
    # Define none for both target (i, j, k) and base (x, y, z) values
    i, j, k, x, y, z = None, None, None, None, None, None

    if 'magnification' in scale:
        if scale['magnification'] is None:
            k = source_meta['magnification']
            z = source_meta['magnification']
            i, j = get_base_mm_from_meta(source_meta)
            x, y = i, j
        elif isinstance(scale['magnification'], int) or isinstance(scale['magnification'], float):
            k = return_target_scaling_feature(scale['magnification'])
            z = source_meta['magnification']

            if k is None:
                raise Exception(
                    'Unable to determine a target magnification with the provided value')

            try:
                x, y = get_base_mm_from_meta(source_meta)
                i = x * (z / k)
                j = y * (z / k)
            except BaseException:
                warnings.warn('Unable to define scaling from mm to mag', UserWarning)

        if k is None:
            raise Exception('Not a valid scale for the selected mode')

    if 'mm_x' in scale or 'mm_y' in scale:
        if scale['mm_x'] is None and scale['mm_y'] is None:
            z = source_meta['magnification']
            k = source_meta['magnification']
            i, j = get_base_mm_from_meta(source_meta)
        elif isinstance(scale['mm_x'], float) and isinstance(scale['mm_y'], float):
            i, j = scale['mm_x'], scale['mm_y']
            i = return_target_scaling_feature(i)
            j = return_target_scaling_feature(j)
            z = source_meta['magnification']
            x, y = get_base_mm_from_meta(source_meta)
            zoom_x = z * (x / i)
            zoom_y = z * (y / j)
            if zoom_x != zoom_y:
                warnings.warn(
                    'Pixel dimensions for x and y are not the same. X = {}, Y = {}, Zoom X = {}, Zoom Y = {}'
                    .format(x, y, zoom_x, zoom_y),
                    UserWarning,
                )
            else:
                k = zoom_x

            if 'assume' in scale and scale['assume'] and x is None and y is None:
                x, y, z = generate_assumptions_for_x_y_given_mag(x, y, z)

        else:
            raise Exception('Scale for mm mode must be a tuple of (x, y)')

        if i is None or j is None:
            raise Exception('Not a valid scale for the selected mode')

    out = {
        'base_mm_x': x,
        'base_mm_y': y,
        'base_mag': z,
        'target_mm_x': i,
        'target_mm_y': j,
        'target_mag': k,
    }

    return out


def calculate_slide_dimensions(source: TileSource, region: Optional[Dict[str, int]] = None, scale: Optional[Dict[str, Any]]
                               = None, tile_size: Optional[Dict[str, int]] = None, source_scale: Optional[Dict[str, Any]] = None, **kwargs):
    """
    A function that takes a dictionary containing parameters defining a whole slide image in terms of pixels, scaling, etc.
    :param source: A large image tile source.
    :param region: A dictionary with 'left', 'top', 'width', and 'height' and 'units' defining the region in pixels.
    :param scale: A dictionary with 'magnification' or 'mm_x' and 'mm_y' defining the scale for the image in 'mm' or 'mag' mode.
    :param tile_size: A dictionary with 'width' and 'height' defining the tile size in pixels.
    :param source_scale: A dictionary with 'magnification' or 'mm_x' and 'mm_y' defining the scale for the source region in 'mm' or 'mag' mode.
    :returns: A slide dimensions dictionary that can be used for scaling any tile/region created using the source/iterator.
    """
    # Use base scale pixel size to calculate conversion to get a region of a target size
    # todo: use large image convert scale to replace as many values here as possible
    slide_dimensions = {}

    source_meta = source.getMetadata()

    if region is not None:
        if 'bottom' in region:
            region['height'] = region['bottom'] - region['top']
        if 'right' in region:
            region['width'] = region['right'] - region['left']

        if 'units' not in region:
            raise ValueError(
                "Region must be a dictionary with 'units' which can be 'base_pixels', 'mag_pixels', or 'mm'")

        if 'left' not in region or 'top' not in region or 'width' not in region or 'height' not in region:
            raise ValueError(
                "Region must be a dictionary with 'left', 'top', 'width', and 'height'")
        if region['width'] <= 0 or region['height'] <= 0:
            raise ValueError('Region width and height must be greater than 0')
        if region['left'] < 0 or region['top'] < 0:
            raise ValueError('Region left and top must be greater than 0')
        if region['left'] + region['width'] > source_meta['sizeX'] or region['top'] + region['height'] > source_meta['sizeY']:
            raise ValueError('Region left and top must be less than the image size')
        if not (region['units'] == 'base_pixels' or region['units'] == 'mag_pixels' or region['units'] == 'mm'):
            raise ValueError("Region units must be either 'base_pixels' or 'mag_pixels' or 'mm'")
        if region['units'] == 'mag_pixels' and source_scale is None:
            raise ValueError("Source scale must be provided if region units are 'mag_pixels'")
        slide_dimensions['region_left'] = region['left']
        slide_dimensions['region_top'] = region['top']
        slide_dimensions['region_right'] = region['left'] + region['width']
        slide_dimensions['region_bottom'] = region['top'] + region['height']
        slide_dimensions['region_width'] = region['width']
        slide_dimensions['region_height'] = region['height']
        slide_dimensions['region_units'] = region['units']
    else:
        slide_dimensions['region_left'] = 0
        slide_dimensions['region_top'] = 0
        slide_dimensions['region_right'] = source_meta['sizeX']
        slide_dimensions['region_bottom'] = source_meta['sizeY']
        slide_dimensions['region_width'] = source_meta['sizeX']
        slide_dimensions['region_height'] = source_meta['sizeY']
        slide_dimensions['region_units'] = 'base_pixels'

    if scale is not None:
        if 'magnification' in scale:
            slide_dimensions['scale_mode'] = 'mag'
        elif 'mm_x' in scale and 'mm_y' in scale:
            slide_dimensions['scale_mode'] = 'mm'
        else:
            raise ValueError(
                "Scale must be a dictionary with either 'magnification' or 'mm_x' and 'mm_y'")
    else:
        scale = {'magnification': None}
        slide_dimensions['scale_mode'] = 'mag'

    if tile_size is not None:
        if 'width' not in tile_size and 'height' not in tile_size:
            raise ValueError("Tile size must be a dictionary with both 'width' and 'height'")
        if tile_size['width'] <= 0 or tile_size['height'] <= 0:
            raise ValueError('Tile size width and height must be greater than 0')
        slide_dimensions['tile_size'] = (tile_size['width'], tile_size['height'])
    else:
        slide_dimensions['tile_size'] = (source_meta['tileWidth'], source_meta['tileHeight'])

    slide_dimensions['base_magnification'] = source_meta['magnification']

    scaling_values = get_scaling_values_from_meta(source_meta, scale)
    slide_dimensions['target_magnification'] = scaling_values['target_mag']
    slide_dimensions['base_size_x'] = source_meta['sizeX']
    slide_dimensions['base_size_y'] = source_meta['sizeY']

    # slide dimensions should also include sizes of original sizes
    slide_dimensions['base_tile_width'] = source_meta['tileWidth']
    slide_dimensions['base_tile_height'] = source_meta['tileHeight']

    # base tiles
    slide_dimensions['base_tile_range_x'] = math.ceil(
        source_meta['sizeX'] / source_meta['tileWidth'])
    slide_dimensions['base_tile_range_y'] = math.ceil(
        source_meta['sizeY'] / source_meta['tileHeight'])

    if 'target_mm_x' in scaling_values and scaling_values['target_mm_x'] is not None:
        slide_dimensions['target_mm_x'] = scaling_values['target_mm_x']
        slide_dimensions['base_mm_x'] = scaling_values['base_mm_x']
    else:
        raise Exception(
            'Unable to generate scale dimensions for the selected mode. Failure in the x dimension')

    if 'target_mm_y' in scaling_values and scaling_values['target_mm_y'] is not None:
        slide_dimensions['target_mm_y'] = scaling_values['target_mm_y']
        slide_dimensions['base_mm_y'] = scaling_values['base_mm_y']
    else:
        raise Exception(
            'Unable to generate scale dimensions for the selected mode. Failure in the y dimension')

    if slide_dimensions['scale_mode'] == 'mag':
        if region is not None:
            if slide_dimensions['region_units'] == 'mag_pixels':
                if source_scale is None:
                    raise ValueError(
                        "source_scale parameter must be provided if region units are 'mag_pixels'")
                convert_scale_px = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units'],
                    ),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    sourceScale=source_scale,
                    targetUnits='mag_pixels',
                )

                convert_scale_mm = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units']),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    sourceScale=source_scale,
                    targetUnits='mm',
                )

                base_scale_px = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units'],
                    ),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    sourceScale=source_scale,
                    targetUnits='base_pixels',
                )

            else:
                convert_scale_px = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units'],
                    ),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    targetUnits='mag_pixels',
                )

                convert_scale_mm = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units']),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    targetUnits='mm',
                )

                base_scale_px = source.convertRegionScale(
                    sourceRegion=dict(
                        left=slide_dimensions['region_left'],
                        top=slide_dimensions['region_top'],
                        width=slide_dimensions['region_width'],
                        height=slide_dimensions['region_height'], units=slide_dimensions['region_units'],
                    ),
                    targetScale=dict(magnification=slide_dimensions['target_magnification']),
                    targetUnits='base_pixels',
                )

        else:
            convert_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(magnification=slide_dimensions['target_magnification']),
                targetUnits='mag_pixels',
            )

            convert_scale_mm = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(magnification=slide_dimensions['target_magnification']),
                targetUnits='mm',
            )

            base_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(magnification=slide_dimensions['target_magnification']),
                targetUnits='base_pixels',
            )

        slide_dimensions['level'] = source.getLevelForMagnification(
            slide_dimensions['target_magnification'])

    elif slide_dimensions['scale_mode'] == 'mm':
        if region is not None:
            convert_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=slide_dimensions['region_left'],
                    top=slide_dimensions['region_top'],
                    width=slide_dimensions['region_width'],
                    height=slide_dimensions['region_height'], units=slide_dimensions['region_units']),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='mag_pixels',
            )

            convert_scale_mm = source.convertRegionScale(
                sourceRegion=dict(
                    left=slide_dimensions['region_left'],
                    top=slide_dimensions['region_top'],
                    width=slide_dimensions['region_width'],
                    height=slide_dimensions['region_height'], units=slide_dimensions['region_units']),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='mm',
            )

            base_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=slide_dimensions['region_left'],
                    top=slide_dimensions['region_top'],
                    width=slide_dimensions['region_width'],
                    height=slide_dimensions['region_height'], units=slide_dimensions['region_units']),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='base_pixels',
            )
        else:
            convert_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='mag_pixels',
            )

            convert_scale_mm = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='mm',
            )

            base_scale_px = source.convertRegionScale(
                sourceRegion=dict(
                    left=0,
                    top=0,
                    width=slide_dimensions['base_size_x'],
                    height=slide_dimensions['base_size_y'],
                    units='base_pixels'),
                targetScale=dict(
                    mm_x=slide_dimensions['target_mm_x'],
                    mm_y=slide_dimensions['target_mm_y']),
                targetUnits='base_pixels',
            )

        slide_dimensions['level'] = source.getLevelForMagnification(
            mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y'])

    else:
        raise ValueError('Mode is not valid for creating slide dimensions')

    slide_dimensions['conv_mm_x'] = slide_dimensions['target_mm_x'] / slide_dimensions['base_mm_x']
    slide_dimensions['conv_mm_y'] = slide_dimensions['target_mm_y'] / slide_dimensions['base_mm_y']

    if tile_size is not None:
        slide_dimensions['tile_width_before_scaling'] = math.ceil(
            slide_dimensions['conv_mm_x'] * slide_dimensions['tile_size'][0])
        slide_dimensions['tile_height_before_scaling'] = math.ceil(
            slide_dimensions['conv_mm_y'] * slide_dimensions['tile_size'][1])
    else:
        slide_dimensions['tile_width_before_scaling'] = math.ceil(
            slide_dimensions['conv_mm_x'] * source_meta['tileWidth'])
        slide_dimensions['tile_height_before_scaling'] = math.ceil(
            slide_dimensions['conv_mm_y'] * source_meta['tileHeight'])

    slide_dimensions['base_size_x_mm'] = convert_scale_mm['width']
    slide_dimensions['base_size_y_mm'] = convert_scale_mm['height']

    # use convert scale to get output size, make sure to use ceil to avoid
    # missing pixels on outer edges bottom and right
    slide_dimensions['target_width'] = convert_scale_px['width']
    slide_dimensions['target_height'] = convert_scale_px['height']

    slide_dimensions['tile_target_range_x'] = math.ceil(
        base_scale_px['width'] / slide_dimensions['tile_width_before_scaling'])
    slide_dimensions['tile_target_range_y'] = math.ceil(
        base_scale_px['height'] / slide_dimensions['tile_height_before_scaling'])

    return slide_dimensions
