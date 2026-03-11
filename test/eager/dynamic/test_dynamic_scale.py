import large_image

import numpy as np

from eager.eager_helpers import generate_random_tile_indexes



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
    scale_multi = 1/(np.random.random() * (scale_range[1] - scale_range[0]) + scale_range[0])

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

def dynamic_transform_scale_v2(read_kwargs: np.ndarray, slide_dimensions: dict, min_mm: float = 0.00025, max_mm: float = 0.0005, anchor_mm: float = 0.0001):
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

    # If dynamic mm is less than anchor mm, we need to define a new region based on the anchor region
    if dynamic_mm < anchor_mm:
        # define anchor region based on center from read_kwargs
        anchor_conv_mm_x = slide_dimensions['base_mm_x'] / anchor_mm
        anchor_conv_mm_y = slide_dimensions['base_mm_y'] / anchor_mm

        anchor_width = np.ceil(slide_dimensions['tile_size'][0] * anchor_conv_mm_x).astype(np.int64)
        anchor_height = np.ceil(slide_dimensions['tile_size'][1] * anchor_conv_mm_y).astype(np.int64)

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

def dynamic_transform_scale_v2_wrapper(read_kwargs: np.ndarray, slide_dimensions: dict):
    return dynamic_transform_scale_v2(read_kwargs, slide_dimensions)


def main():
    test_image_path = "/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs"
    source = large_image.open(test_image_path)

    size_random = 1500

    tiles = generate_random_tile_indexes(source, size_random)

    count = 0

    eager_iterator = source.eagerIterator(scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tiles=tiles, transform_scale=dynamic_transform_scale_v2_wrapper, batch=1000)
    # eager_iterator = source.eagerIterator(scale={'mm_x': 0.0025, 'mm_y': 0.0025})
    for batch in eager_iterator:
        mm = batch['tile'].mm_view()
        images = batch['tile'].view()

        count += images.shape[0]
        # print("mm: %s" % mm)
        # print(batch)

    print(f"Final count: {count}")
    print(f"Expected count: {size_random}")

    pass

if __name__ == "__main__":
    main()
    pass