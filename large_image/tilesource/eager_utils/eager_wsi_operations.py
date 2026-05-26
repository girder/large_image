"""Whole-slide geometry and scaling helpers for eager reads."""

from __future__ import annotations

import math
import warnings
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

import numpy as np

if TYPE_CHECKING:
    from ..base import TileSource


def get_smallest_bounding_box(roi):
    """Return the smallest bounding box that contains an ROI polygon.

    :param roi: ROI dictionary with a points sequence containing x and y coordinates.
    :returns: The top-left and bottom-right coordinate pairs.
    """
    points = np.array(roi['points'])[:, :2]
    roi_x1, roi_y1 = points.min(axis=0)
    roi_x2, roi_y2 = points.max(axis=0)
    return (roi_x1, roi_y1), (roi_x2, roi_y2)


def return_tile_slides_meeting_area_threshold(
    mask: np.ndarray,
    slide_dim: dict,
    tiles: Union[List, np.ndarray],
    area_threshold: float = 0.25,
    threshold_mask: float = 100,
):
    """Filter tile indexes by the amount of mask signal they contain.

    :param mask: Whole-slide mask image used to score candidate tiles.
    :param slide_dim: Slide dimension metadata from calculate_slide_dimensions.
    :param tiles: Candidate tile indexes in row, column order.
    :param area_threshold: Minimum mask-signal fraction required for a tile.
    :param threshold_mask: Minimum mask pixel value considered signal.
    :returns: A list of tile indexes that meet the threshold.
    """
    return_tiles = []

    if np.max(mask) == 1:
        threshold_mask = 0

    for tile in tiles:
        mask_patch = get_patch_from_mask_for_tile(mask, slide_dim, tile)
        if np.sum(mask_patch > threshold_mask) > np.size(mask_patch) * area_threshold:
            return_tiles.append(tile)

    if len(return_tiles) == 0:
        msg = (
            'No tiles found in the mask that meets parameters. Please ensure your mask '
            'is for the entire whole slide image and your scale and region parameters '
            'are correct.'
        )
        raise ValueError(msg)

    return return_tiles


def return_relevant_tile_indexes_for_slide_dim(
    slide_dimensions: dict, tile_overlap: Optional[Union[Dict[str, int] | Dict[str, float]]] = None,
):
    """Return tile indexes covering the target slide dimensions.

    :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
    :param tile_overlap: Optional x and y tile overlap as pixels or fractions.
    :returns: A numpy array of tile indexes in row, column order.
    """
    range_x = slide_dimensions['tile_target_range_x']
    range_y = slide_dimensions['tile_target_range_y']

    if tile_overlap is not None and 'x' in tile_overlap:
        if isinstance(tile_overlap['x'], int):
            overlap_x = tile_overlap['x'] / slide_dimensions['tile_size'][0]
        elif isinstance(tile_overlap['x'], float):
            overlap_x = tile_overlap['x']
            if overlap_x >= 1:
                msg = 'Tile overlap must be less than the tile size'
                raise ValueError(msg)
        else:
            msg = 'Tile overlap must be an integer or float'
            raise ValueError(msg)
    else:
        overlap_x = 0

    if tile_overlap is not None and 'y' in tile_overlap:
        if isinstance(tile_overlap['y'], int):
            overlap_y = tile_overlap['y'] / slide_dimensions['tile_size'][1]
            if overlap_y >= 1:
                msg = 'Tile overlap must be less than the tile size'
                raise ValueError(msg)
        elif isinstance(tile_overlap['y'], float):
            overlap_y = tile_overlap['y']
        else:
            msg = 'Tile overlap must be an integer or float'
            raise ValueError(msg)
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
    """Return the mask patch corresponding to a tile index.

    :param mask: Whole-slide mask image.
    :param slide_dimensions: Slide dimension metadata from calculate_slide_dimensions.
    :param tile: Tile index in row, column order.
    :returns: A mask patch for the requested tile.
    """
    # todo: needs update for region
    tile_y, tile_x = tile

    mask_size_x = mask.shape[1]
    mask_size_y = mask.shape[0]

    conv_x_base_to_mask = mask_size_x / slide_dimensions['base_size_x']
    conv_y_base_to_mask = mask_size_y / slide_dimensions['base_size_y']

    bound_x1 = round(
        conv_x_base_to_mask * tile_x * slide_dimensions['tile_width_before_scaling'] +
        (slide_dimensions['region_left'] * conv_x_base_to_mask),
    )
    bound_x2 = round(
        conv_x_base_to_mask * (tile_x + 1) * slide_dimensions['tile_width_before_scaling'] +
        (slide_dimensions['region_left'] * conv_x_base_to_mask),
    )

    bound_y1 = round(
        conv_y_base_to_mask * tile_y * slide_dimensions['tile_height_before_scaling'] +
        (slide_dimensions['region_top'] * conv_y_base_to_mask),
    )
    bound_y2 = round(
        conv_y_base_to_mask * (tile_y + 1) * slide_dimensions['tile_height_before_scaling'] +
        (slide_dimensions['region_top'] * conv_y_base_to_mask),
    )

    patch_mask = mask[bound_y1:bound_y2, bound_x1:bound_x2]

    return patch_mask


