import numpy as np
import pytest
from PIL import Image

from large_image.tilesource.eager_utils import eager_fn
from large_image.tilesource.eageriterator import (
    _EAGER_FN_TRANSFORM_SCALE_SENTINEL,
    _EAGER_FN_TRANSFORM_SENTINEL,
    EagerIterator,
)


pytestmark = pytest.mark.singular


REGIONS = np.array([[0, 0, 32, 32]], dtype=np.float32)


def identity_transform(image):
    return image


def invalid_transform_output(image):
    return []


def transform_scale_with_one_arg(read_kwargs):
    return read_kwargs


def invalid_transform_scale_output(read_kwargs, slide_dimensions):
    values = np.zeros(read_kwargs.shape[0], dtype=np.float32)
    tile_size = dict(slide_dimensions['_tile_size'])
    target_scale = {'magnification': slide_dimensions['target_magnification']}
    return (
        values.tolist(),
        values,
        values,
        values,
        values,
        values,
        tile_size,
        target_scale,
        1,
        1,
    )


def transform_scale_with_mm_scale_for_mag_mode(read_kwargs, slide_dimensions):
    values = np.zeros(read_kwargs.shape[0], dtype=np.float32)
    tile_size = dict(slide_dimensions['_tile_size'])
    target_scale = {
        'mm_x': slide_dimensions['target_mm_x'],
        'mm_y': slide_dimensions['target_mm_y'],
    }
    return values, values, values, values, values, values, tile_size, target_scale, 1, 1


@pytest.mark.parametrize(
    ('kwargs', 'match'),
    [
        pytest.param(
            {'workers': 1},
            'at least 2 workers',
            id='worker-count',
        ),
        pytest.param(
            {'output_mode': 'regions'},
            'Regions must be a numpy array',
            id='regions-mode-without-regions',
        ),
        pytest.param(
            {'output_mode': 'tiles', 'regions': REGIONS},
            "output_mode set to 'tiles' but regions provided",
            id='tiles-mode-with-regions',
        ),
        pytest.param(
            {'output_mode': 'regions', 'regions': REGIONS},
            'pad_mode cannot be wsi_edge',
            id='regions-mode-default-pad-mode',
        ),
        pytest.param(
            {'scale': {'mm_x': 0.001}},
            "scale must have both 'mm_x' and 'mm_y'",
            id='scale-missing-mm-y',
        ),
        pytest.param(
            {'scale': {'magnification': 20, 'mm_x': 0.001, 'mm_y': 0.001}},
            "scale cannot have both 'magnification' and 'mm_x' or 'mm_y'",
            id='scale-mixes-magnification-and-mm',
        ),
        pytest.param(
            {'tile_size': {'width': 64}},
            "tile_size must be a dictionary with both 'width' and 'height'",
            id='tile-size-missing-height',
        ),
        pytest.param(
            {'tile_size': {'width': 0, 'height': 64}},
            'tile_size width and height must be greater than 0',
            id='tile-size-not-positive',
        ),
        pytest.param(
            {'tile_overlap': {'x': 1}},
            'tile_overlap must be a dictionary with both',
            id='tile-overlap-missing-axis',
        ),
        pytest.param(
            {'tile_overlap': {'x': 1, 'y': 0.5}},
            'tile_overlap x and y must be both integers or both floats',
            id='tile-overlap-mixed-types',
        ),
        pytest.param(
            {'tile_overlap': {'x': -1, 'y': -1}},
            'tile_overlap x and y must be greater than or equal to 0',
            id='tile-overlap-negative',
        ),
    ],
)
def test_eager_iterator_rejects_fast_constructor_validation_args(
    datastore_svs_source,
    kwargs,
    match,
):
    with pytest.raises(ValueError, match=match):
        datastore_svs_source.eagerIterator(**kwargs)


