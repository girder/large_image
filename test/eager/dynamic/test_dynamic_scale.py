import large_image

import numpy as np

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


def main():
    test_image_path = "/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs"
    source = large_image.open(test_image_path)

    eager_iterator = source.eagerIterator(scale={'mm_x': 0.0025, 'mm_y': 0.0025}, transform_scale=dynamic_transform_scale)
    # eager_iterator = source.eagerIterator(scale={'mm_x': 0.0025, 'mm_y': 0.0025})
    for batch in eager_iterator:
        mm = batch['tile'].mm_view()
        print("mm: %s" % mm)
        print(batch)

if __name__ == "__main__":
    main()
    pass