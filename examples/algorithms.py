import numpy as np


class Labels:
    NEGATIVE = 0
    WEAK = 1
    PLAIN = 2
    STRONG = 3


def rgb_to_hsi(im):
    """
    Convert to H/S/I the R/G/B pixels in im.
    Adapted from
    https://en.wikipedia.org/wiki/HSL_and_HSV#Hue_and_chroma.
    """
    im = np.moveaxis(im, -1, 0)
    if len(im) not in (3, 4):
        msg = f'Expected 3-channel RGB or 4-channel RGBA image; received a {len(im)}-channel image'
        raise ValueError(msg)
    im = im[:3]
    hues = (
        np.arctan2(3**0.5 * (im[1] - im[2]), 2 * im[0] - im[1] - im[2]) / (2 * np.pi)
    ) % 1
    intensities = im.mean(0)
    saturations = np.where(
        intensities, 1 - im.min(0) / np.maximum(intensities, 1e-10), 0,
    )
    return np.stack([hues, saturations, intensities], -1)


def positive_pixel_count(
    data,
    hue_value=0.83,
    hue_width=0.15,
    saturation_minimum=0.05,
    intensity_upper_limit=0.95,
    intensity_lower_limit=0.05,
    intensity_weak_threshold=0.65,
    intensity_strong_threshold=0.35,
):
    image_hsi = rgb_to_hsi(data / 255)
    mask_all_positive = (
        (np.abs(((image_hsi[..., 0] - hue_value + 0.5) % 1) - 0.5) <= hue_width / 2) &
        (image_hsi[..., 1] >= saturation_minimum) &
        (image_hsi[..., 2] < intensity_upper_limit) &
        (image_hsi[..., 2] >= intensity_lower_limit)
    )
    all_positive_i = image_hsi[mask_all_positive, 2]
    mask_weak = all_positive_i >= intensity_weak_threshold
    mask_strong = all_positive_i < intensity_strong_threshold
    mask_pos = ~(mask_weak | mask_strong)

    label_image = np.full(data.shape[:-1], Labels.NEGATIVE, dtype=np.uint8)
    label_image[mask_all_positive] = (
        mask_weak * Labels.WEAK + mask_pos * Labels.PLAIN + mask_strong * Labels.STRONG
    )
    color_map = np.empty((4, 4), dtype=np.uint8)
    color_map[Labels.NEGATIVE] = 255, 255, 255, 0
    color_map[Labels.WEAK] = 60, 78, 194, 255
    color_map[Labels.PLAIN] = 221, 220, 220, 255
    color_map[Labels.STRONG] = 180, 4, 38, 255
    ppcimg = color_map[label_image]
    return ppcimg


ALGORITHM_CODES = {
    'ppc': positive_pixel_count,
}