@pytest.mark.parametrize(
    ('kwargs', 'match'),
    [
        pytest.param(
            {'mask': object()},
            'Mask must be a file path that exists or a numpy array',
            id='unsupported-mask',
        ),
        pytest.param(
            {'region': {'left': 0, 'top': 0, 'width': 1, 'height': 1}},
            "Region must be a dictionary with 'units'",
            id='region-missing-units',
        ),
        pytest.param(
            {'region': {'left': 0, 'top': 0, 'width': 1, 'units': 'base_pixels'}},
            "Region must be a dictionary with 'left', 'top', 'width', and 'height'",
            id='region-missing-dimension',
        ),
        pytest.param(
            {'region': {'left': 0, 'top': 0, 'width': 0, 'height': 1, 'units': 'base_pixels'}},
            'Region width and height must be greater than 0',
            id='region-empty',
        ),
        pytest.param(
            {'region': {'left': -1, 'top': 0, 'width': 1, 'height': 1, 'units': 'base_pixels'}},
            'Region left and top must be greater than 0',
            id='region-negative-origin',
        ),
        pytest.param(
            {'region': {'left': 0, 'top': 0, 'width': 1, 'height': 1, 'units': 'pixels'}},
            "Region units must be either 'base_pixels' or 'mag_pixels' or 'mm'",
            id='region-unsupported-units',
        ),
        pytest.param(
            {'region': {'left': 0, 'top': 0, 'width': 1, 'height': 1, 'units': 'mag_pixels'}},
            "Source scale must be provided if region units are 'mag_pixels'",
            id='region-mag-pixels-without-source-scale',
        ),
        pytest.param(
            {'output_mode': 'regions', 'regions': REGIONS, 'pad_mode': 'equal'},
            'region_size must be provided if output_mode is regions',
            id='regions-mode-missing-region-size',
        ),
        pytest.param(
            {
                'output_mode': 'regions',
                'regions': REGIONS,
                'region_size': {'width': 32, 'height': 32},
                'source_scale': {'magnification': 20},
                'pad_mode': 'equal',
            },
            'source_scale parammter must be None for regions mode',
            id='regions-mode-source-scale',
        ),
        pytest.param(
            {
                'output_mode': 'regions',
                'regions': REGIONS,
                'region_size': {'width': 32, 'height': 32},
                'region': {'left': 0, 'top': 0, 'width': 1, 'height': 1, 'units': 'base_pixels'},
                'pad_mode': 'equal',
            },
            'region parameter must be None for regions mode',
            id='regions-mode-region',
        ),
        pytest.param(
            {
                'output_mode': 'regions',
                'regions': REGIONS,
                'region_size': {'width': 16, 'height': 16},
                'pad_mode': 'equal',
            },
            'Desired region_size is smaller than needed',
            id='region-size-too-small',
        ),
        pytest.param(
            {'transform': identity_transform, 'transform_save_mode': 'base_x_y'},
            "transform_save_mode must be either 'tile_x_y' or 'region_x_y'",
            id='transform-save-mode',
        ),
        pytest.param(
            {'transform': invalid_transform_output},
            'Transform callable must accept either',
            id='transform-output-type',
        ),
        pytest.param(
            {'transform_scale': transform_scale_with_one_arg},
            'transform_scale must have two parameters',
            id='transform-scale-signature',
        ),
        pytest.param(
            {'transform_scale': invalid_transform_scale_output},
            'transform_scale must return 10 values',
            id='transform-scale-output-types',
        ),
        pytest.param(
            {'transform_scale': transform_scale_with_mm_scale_for_mag_mode},
            "transform_scale must return a dictionary with 'magnification'",
            id='transform-scale-mode',
        ),
    ],
)
def test_eager_iterator_rejects_source_backed_constructor_validation_args(
    datastore_svs_source,
    kwargs,
    match,
):
    with pytest.raises(ValueError, match=match):
        datastore_svs_source.eagerIterator(**kwargs)


def test_eager_iterator_rejects_region_outside_base_image(datastore_svs_source):
    metadata = datastore_svs_source.getMetadata()
    region = {
        'left': metadata['sizeX'],
        'top': 0,
        'width': 1,
        'height': 1,
        'units': 'base_pixels',
    }

    with pytest.raises(ValueError, match='Region left and top must be less than the image size'):
        datastore_svs_source.eagerIterator(region=region)


@pytest.mark.parametrize(
    'tile_overlap',
    [
        pytest.param({'x': 1.0, 'y': 0.5}, id='float-x'),
        pytest.param({'x': 0.5, 'y': 1.0}, id='float-y'),
    ],
)
def test_eager_iterator_rejects_fractional_overlap_that_reaches_tile_size(
    datastore_svs_source,
    tile_overlap,
):
    with pytest.raises(ValueError, match='Tile overlap must be less than the tile size'):
        datastore_svs_source.eagerIterator(tile_overlap=tile_overlap)


