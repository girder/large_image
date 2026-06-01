import numpy as np

from large_image.tilesource.eager_utils.eager_image_modifications import pad_chunk_if_necessary


def test_pad_chunk_ignores_negative_padding_for_mixed_size_axes():
    chunk = np.zeros((12, 8, 3), dtype=np.uint8)
    slide_dimensions = {
        'region_right': 100,
        'region_bottom': 100,
    }

    padded = pad_chunk_if_necessary(
        slide_dimensions,
        chunk,
        np.array([0]),
        np.array([8]),
        np.array([0]),
        np.array([12]),
        10,
        6,
        pad_mode='equal',
    )

    assert padded.shape == (12, 10, 3)


def test_pad_chunk_ignores_negative_padding_for_opposite_mixed_size_axes():
    chunk = np.zeros((8, 12, 3), dtype=np.uint8)
    slide_dimensions = {
        'region_right': 100,
        'region_bottom': 100,
    }

    padded = pad_chunk_if_necessary(
        slide_dimensions,
        chunk,
        np.array([0]),
        np.array([12]),
        np.array([0]),
        np.array([8]),
        6,
        10,
        pad_mode='equal',
    )

    assert padded.shape == (10, 12, 3)
