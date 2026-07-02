import math

import numpy as np
import pytest
from PIL import Image


def identity_with_position(image, x, y):
    return image


def crop_callable_transform(image, x, y):
    return image[:32, :32, :]


def fixed_zoom_transform_scale(read_kwargs: np.ndarray, slide_dimensions: dict):
    xlt = read_kwargs[:, 6]
    ytt = read_kwargs[:, 4]
    xrt = read_kwargs[:, 7]
    ybt = read_kwargs[:, 5]

    dynamic_scale = {
        'mm_x': slide_dimensions['target_mm_x'] * 2,
        'mm_y': slide_dimensions['target_mm_y'] * 2,
    }
    conv_mm_x = dynamic_scale['mm_x'] / slide_dimensions['base_mm_x']
    conv_mm_y = dynamic_scale['mm_y'] / slide_dimensions['base_mm_y']

    width = math.ceil(slide_dimensions['tile_size'][0] * conv_mm_x)
    height = math.ceil(slide_dimensions['tile_size'][1] * conv_mm_y)
    center_x = np.round((xlt + xrt) / 2).astype(np.int64)
    center_y = np.round((ytt + ybt) / 2).astype(np.int64)

    xlt = center_x - width // 2
    ytt = center_y - height // 2
    xrt = xlt + width
    ybt = ytt + height

    xlt = np.maximum(xlt, 0)
    ytt = np.maximum(ytt, 0)
    xrt = np.minimum(xrt, slide_dimensions['base_size_x'])
    ybt = np.minimum(ybt, slide_dimensions['base_size_y'])

    mm_x = np.full(read_kwargs.shape[0], dynamic_scale['mm_x'])
    mm_y = np.full(read_kwargs.shape[0], dynamic_scale['mm_y'])
    tile_size = {
        'width': slide_dimensions['tile_size'][0],
        'height': slide_dimensions['tile_size'][1],
    }
    return xlt, ytt, xrt, ybt, mm_x, mm_y, tile_size, dynamic_scale, conv_mm_x, conv_mm_y