def get_base_mm_from_meta(source_meta):
    """Return base pixel sizes from source metadata.

    :param source_meta: Metadata dictionary from a tile source.
    :returns: The base mm_x and mm_y values.
    """
    mm_x = None
    mm_y = None

    if 'mm_x' in source_meta and source_meta['mm_x'] is not None:
        mm_x = source_meta['mm_x']
    if 'mm_y' in source_meta and source_meta['mm_y'] is not None:
        mm_y = source_meta['mm_y']

    if mm_x is None or mm_y is None:
        msg = 'Tile source does not define pixel size in mm'
        raise Exception(msg)
    return (mm_x, mm_y)


def return_target_scaling_feature(feature):
    """Normalize a target scaling value to a float.

    :param feature: Scaling value as a string, integer, float, or None.
    :returns: The scaling value as a float, or None if it cannot be converted.
    """
    out = None
    if isinstance(feature, (str, int, float)):
        out = float(feature)
    return out


def generate_assumptions_for_x_y_given_mag(x, y, z):
    """Estimate pixel sizes from magnification when metadata is incomplete.

    :param x: Existing horizontal pixel size, or None.
    :param y: Existing vertical pixel size, or None.
    :param z: Magnification used to estimate missing pixel sizes.
    :returns: Estimated x, y, and z values.
    """
    if z is None:
        msg = 'Unable to assume using magnification is not defined'
        raise Exception(msg)
    # Prefer scaling using base dimensions
    if x is None:
        x = 0.00025 * z / 40
    if y is None:
        y = 0.00025 * z / 40

    if x is None or y is None or z is None:
        msg = 'Assumption for dimensions failed'
        raise Exception(msg)

    return x, y, z


def get_scaling_values_from_meta(source_meta: dict, scale: Optional[Dict[str, Any]] = None):
    """Calculate base and target scaling values from source metadata.

    :param source_meta: Metadata dictionary from a tile source.
    :param scale: Scale request with either magnification or mm_x and mm_y values.
    :returns: A dictionary with base and target mm and magnification values.
    """
    # Define none for both target (i, j, k) and base (x, y, z) values
    i, j, k, x, y, z = None, None, None, None, None, None
    if scale is None:
        scale = {'magnification': None}

    if 'magnification' in scale:
        if scale['magnification'] is None:
            k = source_meta['magnification']
            z = source_meta['magnification']
            i, j = get_base_mm_from_meta(source_meta)
            x, y = i, j
        elif isinstance(scale['magnification'], (int, float)):
            k = return_target_scaling_feature(scale['magnification'])
            z = source_meta['magnification']

            if k is None:
                msg = 'Unable to determine a target magnification with the provided value'
                raise Exception(msg)

            try:
                x, y = get_base_mm_from_meta(source_meta)
                i = x * (z / k)
                j = y * (z / k)
            except Exception:
                warnings.warn('Unable to define scaling from mm to mag', UserWarning, stacklevel=2)

        if k is None:
            msg = 'Not a valid scale for the selected mode'
            raise Exception(msg)

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
                    (
                        'Pixel dimensions for x and y are not the same. '
                        'X = {}, Y = {}, Zoom X = {}, Zoom Y = {}'
                    ).format(x, y, zoom_x, zoom_y),
                    UserWarning,
                    stacklevel=2,
                )
            else:
                k = zoom_x

            if 'assume' in scale and scale['assume'] and x is None and y is None:
                x, y, z = generate_assumptions_for_x_y_given_mag(x, y, z)

        else:
            msg = 'Scale for mm mode must be a tuple of (x, y)'
            raise Exception(msg)

        if i is None or j is None:
            msg = 'Not a valid scale for the selected mode'
            raise Exception(msg)

    out = {
        'base_mm_x': x,
        'base_mm_y': y,
        'base_mag': z,
        'target_mm_x': i,
        'target_mm_y': j,
        'target_mag': k,
    }

    return out


