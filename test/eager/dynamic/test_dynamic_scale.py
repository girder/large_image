import os
from test.eager.eager_helpers import (get_tissue_mask_with_background_elimination)
from typing import Optional

import matplotlib.pyplot as plt
import numpy as np

import large_image


def dynamic_transform_scale(read_kwargs: np.ndarray, slide_dimensions: dict):
    xlt = read_kwargs[:, 6]
    ytt = read_kwargs[:, 4]
    xrt = read_kwargs[:, 7]
    ybt = read_kwargs[:, 5]
    mm_x = read_kwargs[:, 9]
    mm_y = read_kwargs[:, 8]

    # Range of scaling
    scale_range = [0.35, 1]

    # Randomly zoom out by increasing mm-per-pixel
    scale_multi = 1 / (np.random.random() * (scale_range[1] - scale_range[0]) + scale_range[0])

    # Needs to give dictionary for scaling region
    dynamic_scale = {
        'mm_x': slide_dimensions['target_mm_x'] * scale_multi,
        'mm_y': slide_dimensions['target_mm_y'] * scale_multi,
    }

    conv_mm_x = dynamic_scale['mm_x'] / slide_dimensions['base_mm_x']
    conv_mm_y = dynamic_scale['mm_y'] / slide_dimensions['base_mm_y']

    width = np.ceil(slide_dimensions['tile_size'][0] * conv_mm_x).astype(np.int64)
    height = np.ceil(slide_dimensions['tile_size'][1] * conv_mm_y).astype(np.int64)

    center_x = np.round((xlt + xrt) / 2)
    center_y = np.round((ytt + ybt) / 2)

    xlt = np.round(center_x - (width / 2)).astype(np.int64)
    ytt = np.round(center_y - (height / 2)).astype(np.int64)
    xrt = xlt + width
    ybt = ytt + height

    # Keep region size constant by shifting the full window into bounds.
    dx_left = np.minimum(xlt, 0)
    xlt = xlt - dx_left
    xrt = xrt - dx_left

    dy_top = np.minimum(ytt, 0)
    ytt = ytt - dy_top
    ybt = ybt - dy_top

    dx_right = np.maximum(xrt - slide_dimensions['base_size_x'], 0)
    xlt = xlt - dx_right
    xrt = xrt - dx_right

    dy_bottom = np.maximum(ybt - slide_dimensions['base_size_y'], 0)
    ytt = ytt - dy_bottom
    ybt = ybt - dy_bottom

    mm_x = mm_x * scale_multi
    mm_y = mm_y * scale_multi

    return xlt, ytt, xrt, ybt, mm_x, mm_y, dynamic_scale, conv_mm_x, conv_mm_y