def sparse_regions(metadata, region_size=(96, 80)):
    height, width = region_size
    return np.array(
        [
            [metadata['sizeY'] // 4, metadata['sizeX'] // 5, height, width],
        ],
        dtype=np.float32,
    )


def dense_regions(metadata, region_size=(96, 80)):
    height, width = region_size
    center_top = metadata['sizeY'] // 2
    center_left = metadata['sizeX'] // 2
    offsets = np.array([[-48, -48]], dtype=np.float32)
    regions = np.zeros((offsets.shape[0], 4), dtype=np.float32)
    regions[:, 0] = center_top + offsets[:, 0]
    regions[:, 1] = center_left + offsets[:, 1]
    regions[:, 2] = height
    regions[:, 3] = width
    return regions


def read_all_batches(iterator):
    count = 0
    shapes = []
    positions = []
    with iterator as eager_iterator:
        for batch in eager_iterator:
            shared_tiles = batch['tile']
            tiles = shared_tiles.view().copy()
            shared_tiles.close()

            count += tiles.shape[0]
            shapes.append(tiles.shape)
            positions.extend(
                zip(
                    batch['tile_position']['region_y'].astype(int).tolist(),
                    batch['tile_position']['region_x'].astype(int).tolist(),
                    strict=False,
                ),
            )
    return count, shapes, positions


@pytest.mark.singular
@pytest.mark.parametrize('region_builder', [sparse_regions, dense_regions], ids=['sparse', 'dense'])
def test_eager_regions_from_paper_region_patterns(datastore_svs_source, region_builder):
    metadata = datastore_svs_source.getMetadata()
    regions = region_builder(metadata)

    iterator = datastore_svs_source.eagerIterator(
        output_mode='regions',
        regions=regions,
        region_size={'width': 80, 'height': 96},
        pad_mode='equal',
        chunk_mult=2,
        batch=3,
        prefetch=1,
        workers=2,
    )

    assert iterator.get_output_image_count() == len(regions)
    count, shapes, _positions = read_all_batches(iterator)
    del iterator

    assert count == len(regions)
    assert shapes[-1][0] == 1
    assert all(shape[1:] == (96, 80, 3) for shape in shapes)


@pytest.mark.singular
def test_eager_region_padding_allows_smaller_requested_regions(datastore_svs_source):
    regions = np.array([[64, 80, 24, 32], [96, 128, 48, 40]], dtype=np.float32)

    iterator = datastore_svs_source.eagerIterator(
        output_mode='regions',
        regions=regions,
        region_size={'width': 64, 'height': 64},
        pad_mode='equal',
        pad_fill_mode='white',
        batch=2,
        prefetch=1,
        workers=2,
    )

    count, shapes, _positions = read_all_batches(iterator)
    del iterator

    assert count == len(regions)
    assert shapes == [(2, 64, 64, 3)]


@pytest.mark.singular
def test_eager_explicit_tiles_return_subset_and_partial_final_batch(datastore_svs_source):
    tiles = np.array([[0, 0], [0, 1], [1, 0], [1, 1], [2, 2]], dtype=np.float32)

    iterator = datastore_svs_source.eagerIterator(
        tiles=tiles,
        batch=2,
        prefetch=1,
        workers=2,
    )

    count, shapes, positions = read_all_batches(iterator)
    del iterator

    assert count == len(tiles)
    assert [shape[0] for shape in shapes] == [2, 2, 1]
    assert set(positions) == set(map(tuple, tiles.astype(int).tolist()))


@pytest.mark.singular
def test_eager_tile_overlap_matches_planned_tile_indexes(datastore_svs_source):
    metadata = datastore_svs_source.getMetadata()
    region = {
        'left': 0,
        'top': 0,
        'width': min(metadata['sizeX'], metadata['tileWidth'] * 4),
        'height': min(metadata['sizeY'], metadata['tileHeight'] * 4),
        'units': 'base_pixels',
    }
    overlap = {'x': metadata['tileWidth'] // 2, 'y': metadata['tileHeight'] // 2}

    iterator = datastore_svs_source.eagerIterator(
        region=region,
        tile_overlap=overlap,
        batch=64,
        prefetch=16,
        workers=16,
    )
    from large_image.tilesource.eager_utils.eager_wsi_operations import \
        return_relevant_tile_indexes_for_slide_dim

    expected = len(return_relevant_tile_indexes_for_slide_dim(iterator.slide_dimensions, overlap))

    count, shapes, _positions = read_all_batches(iterator)
    del iterator

    assert count == expected
    assert expected > 4
    assert all(shape[1:] == (metadata['tileHeight'], metadata['tileWidth'], 3) for shape in shapes)


@pytest.mark.singular
def test_eager_mask_filters_explicit_tile_candidates(datastore_svs_source):
    metadata = datastore_svs_source.getMetadata()
    mask = np.zeros((4096, 4096), dtype=np.uint8)
    first_tile_mask_width = max(
        1,
        round(mask.shape[1] * metadata['tileWidth'] / metadata['sizeX']),
    )
    first_tile_mask_height = max(
        1,
        round(mask.shape[0] * metadata['tileHeight'] / metadata['sizeY']),
    )
    mask[:first_tile_mask_height, :first_tile_mask_width] = 255

    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        mask=mask,
        area_threshold=0.5,
        threshold_mask=1,
        batch=2,
        prefetch=1,
        workers=2,
    )

    count, shapes, positions = read_all_batches(iterator)
    del iterator

    assert count == 1
    assert shapes == [(1, metadata['tileHeight'], metadata['tileWidth'], 3)]
    assert positions == [(0, 0)]


@pytest.mark.singular
def test_eager_mask_path_filters_explicit_tile_candidates(datastore_svs_source, tmp_path):
    metadata = datastore_svs_source.getMetadata()
    mask = np.zeros((4096, 4096), dtype=np.uint8)
    first_tile_mask_width = max(
        1,
        round(mask.shape[1] * metadata['tileWidth'] / metadata['sizeX']),
    )
    first_tile_mask_height = max(
        1,
        round(mask.shape[0] * metadata['tileHeight'] / metadata['sizeY']),
    )
    mask[:first_tile_mask_height, :first_tile_mask_width] = 255
    mask_path = tmp_path / 'mask.png'
    Image.fromarray(mask).save(mask_path)

    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        mask=mask_path,
        area_threshold=0.5,
        threshold_mask=1,
        batch=2,
        prefetch=1,
        workers=2,
    )

    count, shapes, positions = read_all_batches(iterator)
    del iterator

    assert count == 1
    assert shapes == [(1, metadata['tileHeight'], metadata['tileWidth'], 3)]
    assert positions == [(0, 0)]