@pytest.mark.parametrize('axis', ['x', 'y'])
def test_eager_iterator_rejects_pixel_overlap_that_reaches_tile_size(datastore_svs_source, axis):
    metadata = datastore_svs_source.getMetadata()
    tile_overlap = {'x': 0, 'y': 0}
    tile_overlap[axis] = metadata['tileWidth' if axis == 'x' else 'tileHeight']

    with pytest.raises(ValueError, match='Tile overlap must be less than the tile size'):
        datastore_svs_source.eagerIterator(tile_overlap=tile_overlap)


def position_transform(image, x, y):
    return image


def transform_scale_raises(read_kwargs, slide_dimensions):
    msg = 'probe failed'
    raise RuntimeError(msg)


def transform_scale_missing_mm_x(read_kwargs, slide_dimensions):
    values = np.zeros(read_kwargs.shape[0], dtype=np.float32)
    tile_size = dict(slide_dimensions['_tile_size'])
    target_scale = {'mm_y': slide_dimensions['target_mm_y']}
    return values, values, values, values, values, values, tile_size, target_scale, 1, 1


def transform_scale_missing_mm_y(read_kwargs, slide_dimensions):
    values = np.zeros(read_kwargs.shape[0], dtype=np.float32)
    tile_size = dict(slide_dimensions['_tile_size'])
    target_scale = {'mm_x': slide_dimensions['target_mm_x']}
    return values, values, values, values, values, values, tile_size, target_scale, 1, 1


def test_eager_iterator_accepts_one_arg_numpy_transform(datastore_svs_source):
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0]], dtype=np.float32),
        transform=identity_transform,
        batch=1,
        prefetch=1,
        workers=2,
    )

    try:
        assert iterator.callable_arg_num == 1
        assert iterator.is_torch is False
        assert iterator.out_dims[0] == 1
    finally:
        iterator.cleanup(wait=False)
        del iterator


def test_eager_iterator_accepts_three_arg_numpy_transform(datastore_svs_source):
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0]], dtype=np.float32),
        transform=position_transform,
        transform_save_mode='region_x_y',
        batch=1,
        prefetch=1,
        workers=2,
    )

    try:
        assert iterator.callable_arg_num == 3
        assert iterator.is_torch is False
    finally:
        iterator.cleanup(wait=False)
        del iterator


def test_eager_iterator_accepts_torch_tensor_transform(datastore_svs_source):
    torch = pytest.importorskip('torch')

    def torch_transform(image):
        return torch.as_tensor(image)

    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0]], dtype=np.float32),
        transform=torch_transform,
        batch=1,
        prefetch=1,
        workers=2,
    )

    try:
        assert iterator.callable_arg_num == 1
        assert iterator.is_torch is True
    finally:
        iterator.cleanup(wait=False)
        del iterator


def test_eager_iterator_rejects_unsupported_transform_object(datastore_svs_source):
    with pytest.raises(ValueError, match='Transform must be'):
        datastore_svs_source.eagerIterator(transform=object())


@pytest.mark.parametrize(
    ('kwargs', 'match'),
    [
        pytest.param(
            {'transform_scale': transform_scale_raises},
            'Provided transform_scale test call failed',
            id='probe-raises',
        ),
        pytest.param(
            {
                'scale': {'mm_x': 0.0005, 'mm_y': 0.0005},
                'transform_scale': transform_scale_missing_mm_x,
            },
            "transform_scale must return a dictionary with units 'mm'",
            id='mm-mode-missing-mm-x',
        ),
        pytest.param(
            {
                'scale': {'mm_x': 0.0005, 'mm_y': 0.0005},
                'transform_scale': transform_scale_missing_mm_y,
            },
            "transform_scale must return a dictionary with units 'mm'",
            id='mm-mode-missing-mm-y',
        ),
    ],
)
def test_eager_iterator_rejects_additional_transform_scale_validation_args(
    datastore_svs_source,
    kwargs,
    match,
):
    with pytest.raises(ValueError, match=match):
        datastore_svs_source.eagerIterator(**kwargs)


def test_eager_iterator_accepts_existing_mask_path(datastore_svs_source, tmp_path):
    mask_path = tmp_path / 'mask.png'
    Image.fromarray(np.ones((8, 8), dtype=np.uint8) * 255).save(mask_path)

    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        mask=str(mask_path),
        batch=2,
        prefetch=1,
        workers=2,
    )

    try:
        assert iterator.get_output_image_count() == 2
    finally:
        iterator.cleanup(wait=False)
        del iterator