def dynamic_transform_scale_v2(read_kwargs: np.ndarray, slide_dimensions: dict,
                               min_mm: float = 0.00025, max_mm: float = 0.0005, anchor_mm: float = 0.0001):
    xlt = read_kwargs[:, 6]
    ytt = read_kwargs[:, 4]
    xrt = read_kwargs[:, 7]
    ybt = read_kwargs[:, 5]
    mm_x = read_kwargs[:, 9]
    mm_y = read_kwargs[:, 8]

    dynamic_mm = np.random.random() * (max_mm - min_mm) + min_mm

    # Needs to give dictionary for scaling region
    dynamic_scale = {
        'mm_x': dynamic_mm,
        'mm_y': dynamic_mm,
    }

    conv_mm_x = dynamic_scale['mm_x'] / slide_dimensions['base_mm_x']
    conv_mm_y = dynamic_scale['mm_y'] / slide_dimensions['base_mm_y']

    width = np.ceil(slide_dimensions['tile_size'][0] * conv_mm_x).astype(np.int64)
    height = np.ceil(slide_dimensions['tile_size'][1] * conv_mm_y).astype(np.int64)

    center_x = np.round((xlt + xrt) / 2)
    center_y = np.round((ytt + ybt) / 2)

    # If dynamic mm is less than anchor mm, we need to define a new region
    # based on the anchor region
    if dynamic_mm < anchor_mm:
        # define anchor region based on center from read_kwargs
        anchor_conv_mm_x = slide_dimensions['base_mm_x'] / anchor_mm
        anchor_conv_mm_y = slide_dimensions['base_mm_y'] / anchor_mm

        anchor_width = np.ceil(slide_dimensions['tile_size'][0] * anchor_conv_mm_x).astype(np.int64)
        anchor_height = np.ceil(
            slide_dimensions['tile_size'][1] *
            anchor_conv_mm_y).astype(
            np.int64)

        anchor_xlt = np.round(center_x - (anchor_width / 2)).astype(np.int64)
        anchor_ytt = np.round(center_y - (anchor_height / 2)).astype(np.int64)
        anchor_xrt = anchor_xlt + anchor_width
        anchor_ybt = anchor_ytt + anchor_height

        center_x_min = anchor_xlt + width
        center_y_min = anchor_ytt + height
        center_x_max = anchor_xrt - width
        center_y_max = anchor_ybt - height

        center_dx_left = np.minimum(center_x_min, 0)
        center_dx_right = np.maximum(center_x_max - slide_dimensions['base_size_x'], 0)
        center_dy_top = np.minimum(center_y_min, 0)
        center_dy_bottom = np.maximum(center_y_max - slide_dimensions['base_size_y'], 0)

        center_x_min = center_x_min - center_dx_left
        center_y_min = center_y_min - center_dy_top
        center_x_max = center_x_max - center_dx_right
        center_y_max = center_y_max - center_dy_bottom

        random_center_x_range = np.random() * (center_x_max - center_x_min) + center_x_min
        random_center_y_range = np.random() * (center_y_max - center_y_min) + center_y_min

        xlt = np.round(random_center_x_range - (width / 2)).astype(np.int64)
        ytt = np.round(random_center_y_range - (height / 2)).astype(np.int64)
        xrt = xlt + width
        ybt = ytt + height
    else:
        # If dynamic mm is greater than anchor mm, we need to define a new region based
        # on the original center region which should always be within the bounds of the slide
        xlt = np.round(center_x - (width / 2)).astype(np.int64)
        ytt = np.round(center_y - (height / 2)).astype(np.int64)
        xrt = xlt + width
        ybt = ytt + height

        # Keep region size constant by shifting the full window into bounds.
        dx_left = np.minimum(xlt, 0)
        xlt = xlt - dx_left
        xrt = xrt - dx_left

        dy_top = np.minimum(ytt, 0)
        ytt = ytt - dy_top
        ybt = ybt - dy_top

        dx_right = np.maximum(xrt - slide_dimensions['base_size_x'], 0)
        xlt = xlt - dx_right
        xrt = xrt - dx_right

        dy_bottom = np.maximum(ybt - slide_dimensions['base_size_y'], 0)
        ytt = ytt - dy_bottom
        ybt = ybt - dy_bottom

    mm_x = np.repeat(dynamic_mm, read_kwargs.shape[0])
    mm_y = np.repeat(dynamic_mm, read_kwargs.shape[0])

    return xlt, ytt, xrt, ybt, mm_x, mm_y, dynamic_scale, conv_mm_x, conv_mm_y


def get_mask_from_region(slide_dimensions, mask, xlt: np.ndarray,
                         ytt: np.ndarray, xrt: np.ndarray, ybt: np.ndarray):
    scaled_xlt, scaled_ytt, scaled_xrt, scaled_ybt = scale_region_coordinates(
        slide_dimensions, mask, xlt, ytt, xrt, ybt)
    if np.ndim(scaled_xlt) == 0:
        return mask[int(scaled_ytt):int(scaled_ybt), int(scaled_xlt):int(scaled_xrt)]

    regions = np.empty(np.shape(scaled_xlt), dtype=object)
    for idx in np.ndindex(np.shape(scaled_xlt)):
        regions[idx] = mask[
            int(scaled_ytt[idx]):int(scaled_ybt[idx]),
            int(scaled_xlt[idx]):int(scaled_xrt[idx]),
        ]
    return regions