@pytest.mark.singular
def test_eager_nchw_callable_transform_uses_tile_coordinates(datastore_svs_source):
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        transform=crop_callable_transform,
        nchw=True,
        batch=2,
        prefetch=1,
        workers=2,
    )

    with iterator as eager_iterator:
        batch = next(eager_iterator)
        shared_tiles = batch['tile']
        tiles = shared_tiles.view().copy()
        shared_tiles.close()

    del iterator

    assert tiles.shape == (2, 3, 32, 32)


@pytest.mark.singular
def test_eager_transform_save_mode_can_pass_region_coordinates(datastore_svs_source):
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        transform=identity_with_position,
        transform_save_mode='region_x_y',
        batch=2,
        prefetch=1,
        workers=2,
    )

    count, shapes, _positions = read_all_batches(iterator)
    del iterator

    assert count == 2
    assert len(shapes) == 1


@pytest.mark.singular
def test_eager_randomized_chunks_are_seed_reproducible(datastore_svs_source):
    kwargs = dict(
        tiles=np.array([[0, 0], [0, 1], [1, 0], [1, 1], [2, 2], [2, 3]], dtype=np.float32),
        randomize_chunks=True,
        seed=11,
        batch=2,
        prefetch=1,
        workers=2,
    )
    iterator_a = datastore_svs_source.eagerIterator(**kwargs)
    iterator_b = datastore_svs_source.eagerIterator(**kwargs)

    try:
        chunks_a = [chunk.tolist() for chunk in iterator_a.read_kwargs]
        chunks_b = [chunk.tolist() for chunk in iterator_b.read_kwargs]
    finally:
        iterator_a.cleanup(wait=False)
        iterator_b.cleanup(wait=False)
        del iterator_a
        del iterator_b

    assert chunks_a == chunks_b


@pytest.mark.singular
@pytest.mark.parametrize('magnification_type', [int, float], ids=['int', 'float'])
def test_eager_scale_accepts_numeric_magnification(datastore_svs_source, magnification_type):
    metadata = datastore_svs_source.getMetadata()
    magnification = magnification_type(metadata['magnification'])

    iterator = datastore_svs_source.eagerIterator(
        scale={'magnification': magnification},
        tiles=np.array([[0, 0]], dtype=np.float32),
        tile_size={'width': 64, 'height': 64},
        batch=1,
        prefetch=1,
        workers=2,
    )

    count, shapes, positions = read_all_batches(iterator)

    assert iterator.slide_dimensions['scale_mode'] == 'mag'
    assert iterator.slide_dimensions['target_magnification'] == float(magnification)
    assert count == 1
    assert shapes == [(1, 64, 64, 3)]
    assert positions == [(0, 0)]

    del iterator


@pytest.mark.singular
def test_eager_transform_scale_populates_runtime_mm_metadata(datastore_svs_source):
    metadata = datastore_svs_source.getMetadata()
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[2, 2], [2, 3]], dtype=np.float32),
        tile_size={'width': 64, 'height': 64},
        scale={'mm_x': metadata['mm_x'], 'mm_y': metadata['mm_y']},
        transform_scale=fixed_zoom_transform_scale,
        batch=2,
        prefetch=1,
        workers=2,
    )
    expected_mm_x = iterator.slide_dimensions['target_mm_x'] * 2
    expected_mm_y = iterator.slide_dimensions['target_mm_y'] * 2

    with iterator as eager_iterator:
        batch = next(eager_iterator)
        shared_tiles = batch['tile']
        tiles = shared_tiles.view().copy()
        mm = shared_tiles.mm_view().copy()
        shared_tiles.close()

    del iterator

    assert tiles.shape == (2, 64, 64, 3)
    assert np.allclose(mm[:, 0], expected_mm_y)
    assert np.allclose(mm[:, 1], expected_mm_x)