def _normalize_region_bounds(region: Dict[str, Any]) -> None:
    """Normalize right/bottom region bounds into width and height.

    :param region: Mutable region dictionary supplied by the caller.
    :returns: None.
    """
    if 'bottom' in region:
        region['height'] = region['bottom'] - region['top']
    if 'right' in region:
        region['width'] = region['right'] - region['left']


def _validate_region(region: Dict[str, Any], source_meta: Dict[str, Any], source_scale) -> None:
    """Validate an eager source region.

    :param region: Region with left, top, width, height, and units.
    :param source_meta: Tile-source metadata used for image bounds.
    :param source_scale: Scale required when the region is in mag pixels.
    :returns: None.
    """
    if 'units' not in region:
        msg = (
            "Region must be a dictionary with 'units' which can be "
            "'base_pixels', 'mag_pixels', or 'mm'"
        )
        raise ValueError(msg)
    if any(key not in region for key in ('left', 'top', 'width', 'height')):
        msg = "Region must be a dictionary with 'left', 'top', 'width', and 'height'"
        raise ValueError(msg)
    if region['width'] <= 0 or region['height'] <= 0:
        msg = 'Region width and height must be greater than 0'
        raise ValueError(msg)
    if region['left'] < 0 or region['top'] < 0:
        msg = 'Region left and top must be greater than 0'
        raise ValueError(msg)
    if (
        region['left'] + region['width'] > source_meta['sizeX'] or
        region['top'] + region['height'] > source_meta['sizeY']
    ):
        msg = 'Region left and top must be less than the image size'
        raise ValueError(msg)
    if region['units'] not in {'base_pixels', 'mag_pixels', 'mm'}:
        msg = "Region units must be either 'base_pixels' or 'mag_pixels' or 'mm'"
        raise ValueError(msg)
    if region['units'] == 'mag_pixels' and source_scale is None:
        msg = "Source scale must be provided if region units are 'mag_pixels'"
        raise ValueError(msg)


def _region_slide_dimensions(
    source_meta: Dict[str, Any],
    region: Optional[Dict[str, Any]],
    source_scale,
) -> Dict[str, Any]:
    """Return slide-dimension fields describing the requested source region.

    :param source_meta: Tile-source metadata used for the full-image fallback.
    :param region: Optional source region with left, top, width, height, and units.
    :param source_scale: Scale required when the region is in mag pixels.
    :returns: Region-related slide-dimension fields.
    """
    if region is None:
        region = dict(
            left=0,
            top=0,
            width=source_meta['sizeX'],
            height=source_meta['sizeY'],
            units='base_pixels',
        )
    else:
        _normalize_region_bounds(region)
        _validate_region(region, source_meta, source_scale)

    return {
        'region_left': region['left'],
        'region_top': region['top'],
        'region_right': region['left'] + region['width'],
        'region_bottom': region['top'] + region['height'],
        'region_width': region['width'],
        'region_height': region['height'],
        'region_units': region['units'],
    }


def _normalize_scale(scale: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], str]:
    """Return a usable scale dictionary and eager scale mode.

    :param scale: Optional target scale using magnification or mm_x and mm_y.
    :returns: A scale dictionary and either 'mag' or 'mm'.
    """
    if scale is None:
        return {'magnification': None}, 'mag'
    if 'magnification' in scale:
        return scale, 'mag'
    if 'mm_x' in scale and 'mm_y' in scale:
        return scale, 'mm'
    msg = "Scale must be a dictionary with either 'magnification' or 'mm_x' and 'mm_y'"
    raise ValueError(msg)


def _tile_size_from_meta(
    source_meta: Dict[str, Any], tile_size: Optional[Dict[str, int]],
) -> tuple[int, int]:
    """Return the requested eager tile size.

    :param source_meta: Tile-source metadata used for the default size.
    :param tile_size: Optional output tile size with width and height.
    :returns: Tile width and height.
    """
    if tile_size is None:
        return source_meta['tileWidth'], source_meta['tileHeight']
    if 'width' not in tile_size or 'height' not in tile_size:
        msg = "Tile size must be a dictionary with both 'width' and 'height'"
        raise ValueError(msg)
    if tile_size['width'] <= 0 or tile_size['height'] <= 0:
        msg = 'Tile size width and height must be greater than 0'
        raise ValueError(msg)
    return tile_size['width'], tile_size['height']