def scale_region_coordinates(slide_dimensions, mask, xlt: np.ndarray,
                             ytt: np.ndarray, xrt: np.ndarray, ybt: np.ndarray):
    base_w = float(slide_dimensions['base_size_x'])
    base_h = float(slide_dimensions['base_size_y'])
    mask_h, mask_w = mask.shape[:2]
    xlt = np.asarray(xlt, dtype=np.float64)
    ytt = np.asarray(ytt, dtype=np.float64)
    xrt = np.asarray(xrt, dtype=np.float64)
    ybt = np.asarray(ybt, dtype=np.float64)

    if xlt.shape != ytt.shape or xlt.shape != xrt.shape or xlt.shape != ybt.shape:
        raise ValueError(
            'scale_region_coordinates expects matching shapes for xlt/ytt/xrt/ybt, '
            f'got {xlt.shape=}, {ytt.shape=}, {xrt.shape=}, {ybt.shape=}',
        )

    # Convert full-resolution coordinates into mask-space coordinates.
    scaled_xlt = np.floor(xlt * mask_w / base_w).astype(np.int64)
    scaled_ytt = np.floor(ytt * mask_h / base_h).astype(np.int64)
    scaled_xrt = np.ceil(xrt * mask_w / base_w).astype(np.int64)
    scaled_ybt = np.ceil(ybt * mask_h / base_h).astype(np.int64)

    scaled_xlt = np.clip(scaled_xlt, 0, mask_w)
    scaled_ytt = np.clip(scaled_ytt, 0, mask_h)
    scaled_xrt = np.clip(scaled_xrt, 0, mask_w)
    scaled_ybt = np.clip(scaled_ybt, 0, mask_h)

    return scaled_xlt, scaled_ytt, scaled_xrt, scaled_ybt


def limit_anchor_region_with_mask(
        slide_dimensions, mask, xlt: np.ndarray, ytt: np.ndarray, xrt: np.ndarray, ybt: np.ndarray):
    xlt = np.asarray(xlt, dtype=np.float64)
    ytt = np.asarray(ytt, dtype=np.float64)
    xrt = np.asarray(xrt, dtype=np.float64)
    ybt = np.asarray(ybt, dtype=np.float64)

    if xlt.shape != ytt.shape or xlt.shape != xrt.shape or xlt.shape != ybt.shape:
        raise ValueError(
            'limit_anchor_region_with_mask expects ndarray inputs with matching shapes, '
            f'got {xlt.shape=}, {ytt.shape=}, {xrt.shape=}, {ybt.shape=}',
        )

    scaled_xlt, scaled_ytt, scaled_xrt, scaled_ybt = scale_region_coordinates(
        slide_dimensions, mask, xlt, ytt, xrt, ybt)
    out_xlt = np.round(xlt).astype(np.int64)
    out_ytt = np.round(ytt).astype(np.int64)
    out_xrt = np.round(xrt).astype(np.int64)
    out_ybt = np.round(ybt).astype(np.int64)

    base_w = float(slide_dimensions['base_size_x'])
    base_h = float(slide_dimensions['base_size_y'])
    mask_h, mask_w = mask.shape[:2]
    base_size_x = int(slide_dimensions['base_size_x'])
    base_size_y = int(slide_dimensions['base_size_y'])

    for idx in np.ndindex(xlt.shape):
        mask_region = mask[
            int(scaled_ytt[idx]):int(scaled_ybt[idx]),
            int(scaled_xlt[idx]):int(scaled_xrt[idx]),
        ]

        # No overlap with mask grid or empty region: keep original region.
        if mask_region.size == 0:
            continue

        non_masked = np.argwhere(mask_region > 0)
        if non_masked.size == 0:
            continue

        min_row = int(non_masked[:, 0].min())
        max_row = int(non_masked[:, 0].max())
        min_col = int(non_masked[:, 1].min())
        max_col = int(non_masked[:, 1].max())

        tight_scaled_xlt = int(scaled_xlt[idx]) + min_col
        tight_scaled_ytt = int(scaled_ytt[idx]) + min_row
        tight_scaled_xrt = int(scaled_xlt[idx]) + max_col + 1
        tight_scaled_ybt = int(scaled_ytt[idx]) + max_row + 1

        # Convert mask-space tight box back to full-resolution coordinates.
        full_xlt = int(np.floor(tight_scaled_xlt * base_w / mask_w))
        full_ytt = int(np.floor(tight_scaled_ytt * base_h / mask_h))
        full_xrt = int(np.ceil(tight_scaled_xrt * base_w / mask_w))
        full_ybt = int(np.ceil(tight_scaled_ybt * base_h / mask_h))

        full_xlt = int(np.clip(full_xlt, 0, base_size_x))
        full_ytt = int(np.clip(full_ytt, 0, base_size_y))
        full_xrt = int(np.clip(full_xrt, 0, base_size_x))
        full_ybt = int(np.clip(full_ybt, 0, base_size_y))

        # Guard against degenerate rectangles.
        if full_xrt <= full_xlt:
            full_xrt = min(full_xlt + 1, base_size_x)
        if full_ybt <= full_ytt:
            full_ybt = min(full_ytt + 1, base_size_y)

        out_xlt[idx] = full_xlt
        out_ytt[idx] = full_ytt
        out_xrt[idx] = full_xrt
        out_ybt[idx] = full_ybt

    return out_xlt, out_ytt, out_xrt, out_ybt