def test_eager_iterator_raises_stop_iteration_after_randomized_exhaustion(datastore_svs_source):
    iterator = datastore_svs_source.eagerIterator(
        tiles=np.array([[0, 0], [0, 1]], dtype=np.float32),
        randomize_chunks=True,
        seed=3,
        batch=1,
        prefetch=1,
        workers=2,
    )

    with iterator as eager_iterator:
        for _batch in eager_iterator:
            pass
        with pytest.raises(StopIteration):
            next(eager_iterator)

    del iterator


@pytest.mark.parametrize(
    ('sentinel', 'method', 'match'),
    [
        pytest.param(
            _EAGER_FN_TRANSFORM_SENTINEL,
            EagerIterator._resolve_worker_transform,
            'Eager transform not set',
            id='transform',
        ),
        pytest.param(
            _EAGER_FN_TRANSFORM_SCALE_SENTINEL,
            EagerIterator._resolve_worker_scale_data,
            'Eager transform-scale not set',
            id='transform-scale',
        ),
    ],
)
def test_eager_iterator_rejects_unset_worker_sentinel(sentinel, method, match):
    eager_fn.set_transform(None)
    eager_fn.set_transform_scale(None)
    read_kwargs = np.zeros((1, 10), dtype=np.float32)

    with pytest.raises(ValueError, match=match):
        if sentinel == _EAGER_FN_TRANSFORM_SENTINEL:
            method(sentinel)
        else:
            method(read_kwargs, {}, sentinel)


@pytest.mark.parametrize(
    'helper_call',
    [
        pytest.param(
            lambda: EagerIterator._output_slices(
                'bad-mode',
                np.array([0]),
                np.array([0]),
                np.array([1]),
                np.array([1]),
                0,
                0,
                1,
                1,
            ),
            id='output-slices',
        ),
        pytest.param(
            lambda: EagerIterator._extract_worker_tiles(
                'bad-mode',
                np.zeros((1, 1, 3), dtype=np.uint8),
                {},
                np.array([0]),
                np.array([1]),
                np.array([0]),
                np.array([1]),
                np.array([0]),
                np.array([1]),
                np.array([0]),
                np.array([1]),
                {'width': 1, 'height': 1},
                None,
                'equal',
                'default',
            ),
            id='extract-worker-tiles',
        ),
        pytest.param(
            lambda: EagerIterator._is_no_scale_read({'scale_mode': 'bad-mode'}, {}),
            id='is-no-scale-read',
        ),
    ],
)
def test_eager_iterator_rejects_unsupported_worker_helper_modes(helper_call):
    with pytest.raises(ValueError, match='not supported|Invalid mode'):
        helper_call()


def test_eager_iterator_worker_bounds_reject_negative_coordinates():
    bounds = {'xr': -1, 'yr': 0, 'xrmax': 1, 'ybmax': 1}

    with pytest.raises(UserWarning, match='Negative coordinates'):
        EagerIterator._validate_worker_bounds('tiles', bounds, {}, np.zeros((1, 10)))


def test_eager_iterator_worker_bounds_reject_regions_beyond_image_size():
    bounds = {'xr': 0, 'yr': 0, 'xrmax': 11, 'ybmax': 5}
    slide_dimensions = {'base_size_x': 10, 'base_size_y': 10}

    with pytest.raises(UserWarning, match='Coordinates > image size'):
        EagerIterator._validate_worker_bounds(
            'regions', bounds, slide_dimensions, np.zeros((1, 10)),
        )


@pytest.mark.parametrize(
    ('target_scale', 'expected_no_scale'),
    [
        pytest.param({'mm_x': 0.25, 'mm_y': 0.25}, True, id='mm-base-scale'),
        pytest.param({'mm_x': 0.5, 'mm_y': 0.5}, False, id='mm-target-scale'),
    ],
)
def test_eager_iterator_chunk_read_kwargs_for_mm_scale(target_scale, expected_no_scale):
    slide_dimensions = {'scale_mode': 'mm', 'base_mm_x': 0.25, 'base_mm_y': 0.25}
    bounds = {
        'xr': np.array(1),
        'yr': np.array(2),
        'h': np.array(3),
        'w': np.array(4),
    }

    no_scale, kwargs = EagerIterator._chunk_read_kwargs(slide_dimensions, target_scale, bounds)

    assert no_scale is expected_no_scale
    if expected_no_scale:
        assert kwargs['region']['left'] == 1
        assert 'sourceRegion' not in kwargs
    else:
        assert kwargs['sourceRegion']['left'] == 1
        assert kwargs['targetScale'] == target_scale