def _add_base_slide_dimensions(
    slide_dimensions: Dict[str, Any], source_meta: Dict[str, Any], scale: Dict[str, Any],
) -> None:
    """Populate base metadata and target scaling fields.

    :param slide_dimensions: Slide-dimension dictionary to update.
    :param source_meta: Tile-source metadata.
    :param scale: Normalized target scale dictionary.
    :returns: None.
    """
    scaling_values = get_scaling_values_from_meta(source_meta, scale)
    slide_dimensions['base_magnification'] = source_meta['magnification']
    slide_dimensions['target_magnification'] = scaling_values['target_mag']
    slide_dimensions['base_size_x'] = source_meta['sizeX']
    slide_dimensions['base_size_y'] = source_meta['sizeY']
    slide_dimensions['base_tile_width'] = source_meta['tileWidth']
    slide_dimensions['base_tile_height'] = source_meta['tileHeight']
    slide_dimensions['base_tile_range_x'] = math.ceil(
        source_meta['sizeX'] / source_meta['tileWidth'],
    )
    slide_dimensions['base_tile_range_y'] = math.ceil(
        source_meta['sizeY'] / source_meta['tileHeight'],
    )
    _add_mm_scaling_values(slide_dimensions, scaling_values)


def _add_mm_scaling_values(
    slide_dimensions: Dict[str, Any], scaling_values: Dict[str, Any],
) -> None:
    """Populate millimeter scaling values.

    :param slide_dimensions: Slide-dimension dictionary to update.
    :param scaling_values: Scale values returned from metadata conversion.
    :returns: None.
    """
    if 'target_mm_x' not in scaling_values or scaling_values['target_mm_x'] is None:
        msg = (
            'Unable to generate scale dimensions for the selected mode. Failure in the x dimension'
        )
        raise Exception(msg)
    if 'target_mm_y' not in scaling_values or scaling_values['target_mm_y'] is None:
        msg = (
            'Unable to generate scale dimensions for the selected mode. Failure in the y dimension'
        )
        raise Exception(msg)
    slide_dimensions['target_mm_x'] = scaling_values['target_mm_x']
    slide_dimensions['target_mm_y'] = scaling_values['target_mm_y']
    slide_dimensions['base_mm_x'] = scaling_values['base_mm_x']
    slide_dimensions['base_mm_y'] = scaling_values['base_mm_y']


def _source_region_from_slide_dimensions(slide_dimensions: Dict[str, Any]) -> Dict[str, Any]:
    """Return a convertRegionScale source region from slide dimensions.

    :param slide_dimensions: Slide dimension metadata.
    :returns: Region dictionary accepted by Large Image scale conversion.
    """
    return dict(
        left=slide_dimensions['region_left'],
        top=slide_dimensions['region_top'],
        width=slide_dimensions['region_width'],
        height=slide_dimensions['region_height'],
        units=slide_dimensions['region_units'],
    )


def _target_scale_from_slide_dimensions(slide_dimensions: Dict[str, Any]) -> Dict[str, Any]:
    """Return a convertRegionScale target scale from slide dimensions.

    :param slide_dimensions: Slide dimension metadata.
    :returns: Target scale dictionary for the active scale mode.
    """
    if slide_dimensions['scale_mode'] == 'mag':
        return {'magnification': slide_dimensions['target_magnification']}
    if slide_dimensions['scale_mode'] == 'mm':
        return {'mm_x': slide_dimensions['target_mm_x'], 'mm_y': slide_dimensions['target_mm_y']}
    msg = 'Mode is not valid for creating slide dimensions'
    raise ValueError(msg)