def dynamic_transform_scale_v3(read_kwargs: np.ndarray, slide_dimensions: dict, tile_size: dict,
                               anchor_mm: float = 0.0001, min_mm: float = 0.00025, max_mm: float = 0.0005, mask: Optional[np.ndarray] = None):
    xlt = read_kwargs[:, 6]
    ytt = read_kwargs[:, 4]
    xrt = read_kwargs[:, 7]
    ybt = read_kwargs[:, 5]
    mm_x = read_kwargs[:, 9]
    mm_y = read_kwargs[:, 8]

    dynamic_mm = np.random.random() * (max_mm - min_mm) + min_mm

    # Needs to give dictionary for scaling region
    dynamic_scale = {
        'mm_x': dynamic_mm,
        'mm_y': dynamic_mm,
    }

    conv_mm_x = dynamic_scale['mm_x'] / slide_dimensions['base_mm_x']
    conv_mm_y = dynamic_scale['mm_y'] / slide_dimensions['base_mm_y']

    width = np.ceil(tile_size['width'] * conv_mm_x).astype(np.int64)
    height = np.ceil(tile_size['height'] * conv_mm_y).astype(np.int64)

    center_x = np.round((xlt + xrt) / 2)
    center_y = np.round((ytt + ybt) / 2)

    # If dynamic mm is less than anchor mm, we need to define a new region
    # based on the anchor region
    if dynamic_mm < anchor_mm:
        # define anchor region based on center from read_kwargs
        anchor_conv_mm_x = slide_dimensions['base_mm_x'] / anchor_mm
        anchor_conv_mm_y = slide_dimensions['base_mm_y'] / anchor_mm

        anchor_width = np.ceil(slide_dimensions['tile_size'][0] * anchor_conv_mm_x).astype(np.int64)
        anchor_height = np.ceil(
            slide_dimensions['tile_size'][1] *
            anchor_conv_mm_y).astype(
            np.int64)

        anchor_xlt = np.round(center_x - (anchor_width / 2)).astype(np.int64)
        anchor_ytt = np.round(center_y - (anchor_height / 2)).astype(np.int64)
        anchor_xrt = anchor_xlt + anchor_width
        anchor_ybt = anchor_ytt + anchor_height

        if mask is not None:
            anchor_xlt, anchor_ytt, anchor_xrt, anchor_ybt = limit_anchor_region_with_mask(
                slide_dimensions, mask, anchor_xlt, anchor_ytt, anchor_xrt, anchor_ybt)

        center_x_min = anchor_xlt + (width / 2)
        center_y_min = anchor_ytt + (height / 2)
        center_x_max = anchor_xrt - (width / 2)
        center_y_max = anchor_ybt - (height / 2)

        center_dx_left = np.minimum(center_x_min, 0)
        center_dx_right = np.maximum(center_x_max - slide_dimensions['base_size_x'], 0)
        center_dy_top = np.minimum(center_y_min, 0)
        center_dy_bottom = np.maximum(center_y_max - slide_dimensions['base_size_y'], 0)

        center_x_min = center_x_min - center_dx_left
        center_y_min = center_y_min - center_dy_top
        center_x_max = center_x_max - center_dx_right
        center_y_max = center_y_max - center_dy_bottom

        random_center_x_range = np.floor(
            np.random.random() * (center_x_max - center_x_min) + center_x_min)
        random_center_y_range = np.floor(
            np.random.random() * (center_y_max - center_y_min) + center_y_min)

        xlt = np.floor(random_center_x_range - (width / 2)).astype(np.int64)
        ytt = np.floor(random_center_y_range - (height / 2)).astype(np.int64)
        xrt = xlt + width
        ybt = ytt + height
    else:
        # If dynamic mm is greater than anchor mm, we need to define a new region based
        # on the original center region which should always be within the bounds of the slide
        xlt = np.round(center_x - (width / 2)).astype(np.int64)
        ytt = np.round(center_y - (height / 2)).astype(np.int64)
        xrt = xlt + width
        ybt = ytt + height

    # Keep region size constant by shifting the full window into bounds.
    dx_left = np.minimum(xlt, 0)
    xlt = xlt - dx_left
    xrt = xrt - dx_left

    dy_top = np.minimum(ytt, 0)
    ytt = ytt - dy_top
    ybt = ybt - dy_top

    dx_right = np.maximum(xrt - slide_dimensions['base_size_x'], 0)
    xlt = xlt - dx_right
    xrt = xrt - dx_right

    dy_bottom = np.maximum(ybt - slide_dimensions['base_size_y'], 0)
    ytt = ytt - dy_bottom
    ybt = ybt - dy_bottom

    mm_x = np.repeat(dynamic_mm, read_kwargs.shape[0])
    mm_y = np.repeat(dynamic_mm, read_kwargs.shape[0])

    return xlt, ytt, xrt, ybt, mm_x, mm_y, tile_size, dynamic_scale, conv_mm_x, conv_mm_y