def _convert_region_scales(
    source: TileSource, slide_dimensions: Dict[str, Any], source_scale: Optional[Dict[str, Any]],
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """Convert the requested eager source region into output scales.

    :param source: Tile source used for scale conversion.
    :param slide_dimensions: Slide dimension metadata.
    :param source_scale: Source scale required for mag-pixel regions.
    :returns: Pixel, millimeter, and base-pixel converted regions.
    """
    convert_kwargs: Dict[str, Any] = dict(
        sourceRegion=_source_region_from_slide_dimensions(slide_dimensions),
        targetScale=_target_scale_from_slide_dimensions(slide_dimensions),
    )
    if slide_dimensions['region_units'] == 'mag_pixels':
        if source_scale is None:
            msg = "source_scale parameter must be provided if region units are 'mag_pixels'"
            raise ValueError(msg)
        convert_kwargs['sourceScale'] = source_scale
    return (
        source.convertRegionScale(**convert_kwargs, targetUnits='mag_pixels'),
        source.convertRegionScale(**convert_kwargs, targetUnits='mm'),
        source.convertRegionScale(**convert_kwargs, targetUnits='base_pixels'),
    )


def _add_level(source: TileSource, slide_dimensions: Dict[str, Any]) -> None:
    """Populate the tile-source level for the active scale mode.

    :param source: Tile source used for level selection.
    :param slide_dimensions: Slide dimension metadata to update.
    :returns: None.
    """
    if slide_dimensions['scale_mode'] == 'mag':
        slide_dimensions['level'] = source.getLevelForMagnification(
            slide_dimensions['target_magnification'],
        )
        return
    if slide_dimensions['scale_mode'] == 'mm':
        slide_dimensions['level'] = source.getLevelForMagnification(
            mm_x=slide_dimensions['target_mm_x'], mm_y=slide_dimensions['target_mm_y'],
        )
        return
    msg = 'Mode is not valid for creating slide dimensions'
    raise ValueError(msg)


def _add_output_dimensions(
    slide_dimensions: Dict[str, Any],
    convert_scale_px: Dict[str, Any],
    convert_scale_mm: Dict[str, Any],
    base_scale_px: Dict[str, Any],
) -> None:
    """Populate output dimensions derived from converted region scales.

    :param slide_dimensions: Slide dimension metadata to update.
    :param convert_scale_px: Region converted into target pixels.
    :param convert_scale_mm: Region converted into millimeters.
    :param base_scale_px: Region converted into base pixels.
    :returns: None.
    """
    slide_dimensions['conv_mm_x'] = slide_dimensions['target_mm_x'] / slide_dimensions['base_mm_x']
    slide_dimensions['conv_mm_y'] = slide_dimensions['target_mm_y'] / slide_dimensions['base_mm_y']
    slide_dimensions['tile_width_before_scaling'] = math.ceil(
        slide_dimensions['conv_mm_x'] * slide_dimensions['tile_size'][0],
    )
    slide_dimensions['tile_height_before_scaling'] = math.ceil(
        slide_dimensions['conv_mm_y'] * slide_dimensions['tile_size'][1],
    )
    slide_dimensions['base_size_x_mm'] = convert_scale_mm['width']
    slide_dimensions['base_size_y_mm'] = convert_scale_mm['height']
    slide_dimensions['target_width'] = convert_scale_px['width']
    slide_dimensions['target_height'] = convert_scale_px['height']
    slide_dimensions['tile_target_range_x'] = math.ceil(
        base_scale_px['width'] / slide_dimensions['tile_width_before_scaling'],
    )
    slide_dimensions['tile_target_range_y'] = math.ceil(
        base_scale_px['height'] / slide_dimensions['tile_height_before_scaling'],
    )


def calculate_slide_dimensions(
    source: TileSource,
    region: Optional[Dict[str, int]] = None,
    scale: Optional[Dict[str, Any]] = None,
    tile_size: Optional[Dict[str, int]] = None,
    source_scale: Optional[Dict[str, Any]] = None,
    **kwargs,
):
    """Calculate slide geometry for eager reads.

    :param source: Large Image tile source used for metadata and scale conversion.
    :param region: Optional region with left, top, width, height, and units.
    :param scale: Optional target scale using magnification or mm_x and mm_y.
    :param tile_size: Optional output tile size with width and height in pixels.
    :param source_scale: Source scale used when region units are mag_pixels.
    :param kwargs: Additional options reserved for compatibility.
    :returns: A slide dimension dictionary used by eager read planning and workers.
    """
    source_meta = source.getMetadata()
    normalized_scale, scale_mode = _normalize_scale(scale)
    slide_dimensions = _region_slide_dimensions(source_meta, region, source_scale)
    slide_dimensions['scale_mode'] = scale_mode
    slide_dimensions['tile_size'] = _tile_size_from_meta(source_meta, tile_size)

    _add_base_slide_dimensions(slide_dimensions, source_meta, normalized_scale)
    convert_scale_px, convert_scale_mm, base_scale_px = _convert_region_scales(
        source, slide_dimensions, source_scale,
    )
    _add_level(source, slide_dimensions)
    _add_output_dimensions(
        slide_dimensions, convert_scale_px, convert_scale_mm, base_scale_px,
    )
    return slide_dimensions