def dynamic_transform_scale_v2_wrapper(read_kwargs: np.ndarray, slide_dimensions: dict):
    return dynamic_transform_scale_v2(read_kwargs, slide_dimensions)


def main():
    test_image_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'
    source = large_image.open(test_image_path)

    os.makedirs('/scr/arosado/performance/eager/dynamic/images', exist_ok=True)

    def save_image(images: np.ndarray, x: int, y: int):
        if x > -1 and y > -1:
            plt.imsave(f'/scr/arosado/performance/eager/dynamic/images/image_{x}_{y}.png', images)
        return images

    size_random = 1500

    count = 0

    thumbnail, _ = source.getThumbnail(width=1024, format='numpy')

    mask, _ = get_tissue_mask_with_background_elimination(thumbnail)

    def dynamic_transform_scale_v3_wrapper(read_kwargs: np.ndarray, slide_dimensions: dict):
        return dynamic_transform_scale_v3(read_kwargs, slide_dimensions, tile_size={
                                          'width': 256, 'height': 256}, mask=mask)

    eager_iterator = source.eagerIterator(
        tile_size={
            'width': 224,
            'height': 224},
        scale={
            'mm_x': 0.0007,
            'mm_y': 0.0007},
        mask=mask,
        transform_scale=dynamic_transform_scale_v3_wrapper,
        transform=save_image,
        batch=1000)
    # eager_iterator = source.eagerIterator(scale={'mm_x': 0.0025, 'mm_y': 0.0025})
    for batch in eager_iterator:
        mm = batch['tile'].mm_view()
        images = batch['tile'].view()

        count += images.shape[0]
        # print("mm: %s" % mm)
        # print(batch)

    print(f'Final count: {count}')
    print(f'Expected count: {size_random}')



if __name__ == '__main__':
    main()
