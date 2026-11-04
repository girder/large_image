import multiprocessing
import os
import sqlite3
import subprocess
import zipfile
from datetime import datetime, timezone
from multiprocessing.pool import Pool, ThreadPool
from os import sys

import large_image_source_test
import large_image_source_zarr
import numpy as np
import pytest
from PIL import Image

import large_image
from large_image.constants import NEW_IMAGE_PATH_FLAG
from large_image.exceptions import TileSourceError
from large_image.tilesource.resample import ResampleMethod

TMP_DIR = 'tmp/zarr_sink'
FILE_TYPES = [
    'tiff',
    'sqlite',
    'db',
    'zip',
    'zarr',
]


def metadataFile(sink):
    """
    Get the name of the group metadata file that a sink writes.
    """
    return 'zarr.json' if sink._zarrFormat == 3 else '.zattrs'


def omeMetadata(source):
    """
    Get the OME metadata dictionary of a zarr source, regardless of whether
    it is under an "ome" key.
    """
    base = source.getInternalMetadata()['zarr']['base']
    return base.get('ome', base)


def copyFromSource(source, sink):
    metadata = source.getMetadata()
    for frame in metadata.get('frames', []):
        for tile in source.tileIterator(frame=frame['Frame'], format='numpy'):
            t = tile['tile']
            x, y = tile['x'], tile['y']
            kwargs = {
                'z': frame['IndexZ'],
                'c': frame['IndexC'],
            }
            sink.addTile(t, x=x, y=y, **kwargs)


def testNew():
    sink = large_image_source_zarr.new()
    assert sink.metadata['levels'] == 0
    assert sink.getRegion(format='numpy')[0].shape[:2] == (0, 0)


def testBasicAddTile():
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((10, 10)), 0, 0)
    sink.addTile(np.random.random((10, 10, 2)), 10, 0)

    metadata = sink.getMetadata()
    assert metadata.get('levels') == 1
    assert metadata.get('sizeX') == 20
    assert metadata.get('sizeY') == 10
    assert metadata.get('bandCount') == 2
    assert metadata.get('dtype') == 'float64'


def testAddTileWithMask():
    sink = large_image_source_zarr.new()
    tile0 = np.random.random((10, 10))
    sink.addTile(tile0, 0, 0)
    orig = sink.getRegion(format='numpy')[0]
    tile1 = np.random.random((10, 10))
    sink.addTile(tile1, 0, 0, mask=np.random.random((10, 10)) > 0.5)
    cur = sink.getRegion(format='numpy')[0]
    assert (tile0 == orig[:, :, 0]).all()
    assert not (tile1 == orig[:, :, 0]).all()
    assert not (tile0 == cur[:, :, 0]).all()
    assert not (tile1 == cur[:, :, 0]).all()


def testAddTileWithLevel():
    sink = large_image_source_zarr.new()
    tile0 = np.random.random((100, 100))
    sink.addTile(tile0, 0, 0)
    arrays = dict(sink._zarr.arrays())
    assert arrays.get('0') is not None
    assert arrays.get('0').shape == (100, 100, 1)

    tile1 = np.random.random((10, 10))
    sink.addTile(tile1, 0, 0, level=1)
    arrays = dict(sink._zarr.arrays())
    assert arrays.get('0') is not None
    assert arrays.get('0').shape == (100, 100, 1)
    assert arrays.get('1') is not None
    assert arrays.get('1').shape == (10, 10, 1)

    tile1 = np.random.random((100, 100))
    sink.addTile(tile1, 0, 100)
    arrays = dict(sink._zarr.arrays())
    assert arrays.get('0') is not None
    assert arrays.get('0').shape == (200, 100, 1)
    # previously written levels should be cleared after changing level 0 data
    assert arrays.get('1') is None


def testNoSamplesAxis(tmp_path):
    output_file = tmp_path / 'test.tiff'
    sink = large_image_source_zarr.new()
    data = np.zeros((4, 1040, 1388))
    sink.addTile(data, 0, 0, axes=['c', 'y', 'x'])
    sink.write(output_file)
    assert sink.metadata.get('bandCount') == 1


def testExtraAxis():
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((256, 256)), 0, 0, z=1)
    metadata = sink.getMetadata()
    assert metadata.get('bandCount') == 1
    assert len(metadata.get('frames')) == 2


def testXYAxis():
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((256, 256)), 0, 0, xy=1)
    metadata = sink.getMetadata()
    assert metadata['IndexStride']['IndexXY'] == 1


def testXLength1():
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((1, 1, 1)), x=0, y=138)
    sink.addTile(np.zeros((1, 1, 1)), x=0, y=138)
    metadata = sink.getMetadata()
    assert metadata.get('sizeX') == 1


def testMultiFrameAxes():
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((256, 256)), 0, 0, q=1)
    assert sink.metadata.get('IndexRange') == dict(IndexQ=2)
    sink.addTile(np.random.random((256, 256)), 0, 0, r=1)
    assert sink.metadata.get('IndexRange') == dict(IndexQ=2, IndexR=2)


@pytest.mark.parametrize('file_type', FILE_TYPES)
def testCrop(file_type, tmp_path):
    output_file = tmp_path / f'test.{file_type}'
    sink = large_image_source_zarr.new()

    # add tiles with some overlap
    sink.addTile(np.random.random((10, 10)), 0, 0)
    sink.addTile(np.random.random((10, 10)), 8, 0)
    sink.addTile(np.random.random((10, 10)), 0, 8)
    sink.addTile(np.random.random((10, 10)), 8, 8)

    region, _ = sink.getRegion(format='numpy')
    shape = region.shape
    assert shape == (18, 18, 1)

    sink.crop = (2, 2, 10, 10)

    # crop only applies when using write
    sink.write(output_file)
    if file_type == 'zarr':
        output_file /= metadataFile(sink)
    written = large_image.open(output_file)
    region, _ = written.getRegion(format='numpy')
    shape = region.shape
    assert shape == (10, 10, 1)


@pytest.mark.parametrize('file_type', FILE_TYPES)
def testImageCopySmallFileTypes(file_type, tmp_path):
    output_file = tmp_path / f'test.{file_type}'
    sink = large_image_source_zarr.new()
    source = large_image_source_test.TestTileSource(
        fractal=True,
        tileWidth=128,
        tileHeight=128,
        sizeX=512,
        sizeY=1024,
        frames='c=2,z=3',
    )
    copyFromSource(source, sink)

    metadata = sink.getMetadata()
    assert metadata.get('sizeX') == 512
    assert metadata.get('sizeY') == 1024
    assert metadata.get('dtype') == 'uint8'
    assert metadata.get('levels') == 2
    assert metadata.get('bandCount') == 3
    assert len(metadata.get('frames')) == 6

    sink.write(output_file)
    if file_type == 'zarr':
        output_file /= metadataFile(sink)
    written = large_image.open(output_file)

    new_metadata = written.getMetadata()
    assert new_metadata.get('sizeX') == 512
    assert new_metadata.get('sizeY') == 1024
    assert new_metadata.get('dtype') == 'uint8'
    assert new_metadata.get('levels') == 2 or new_metadata.get('levels') == 3
    assert new_metadata.get('bandCount') == 3
    assert len(new_metadata.get('frames')) == 6


@pytest.mark.parametrize('resample_method', [
    ResampleMethod.PIL_LANCZOS,
    ResampleMethod.NP_NEAREST,
])
def testImageCopySmallMultiband(resample_method, tmp_path):
    output_file = tmp_path / f'test_{resample_method}.db'
    sink = large_image_source_zarr.new()
    bands = (
        'red=0-255,green=0-255,blue=0-255,'
        'ir1=0-255,ir2=0-255,gray=0-255,other=0-255'
    )
    source = large_image_source_test.TestTileSource(
        fractal=True,
        tileWidth=128,
        tileHeight=128,
        sizeX=512,
        sizeY=1024,
        frames='c=2,z=3',
        bands=bands,
    )
    copyFromSource(source, sink)

    metadata = sink.getMetadata()
    assert metadata.get('sizeX') == 512
    assert metadata.get('sizeY') == 1024
    assert metadata.get('dtype') == 'uint8'
    assert metadata.get('levels') == 2
    assert metadata.get('bandCount') == 7
    assert len(metadata.get('frames')) == 6

    sink.write(output_file, resample=resample_method)
    written = large_image.open(output_file)
    new_metadata = written.getMetadata()

    assert new_metadata.get('sizeX') == 512
    assert new_metadata.get('sizeY') == 1024
    assert new_metadata.get('dtype') == 'uint8'
    assert new_metadata.get('levels') == 2 or new_metadata.get('levels') == 3
    assert new_metadata.get('bandCount') == 7
    assert len(new_metadata.get('frames')) == 6

    written_arrays = dict(written._zarr.arrays())
    assert len(written_arrays) == written.levels
    assert written_arrays.get('0') is not None
    assert written_arrays.get('0').shape == (2, 3, 1024, 512, 7)
    assert written_arrays.get('1') is not None
    assert written_arrays.get('1').shape == (2, 3, 512, 256, 7)


@pytest.mark.parametrize('resample_method', list(ResampleMethod))
def testImageCopySmallDownsampling(resample_method, tmp_path):
    output_file = tmp_path / f'test_{resample_method}.db'
    sink = large_image_source_zarr.new()
    source = large_image_source_test.TestTileSource(
        fractal=True,
        tileWidth=128,
        tileHeight=128,
        sizeX=511,
        sizeY=1023,
        frames='c=2,z=3',
    )
    copyFromSource(source, sink)

    sink.write(output_file, resample=resample_method)
    written = large_image.open(output_file)

    written_arrays = dict(written._zarr.arrays())
    assert len(written_arrays) == written.levels
    assert written_arrays.get('0') is not None
    assert written_arrays.get('0').shape == (2, 3, 1023, 511, 3)
    assert written_arrays.get('1') is not None
    assert written_arrays.get('1').shape == (2, 3, 512, 256, 3)

    sample_region, _format = written.getRegion(
        region=dict(top=252, bottom=260, left=0, right=4),
        output=dict(maxWidth=2, maxHeight=4),
        format='numpy',
    )
    assert sample_region.shape == (4, 2, 3)
    white_mask = (sample_region[..., 0] == 255).flatten().tolist()

    expected_masks = {
        ResampleMethod.PIL_NEAREST: [
            # expect any of the four variations, this will depend on version
            [True, False, True, False, True, True, True, False],  # upper left
            [True, False, True, True, True, False, True, False],  # lower left
            [True, False, False, True, True, True, False, False],  # upper right
            [False, False, True, True, False, True, True, False],  # lower right
        ],
        ResampleMethod.PIL_LANCZOS:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.PIL_BILINEAR:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.PIL_BICUBIC:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.PIL_BOX:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.PIL_HAMMING:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.NP_MEAN:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.NP_MEDIAN:
        [[True, False, True, True, True, True, True, False]],
        ResampleMethod.NP_MODE:
        [[True, False, True, True, True, True, True, False]],
        ResampleMethod.NP_MAX:
        [[True, False, True, True, True, True, True, False]],
        ResampleMethod.NP_MIN:
        [[False, False, False, False, False, False, False, False]],
        ResampleMethod.NP_NEAREST:
        [[True, False, True, False, True, True, True, False]],
        ResampleMethod.NP_MAX_COLOR:
        [[True, False, True, True, True, True, True, False]],
        ResampleMethod.NP_MIN_COLOR:
        [[False, False, False, False, False, False, False, False]],
    }

    assert white_mask in expected_masks[resample_method]


def testCropAndDownsample(tmp_path):
    output_file = tmp_path / 'cropped.db'
    sink = large_image_source_zarr.new()

    # add tiles with some overlap to multiple frames
    num_frames = 4
    num_bands = 5
    for z in range(num_frames):
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 900, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 900, z=z)

    current_arrays = dict(sink._zarr.arrays())
    assert len(current_arrays) == 1
    assert current_arrays.get('0') is not None
    assert current_arrays.get('0').shape == (num_frames, 1900, 1950, num_bands)

    sink.crop = (50, 100, 1825, 1800)
    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    written_arrays = dict(written._zarr.arrays())

    assert len(written_arrays) == written.levels
    assert written_arrays.get('0') is not None
    assert written_arrays.get('0').shape == (num_frames, 1800, 1825, num_bands)
    assert written_arrays.get('1') is not None
    assert written_arrays.get('1').shape == (num_frames, 900, 913, num_bands)
    assert written_arrays.get('2') is not None
    assert written_arrays.get('2').shape == (num_frames, 450, 456, num_bands)


def testCropToTiff(tmp_path):
    output_file = tmp_path / 'cropped.tiff'
    sink = large_image_source_zarr.new()

    # add tiles with some overlap to multiple frames
    num_frames = 1
    num_bands = 3
    for z in range(num_frames):
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 900, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 900, z=z)

    current_arrays = dict(sink._zarr.arrays())
    assert len(current_arrays) == 1
    assert current_arrays.get('0') is not None
    assert current_arrays.get('0').shape == (num_frames, 1900, 1950, num_bands)

    sink.crop = (100, 50, 1800, 1825)
    sink.write(output_file)
    source = large_image.open(output_file)
    assert source.sizeX == 1800
    assert source.sizeY == 1825


def testMetadata(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()

    description = 'random data image for testing internal metadata'
    channel_names = ['red', 'green', 'blue', 'IR', 'UV']
    channel_colors = ['FF0000', '00FF00', '0000FF', 'FFFF00', 'FF00FF']
    num_frames = 4
    num_bands = 5
    for z in range(num_frames):
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 900, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 900, z=z)

    sink.imageDescription = description
    sink.channelNames = channel_names
    sink.channelColors = channel_colors
    sink.mm_x = 5
    sink.mm_y = 5

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    assert written._is_ome

    int_metadata = written.getInternalMetadata()
    base_metadata = int_metadata.get('zarr', {}).get('base')
    assert base_metadata is not None
    if sink._zarrFormat == 3:
        # OME-Zarr 0.5 and later nest the metadata under "ome"
        assert set(base_metadata) == {'ome'}
        ome_metadata = base_metadata['ome']
        assert ome_metadata['version'] == '0.5'
        version = None
    else:
        ome_metadata = base_metadata
        version = '0.4'

    multiscales = ome_metadata.get('multiscales')
    assert multiscales is not None
    assert len(multiscales) == 1
    assert multiscales[0].get('version') == version
    assert NEW_IMAGE_PATH_FLAG in multiscales[0].get('name')

    axes = multiscales[0].get('axes')
    assert axes is not None
    assert len(axes) == 4
    assert {'name': 'z'} in axes
    assert {'name': 'y', 'type': 'space', 'unit': 'millimeter'} in axes
    assert {'name': 'x', 'type': 'space', 'unit': 'millimeter'} in axes
    assert {'name': 's', 'type': 'channel'} in axes

    datasets = multiscales[0].get('datasets')
    assert len(datasets) == 3
    for i, d in enumerate(datasets):
        assert d.get('path') == str(i)
        coord_transforms = d.get('coordinateTransformations')
        assert coord_transforms is not None
        assert len(coord_transforms) == 1
        assert coord_transforms[0].get('type') == 'scale'
        assert coord_transforms[0].get('scale') == [
            1.0, 5 * 2 ** i, 5 * 2 ** i, 1.0,
        ]

    nested_metadata = multiscales[0].get('metadata')
    assert nested_metadata is not None
    assert nested_metadata.get('description') == description
    assert nested_metadata.get('kwargs', {}).get('multichannel')

    omero = ome_metadata.get('omero')
    assert omero is not None
    assert omero.get('id') == 1
    assert omero.get('version') == version
    assert NEW_IMAGE_PATH_FLAG in omero.get('name')

    channels = omero.get('channels')
    assert channels is not None
    assert len(channels) == num_bands
    for i, c in enumerate(channels):
        assert c.get('active')
        assert c.get('coefficient') == 1
        assert c.get('color') == channel_colors[i]
        assert c.get('family') == 'linear'
        assert not c.get('inverted')
        assert c.get('label') == channel_names[i]
        assert c.get('window') == {'min': 0.0, 'max': 1.0, 'start': 0.0, 'end': 1.0}

    if sink._zarrFormat == 3:
        for _, arr in written._zarr.arrays():
            assert list(arr.metadata.dimension_names) == ['z', 'y', 'x', 's']
        # # max should be nearly 1 and min should be nearly 0
        # assert math.ceil(window.get('end')) == 1
        # assert math.ceil(window.get('max')) == 1
        # assert math.floor(window.get('start')) == 0
        # assert math.floor(window.get('min')) == 0

    rdefs = omero.get('rdefs')
    assert rdefs is not None
    assert rdefs.get('model') == 'color'
    assert rdefs.get('defaultZ') == 0


def testChannelNames(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()

    for c in range(5):
        sink.addTile(np.random.random((4, 4, 3)), c=c)

    sink.channelNames = ['a', 'b', 'c', 'd', 'e']
    sink.write(output_file)
    written = large_image.open(output_file)
    assert len(written.metadata['channels']) == 5


def testAddAssociatedImages(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()

    num_frames = 4
    num_bands = 5
    for z in range(num_frames):
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 0, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 0, 900, z=z)
        sink.addTile(np.random.random((1000, 1000, num_bands)), 950, 900, z=z)

    image_sizes = [
        (200, 300, 3),
        (400, 500, 3),
        (600, 700, 3),
    ]

    for image_size in image_sizes:
        image_data = (np.random.random(image_size) * 255).astype(np.uint8)
        img = Image.fromarray(image_data)
        sink.addAssociatedImage(img)

    original_image_list = sink.getAssociatedImagesList()

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    written_image_list = written.getAssociatedImagesList()

    for image_list in [original_image_list, written_image_list]:
        assert len(image_list) == len(image_sizes)
        for i, image_name in enumerate(image_list):
            retrieved = sink._getAssociatedImage(image_name)
            expected_size = image_sizes[i]
            assert retrieved is not None
            assert isinstance(retrieved, Image.Image)
            # PIL Image size doesn't include bands and swaps x & y
            assert retrieved.size == (expected_size[1], expected_size[0])


def _add_tile_from_seed_data(sink, seed_data, position):
    tile = seed_data[
        position['z'],
        position['y'],
        position['x'],
        position['s'],
    ]
    sink.addTile(
        tile,
        position['x'].start,
        position['y'].start,
        z=position['z'],
    )


@pytest.mark.singular
def testConcurrency(tmp_path):
    output_file = tmp_path / 'test.db'
    max_workers = 5
    tile_size = (100, 100)
    target_shape = (2, 300, 300, 5)
    tile_positions = []
    seed_data = np.random.random(target_shape)

    for z in range(target_shape[0]):
        for y in range(int(target_shape[1] / tile_size[0])):
            for x in range(int(target_shape[2] / tile_size[1])):
                tile_positions.append({
                    'z': z,
                    'y': slice(y * tile_size[0], (y + 1) * tile_size[0]),
                    'x': slice(x * tile_size[1], (x + 1) * tile_size[1]),
                    's': slice(0, target_shape[3]),
                })

    for pool_class in [Pool, ThreadPool]:
        sink = large_image_source_zarr.new()
        # allocate space by adding last tile first
        _add_tile_from_seed_data(sink, seed_data, tile_positions[-1])
        with pool_class(max_workers) as pool:
            pool.starmap(_add_tile_from_seed_data, [
                (sink, seed_data, position)
                for position in tile_positions[:-1]
            ])
        sink.write(output_file)
        written = large_image_source_zarr.open(output_file)
        written_arrays = dict(written._zarr.arrays())
        data = np.array(written_arrays.get('0'))
        assert len(written_arrays) == written.levels
        assert data is not None
        assert data.shape == seed_data.shape
        assert np.allclose(data, seed_data)


def get_expected_metadata(axis_spec, frame_shape):
    return dict(
        levels=1,
        sizeY=frame_shape[0],
        sizeX=frame_shape[1],
        bandCount=frame_shape[2],
        frames=[],
        tileWidth=512,
        tileHeight=512,
        magnification=None,
        mm_x=0,
        mm_y=0,
        dtype='float64',
        channels=[f'Band {c + 1}' for c in range(len(axis_spec['c']['values']))],
        channelmap={f'Band {c + 1}': c for c in range(len(axis_spec['c']['values']))},
        IndexRange={
            f'Index{k.upper()}': len(v['values']) for k, v in axis_spec.items()
        },
        IndexStride={
            f'Index{k.upper()}': v['stride'] for k, v in axis_spec.items()
        },
        **{
            f'Value{k.upper()}': dict(
                values=v['values'],
                units=v['units'],
                uniform=v['uniform'],
                min=min(v['values']),
                max=max(v['values']),
                datatype=v['dtype'],
            ) for k, v in axis_spec.items()
        },
    )


def compare_metadata(actual, expected):
    assert type(actual) is type(expected)
    if isinstance(actual, list):
        for i, v in enumerate(actual):
            compare_metadata(v, expected[i])
    elif isinstance(actual, dict):
        assert len(actual.keys()) == len(expected.keys())
        for k, v in actual.items():
            compare_metadata(v, expected[k])
    else:
        assert actual == expected


@pytest.mark.parametrize('use_add_tile_args', [True, False])
def testFrameValuesSmall(use_add_tile_args, tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()

    frame_shape = (300, 400, 3)
    axis_spec = dict(c=dict(
        values=['r', 'g', 'b'],
        uniform=True,
        units='channel',
        stride=1,
        dtype='str32',
    ))
    expected_metadata = get_expected_metadata(axis_spec, frame_shape)

    frame_values_shape = [
        *[len(v['values']) for v in axis_spec.values()],
        len(axis_spec),
    ]
    frame_values = np.empty(frame_values_shape, dtype=object)

    frame = 0
    index = 0
    for c, c_value in enumerate(axis_spec['c']['values']):
        add_tile_args = dict(c=c, axes=['c', 'y', 'x', 's'])
        if use_add_tile_args:
            add_tile_args.update(c_value=c_value)
        else:
            frame_values[c] = [c_value]
        random_tile = np.random.random(frame_shape)
        sink.addTile(random_tile, 0, 0, **add_tile_args)
        expected_metadata['frames'].append(
            dict(
                Frame=frame,
                Index=index,
                IndexC=c,
                ValueC=c_value,
                Channel=f'Band {c + 1}',
            ),
        )
        frame += 1
    index += 1

    if not use_add_tile_args:
        sink.frameAxes = list(axis_spec.keys())
        sink.frameValues = frame_values
    sink.frameUnits = {
        k: v['units'] for k, v in axis_spec.items()
    }
    compare_metadata(dict(sink.getMetadata()), expected_metadata)

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    compare_metadata(dict(written.getMetadata()), expected_metadata)


@pytest.mark.parametrize('use_add_tile_args', [True, False])
def testFrameValues(use_add_tile_args, tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()

    frame_shape = (300, 400, 3)
    axis_spec = dict(
        z=dict(
            values=[2, 4, 6, 8],
            uniform=True,
            units='meter',
            stride=9,
            dtype='int64',
        ),
        t=dict(
            values=[10.0, 20.0, 30.0],
            uniform=False,
            units='millisecond',
            stride=3,
            dtype='float64',
        ),
        c=dict(
            values=['r', 'g', 'b'],
            uniform=True,
            units='channel',
            stride=1,
            dtype='str32',
        ),
    )
    expected_metadata = get_expected_metadata(axis_spec, frame_shape)

    frame_values_shape = [
        *[len(v['values']) for v in axis_spec.values()],
        len(axis_spec),
    ]
    frame_values = np.empty(frame_values_shape, dtype=object)

    frame = 0
    index = 0
    for z, z_value in enumerate(axis_spec['z']['values']):
        for t, t_value in enumerate(axis_spec['t']['values']):
            if not axis_spec['t']['uniform']:
                t_value += 0.01 * z
            for c, c_value in enumerate(axis_spec['c']['values']):
                add_tile_args = dict(z=z, t=t, c=c, axes=['z', 't', 'c', 'y', 'x', 's'])
                if use_add_tile_args:
                    add_tile_args.update(z_value=z_value, t_value=t_value, c_value=c_value)
                else:
                    frame_values[z, t, c] = [z_value, t_value, c_value]
                random_tile = np.random.random(frame_shape)
                sink.addTile(random_tile, 0, 0, **add_tile_args)
                expected_metadata['frames'].append(
                    dict(
                        Frame=frame,
                        Index=index,
                        IndexZ=z,
                        ValueZ=z_value,
                        IndexT=t,
                        ValueT=t_value,
                        IndexC=c,
                        ValueC=c_value,
                        Channel=f'Band {c + 1}',
                    ),
                )
                frame += 1
            index += 1

    if not use_add_tile_args:
        sink.frameAxes = list(axis_spec.keys())
        sink.frameValues = frame_values
    sink.frameUnits = {
        k: v['units'] for k, v in axis_spec.items()
    }
    compare_metadata(dict(sink.getMetadata()), expected_metadata)

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    assert written.metadata['IndexRange'] == expected_metadata['IndexRange']
    assert written.metadata['IndexStride']['IndexC'] == 1


def testFrameValuesEdgeCases(tmp_path):
    # case 1
    ts = large_image.new()
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=0, z_value=1, c_value='DAPI')
    assert ts.metadata.get('bandCount') == 3
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=1, z=0, z_value=1, c_value='CD4')

    # case 2
    ts = large_image.new()
    ts.addTile(np.zeros((100, 100, 1)), x=0, y=0, c=0, z=0, z_value=1, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 1)), x=0, y=0, c=1, z=0, z_value=1, c_value='CD4')
    metadata = ts.getMetadata()
    assert metadata.get('frames') is not None
    assert len(metadata.get('frames')) == 2

    # case 3
    ts = large_image.new()
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=0, z_value=1, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=1, z_value=3.2, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=2, z_value=6.3, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=1, z=2, z_value=6.4, c_value='CD4')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=1, z=1, z_value=3.1, c_value='CD4')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=1, z_value=1.1)

    # case 4
    ts = large_image.new()
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=0, z_value=1, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=1, z_value=3.2, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=2, z_value=6.3, c_value='DAPI')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=1, z=2, z_value=6.4, c_value='CD4')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=1, z=1, z_value=3.1, c_value='CD4')
    ts.addTile(np.zeros((100, 100, 3)), x=0, y=0, c=0, z=1, z_value=1.1)
    frame_metadata = ts.metadata.get('frames', [])
    assert len(frame_metadata) == 6

    for frame in frame_metadata:
        for value in frame.values():
            # ensure that values are cast to native python types
            assert not isinstance(value, np.generic)


@pytest.mark.singular
def testSubprocess(tmp_path):
    sink = large_image_source_zarr.new()
    path = sink.largeImagePath
    subprocess.run([sys.executable, '-c', """import large_image_source_zarr
import numpy as np
sink = large_image_source_zarr.open('%s')
sink.addTile(np.ones((1, 1, 1)), x=2047, y=2047, t=5, z=2, t_value='thursday', z_value=0.2)
""" % path], capture_output=True, text=True, check=True)
    sink.addTile(np.ones((1, 1, 1)), x=5000, y=4095, t=0, z=4, t_value='sunday', z_value=0.4)

    metadata = sink.getMetadata()
    assert metadata['IndexRange']['IndexZ'] == 5
    assert sink.getRegion(
        region=dict(left=2047, top=2047, width=1, height=1),
        format='numpy',
        frame=17,
    )[0] == 1
    assert metadata['frames'][17]['ValueT'] == 'thursday'
    assert metadata['frames'][17]['ValueZ'] == 0.2
    assert sink.getRegion(
        region=dict(left=5000, top=4095, width=1, height=1),
        format='numpy',
        frame=24,
    )[0] == 1
    assert metadata['frames'][24]['ValueT'] == 'sunday'
    assert metadata['frames'][24]['ValueZ'] == 0.4
    assert sink.sizeX == 5001


@pytest.mark.singular
def testSubprocessFrameValues(tmp_path):
    # Each process has its own frame values; neither should replace the
    # other's
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((1, 1, 1)), x=0, y=0, t=0, t_value='sunday')
    subprocess.run([sys.executable, '-c', """import large_image_source_zarr
import numpy as np
sink = large_image_source_zarr.open('%s')
sink.addTile(np.ones((1, 1, 1)), x=0, y=0, t=1, t_value='monday')
""" % sink.largeImagePath], capture_output=True, text=True, check=True)
    sink.addTile(np.ones((1, 1, 1)), x=0, y=0, t=2, t_value='tuesday')

    metadata = sink.getMetadata()
    assert [frame['ValueT'] for frame in metadata['frames']] == ['sunday', 'monday', 'tuesday']


def _add_frame(sink, t):
    sink.addTile(np.full((10, 10, 1), t, dtype=np.uint8), x=0, y=0, t=t, t_value=f'time {t}')


@pytest.mark.singular
@pytest.mark.parametrize('pool_class', [
    Pool, ThreadPool, multiprocessing.get_context('forkserver').Pool,
], ids=['process', 'thread', 'forkserver'])
def testConcurrentFrameValues(tmp_path, pool_class):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    _add_frame(sink, 0)
    with pool_class(5) as pool:
        pool.starmap(_add_frame, [(sink, t) for t in range(1, 20)])
    sink.write(output_file, lossy=False)
    written = large_image_source_zarr.open(output_file)
    metadata = written.getMetadata()
    assert [frame['ValueT'] for frame in metadata['frames']] == [f'time {t}' for t in range(20)]
    for t in range(20):
        assert written.getRegion(format='numpy', frame=t)[0][0, 0, 0] == t


@pytest.mark.parametrize('suffix', ['.db', '.zip', '.zarr'])
def testWriteExcludesInternalFiles(tmp_path, suffix):
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 3), dtype=np.uint8), x=0, y=0)
    output_file = tmp_path / f'test{suffix}'
    sink.write(output_file, lossy=False)
    if suffix == '.db':
        keys = {row[0] for row in sqlite3.connect(output_file).execute('SELECT k FROM zarr')}
    elif suffix == '.zip':
        keys = set(zipfile.ZipFile(output_file).namelist())
    else:
        keys = set(os.listdir(output_file))
        output_file /= metadataFile(sink)
    assert metadataFile(sink) in keys
    assert not keys & {'.zarr_flock', '.zarr_stamp'}
    assert large_image_source_zarr.open(output_file).getRegion(format='numpy')[0].sum() == 300


@pytest.mark.parametrize('axes_order', ['tzd', 'tdz', 'dzt', 'dtz', 'ztd', 'zdt'])
def testAddAxes(tmp_path, axes_order):
    sink = large_image_source_zarr.new()
    kwarg_groups = [
        dict(t=0, t_value='sunday'),
        dict(
            t=5, t_value='friday',
            z=1, z_value=0.1,
            axes=axes_order.replace('d', '') + 'yxs',
        ),
        dict(
            t=6, t_value='saturday',
            z=2, z_value=0.2,
            d=1, d_value=100,
            axes=axes_order + 'yxs',
        ),
    ]
    for kwarg_group in kwarg_groups:
        sink.addTile(
            np.ones((4, 4, 4)),
            x=1020, y=1020,
            **kwarg_group,
        )

    metadata = sink.getMetadata()
    t_stride = metadata['IndexStride']['IndexT']
    z_stride = metadata['IndexStride']['IndexZ']
    expected_filled_frames = [
        # first and last frame are known, middle frame depends on axis ordering
        0, z_stride + t_stride * 5, 41,
    ]
    for frame in metadata.get('frames', []):
        frame_index = frame.get('Frame')
        sample = sink.getRegion(
            region=dict(left=1020, top=1020, width=1, height=1),
            format='numpy',
            frame=frame_index,
        )[0]
        frame_values = dict(
            t_value=frame.get('ValueT'),
            z_value=frame.get('ValueZ'),
            d_value=frame.get('ValueD'),
        )
        kwarg_group = {}
        if frame_index in expected_filled_frames:
            kwarg_group = kwarg_groups[expected_filled_frames.index(frame_index)]
            assert (sample == 1).all()
        else:
            assert (sample == 0).all()

        for k, v in frame_values.items():
            assert v == kwarg_group.get(k, 0)


def testMinWidthMinHeight(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((256, 256, 1), dtype=np.uint8), x=0, y=0)
    sink.minWidth = 1024
    sink.minHeight = 2048
    sink.addTile(np.zeros((256, 256, 1), dtype=np.uint8), x=256, y=0)
    sink.minWidth = 768
    sink.minHeight = 800
    sink.write(output_file)

    written = large_image_source_zarr.open(output_file)
    metadata = written.getMetadata()
    assert metadata.get('sizeX') == 768
    assert metadata.get('sizeY') == 800


def testNegativeMinWidth():
    sink = large_image_source_zarr.new()
    with pytest.raises(TileSourceError) as e:
        sink.minWidth = -10
    assert str(e.value) == 'minWidth must be positive or None'


def testNegativeMinHeight():
    sink = large_image_source_zarr.new()
    with pytest.raises(TileSourceError) as e:
        sink.minHeight = -10
    assert str(e.value) == 'minHeight must be positive or None'


def testDescriptionAndAdditionalMetadata(tmp_path):
    output_file = tmp_path / 'test.tiff'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((256, 256, 1), dtype=np.uint8), x=0, y=0)

    description = 'This is a test description.'
    additional_metadata = dict(
        name='Test',
        values=[1, 2, 3],
        nested=dict(hello='world'),
    )
    both = dict(
        description=description,
        additionalMetadata=additional_metadata,
    )

    sink.imageDescription = description
    assert sink._imageDescription == description
    sink.additionalMetadata = additional_metadata
    assert sink._imageDescription == both
    assert sink.imageDescription == description
    assert sink.additionalMetadata == additional_metadata

    # modify values and check again
    description = 'This is another test description'
    both['description'] = description
    additional_metadata['name'] = 'Test 2'
    both['additionalMetadata'] = additional_metadata
    sink.imageDescription = description
    sink.additionalMetadata = additional_metadata
    assert sink._imageDescription == both
    assert sink.imageDescription == description
    assert sink.additionalMetadata == additional_metadata

    sink.write(output_file)
    written = large_image.open(output_file)
    internal = written.getInternalMetadata()['xml']['internal']['zarr']['base']
    internal = internal.get('ome', internal)
    assert internal['multiscales'][0]['metadata']['description'] == both


def testRehydrateDescriptionAndAdditionalMetadata(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((256, 256, 1), dtype=np.uint8), x=0, y=0)

    description = 'This is a test description.'
    additional_metadata = dict(
        name='Test',
        values=[1, 2, 3],
        nested=dict(hello='world'),
    )
    sink.imageDescription = description
    sink.additionalMetadata = additional_metadata

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    assert written.imageDescription == description
    assert written.additionalMetadata == additional_metadata


def testNonserializableDescriptionAndAdditionalMetadata(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((256, 256, 1), dtype=np.uint8), x=0, y=0)

    created = datetime.now(tz=timezone.utc)
    with pytest.raises(TileSourceError):
        sink.imageDescription = created
    with pytest.raises(TileSourceError):
        sink.additionalMetadata = dict(created=created)
    sink.write(output_file)


def testNoneDescriptionAndAdditionalMetadata():
    sink = large_image_source_zarr.new()
    assert sink.imageDescription is None
    assert sink.additionalMetadata is None


def testSingleBand(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((1024, 1024, 1), dtype=np.uint8))
    sink.write(output_file)


def testSingleBandAndSingleX(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.zeros((1, 1024, 1), dtype=np.uint8))
    sink.write(output_file)


@pytest.mark.parametrize(('n_gcps', 't_gcps'), [(2, list), (2, str), (4, list), (4, str)])
def testGeoreferencing(tmp_path, n_gcps, t_gcps):
    output_file = tmp_path / 'test.tiff'
    sink = large_image_source_zarr.new()

    sink.addTile(np.random.random((256, 256, 3)) * 10, x=0, y=0)

    sink.projection = 4326
    bbox = [
        # covers lincoln memorial
        [-77.050923, 38.888728],
        [-77.049437, 38.889805],
    ]
    gcps = [
        (bbox[0][0], bbox[0][1], 0, 0),
        (bbox[0][0], bbox[1][1], 0, 256),
        (bbox[1][0], bbox[1][1], 256, 256),
        (bbox[1][0], bbox[0][1], 256, 0),
    ]
    if n_gcps == 2:
        gcps = [gcps[0], gcps[2]]
    if t_gcps is str:
        gcps = ' '.join(' '.join(str(v) for v in gcp) for gcp in gcps)
    sink.gcps = gcps
    sink.write(output_file)

    written = large_image.open(output_file)
    metadata = written.getMetadata()
    assert metadata['geospatial']
    sb = metadata['sourceBounds']
    assert sb['srs'] == '+proj=longlat +datum=WGS84 +no_defs'
    assert sb['xmin'] == bbox[0][0]
    assert sb['xmax'] == bbox[1][0]
    assert sb['ymin'] == bbox[0][1]
    assert sb['ymax'] == bbox[1][1]


def testGeoreferencingNoProjection(tmp_path):
    output_file = tmp_path / 'test.tiff'
    sink = large_image_source_zarr.new()

    sink.addTile(np.random.random((256, 256, 3)) * 10, x=0, y=0)

    bbox = [
        # covers lincoln memorial
        [-77.050923, 38.888728],
        [-77.049437, 38.889805],
    ]
    sink.gcps = [
        (bbox[0][0], bbox[0][1], 0, 0),
        (bbox[1][0], bbox[1][1], 256, 256),
    ]
    sink.write(output_file)
    written = large_image.open(output_file)
    metadata = written.getMetadata()
    assert metadata.get('geospatial') is None


def testGeoreferencingNoGCPs(tmp_path):
    output_file = tmp_path / 'test.tiff'
    sink = large_image_source_zarr.new()

    sink.addTile(np.random.random((256, 256, 3)) * 10, x=0, y=0)

    sink.projection = 4326
    with pytest.raises(TileSourceError):
        sink.write(output_file)
    written = large_image.open(output_file)
    metadata = written.getMetadata()
    assert metadata.get('geospatial') is None


@pytest.mark.parametrize('projection', ['', 'invalid', 'epsg:0', 0])
def testGeoreferencingInvalidProjection(tmp_path, projection):
    sink = large_image_source_zarr.new()

    with pytest.raises(TileSourceError):
        sink.projection = projection


@pytest.mark.parametrize('gcps', [
    '', 0, [], [()], [(), ()], ['50', '100'], [(-77, 38, 0, 0)], '-77 38 0 0',
])
def testGeoreferencingInvalidGCPs(tmp_path, gcps):
    sink = large_image_source_zarr.new()

    with pytest.raises(TileSourceError):
        sink.gcps = gcps


def testGeoreferencingDuplicateGCPs(tmp_path):
    sink = large_image_source_zarr.new()
    gcps = [
        (-77, -38, 0, 0),
        (-77, -38, 10, 10),
        (-76, -39, 0, 0),
        (-76, -39, 10, 10),
    ]
    with pytest.warns(Warning):
        sink.gcps = gcps
    assert sink.gcps == [(-77, -38, 0, 0), (-76, -39, 10, 10)]


def _zarr3():
    large_image_source_zarr._lazyImport()
    return large_image_source_zarr.zarr3


@pytest.mark.parametrize('zarr_format', [2, 3])
def testZarrFormatOption(tmp_path, zarr_format):
    if zarr_format == 3 and not _zarr3():
        with pytest.raises(TileSourceError):
            large_image_source_zarr.new(zarr_format=zarr_format)
        return
    sink = large_image_source_zarr.new(zarr_format=zarr_format)
    assert sink._zarrFormat == zarr_format
    sink.addTile(np.ones((10, 10, 3), dtype=np.uint8), x=0, y=0)
    output_file = tmp_path / 'test.zarr'
    sink.write(output_file, lossy=False)
    files = set(os.listdir(output_file))
    if zarr_format == 3:
        assert 'zarr.json' in files
        assert '.zattrs' not in files
    else:
        assert '.zattrs' in files
        assert 'zarr.json' not in files
    written = large_image_source_zarr.open(output_file / metadataFile(sink))
    assert written._is_ome
    assert written.getRegion(format='numpy')[0].sum() == 300
    ome = omeMetadata(written)
    if zarr_format == 3:
        assert ome['version'] == '0.5'
        assert 'version' not in ome['multiscales'][0]
        assert 'version' not in ome['omero']
    else:
        assert 'version' not in ome
        assert ome['multiscales'][0]['version'] == '0.4'
        assert ome['omero']['version'] == '0.4'
    assert 'bioformats2raw.layout' not in ome
    assert 'bioformats2raw.layout' not in written.getInternalMetadata()['zarr']['base']


@pytest.mark.singular
def testSubprocessUsesSameFormat(tmp_path):
    # A process that reopens a new image uses the format it was created with
    # rather than the default.
    sink = large_image_source_zarr.new(zarr_format=2)
    sink.addTile(np.ones((1, 1, 1)), x=0, y=0)
    result = subprocess.run([sys.executable, '-c', """import large_image_source_zarr
import numpy as np
sink = large_image_source_zarr.open('%s')
sink.addTile(np.ones((1, 1, 1)), x=10, y=0)
print(sink._zarrFormat)
""" % sink.largeImagePath], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == '2'
    # Adding another tile syncs what the other process wrote
    sink.addTile(np.ones((1, 1, 1)), x=0, y=0)
    assert sink.getMetadata()['sizeX'] == 11
    assert not (sink._tempdir / 'zarr.json').exists()


def testReadOmeZarr06(tmp_path):
    # OME-Zarr 0.6 moves the axes into coordinate systems and can wrap the
    # scale in a sequence transformation.
    if not _zarr3():
        pytest.skip('Requires zarr 3')
    import zarr

    path = tmp_path / 'test.zarr'
    group = zarr.open_group(path, mode='w', zarr_format=3)
    data = np.zeros((2, 3, 64, 128), dtype=np.uint8)
    for c in range(3):
        data[:, c] = c + 1
    group.create_array('s0', shape=data.shape, chunks=(1, 1, 32, 32), dtype=data.dtype,
                       dimension_names=['t', 'c', 'y', 'x'])[:] = data
    group.create_array('s1', shape=(2, 3, 32, 64), chunks=(1, 1, 32, 32), dtype=data.dtype,
                       dimension_names=['t', 'c', 'y', 'x'])[:] = data[:, :, ::2, ::2]
    group.update_attributes({'ome': {
        'version': '0.6',
        'multiscales': [{
            'name': 'example',
            'coordinateSystems': [{
                'name': 'intrinsic',
                'axes': [
                    {'name': 't', 'type': 'time', 'unit': 'second'},
                    {'name': 'c', 'type': 'channel'},
                    {'name': 'y', 'type': 'space', 'unit': 'micrometer'},
                    {'name': 'x', 'type': 'space', 'unit': 'micrometer'},
                ],
            }],
            'datasets': [{
                'path': 's0',
                'coordinateTransformations': [{
                    'type': 'scale', 'scale': [1.0, 1.0, 0.5, 0.25],
                    'input': {'path': 's0'}, 'output': {'name': 'intrinsic'},
                }],
            }, {
                'path': 's1',
                'coordinateTransformations': [{
                    'type': 'sequence',
                    'input': {'path': 's1'}, 'output': {'name': 'intrinsic'},
                    'transformations': [
                        {'type': 'scale', 'scale': [1.0, 1.0, 1.0, 0.5]},
                        {'type': 'translation', 'translation': [0, 0, 0.25, 0.125]},
                    ],
                }],
            }],
        }],
        'omero': {
            'channels': [
                {'label': name, 'color': 'FFFFFF',
                 'window': {'min': 0, 'max': 255, 'start': 0, 'end': 255}}
                for name in ['DAPI', 'GFP', 'RFP']
            ],
        },
    }})
    for source in [large_image_source_zarr.open(path / 'zarr.json'),
                   large_image.open(path / 'zarr.json')]:
        assert source._is_ome
        metadata = source.getMetadata()
        assert metadata['sizeX'] == 128
        assert metadata['sizeY'] == 64
        assert metadata['mm_x'] == 0.25e-3
        assert metadata['mm_y'] == 0.5e-3
        assert len(metadata['frames']) == 6
        assert metadata['channels'] == ['DAPI', 'GFP', 'RFP']
        assert source.getRegion(format='numpy', frame=1)[0][0, 0, 0] == 2
        assert source.getRegion(format='numpy', frame=1, output=dict(maxWidth=64))[0].shape == (
            32, 64, 1)


def _writeZarr(path, arrays, attrs=None):
    """
    Write a zarr hierarchy directly with the zarr library.

    :param path: the directory to write.
    :param arrays: a dictionary of array paths and numpy arrays.
    :param attrs: a dictionary of group paths ('' for the root) and the
        attributes to set on them.
    :returns: the path of the root metadata file to open.
    """
    large_image_source_zarr._lazyImport()
    zarr = large_image_source_zarr.zarr
    root = zarr.open_group(str(path), mode='w')
    for name, data in arrays.items():
        arr = zarr.zeros(data.shape, dtype=data.dtype, store=root.store, path=name)
        arr[...] = data
    for name, value in (attrs or {}).items():
        node = root if name == '' else root[name]
        node.attrs.update(value)
    return _zarrMetadataPath(path)


def _zarrMetadataPath(path):
    for fname in ('zarr.json', '.zattrs', '.zgroup', '.zarray'):
        if (path / fname).exists():
            return path / fname
    msg = 'No zarr metadata file written'
    raise AssertionError(msg)


def _omeAttrs(axes, shape, levels=('0',), omero=None):
    """
    Make OME-Zarr 0.4 style attributes for a multiscale image.

    :param axes: a list of axis names.
    :param shape: the shape of the base array.
    :param levels: the paths of the level arrays.
    :param omero: an optional omero dictionary.
    """
    attrs = {'multiscales': [{
        'version': '0.4',
        'axes': [
            {'name': a, 'type': 'space', 'unit': 'millimeter'} if a in 'xy' else
            {'name': a, 'type': 'channel'} if a == 'c' else
            {'name': a}
            for a in axes
        ],
        'datasets': [{
            'path': level,
            'coordinateTransformations': [{
                'type': 'scale',
                'scale': [2.0 ** idx if a in 'xy' else 1.0 for a in axes],
            }],
        } for idx, level in enumerate(levels)],
    }]}
    if omero is not None:
        attrs['omero'] = omero
    return attrs


def _rampData(shape, dtype=np.uint8):
    """
    Make an array where each index along the first axis has a distinct value.
    """
    data = np.zeros(shape, dtype=dtype)
    for i in range(shape[0]):
        data[i] = i + 1
    return data


def testAssociatedImageSingleBand(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((300, 400, 3)), 0, 0)
    sink.addAssociatedImage(np.full((100, 150), 7, dtype=np.uint8), imageKey='gray')
    sink.addAssociatedImage(np.full((100, 150, 1), 9, dtype=np.uint8), imageKey='gray1')
    sink.addAssociatedImage(np.full((100, 150, 3), 11, dtype=np.uint8))
    assert sink.getAssociatedImagesList() == ['gray', 'gray1', 'image_3']

    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    assert sorted(written.getAssociatedImagesList()) == ['gray', 'gray1', 'image_3']
    for source in (sink, written):
        for key, value in (('gray', 7), ('gray1', 9), ('image_3', 11)):
            pil = source._getAssociatedImage(key)
            assert pil.size == (150, 100)
            assert np.asarray(pil).reshape(100, 150, -1)[0, 0, 0] == value
            image, mime = source.getAssociatedImage(key, format='numpy')
            assert image.shape[:2] == (100, 150)
        assert source.getAssociatedImage('missing') is None


@pytest.mark.parametrize(('shape', 'bands', 'frames'), [
    ((64, 128, 3), 3, 1),
    ((4, 64, 128), 4, 1),
    ((5, 64, 128), 1, 5),
    ((5, 64, 128, 3), 3, 5),
])
def testReadNonOmeArray(tmp_path, shape, bands, frames):
    path = _writeZarr(tmp_path / 'test.zarr', {'0': _rampData(shape)})
    source = large_image_source_zarr.open(path)
    assert not source._is_ome
    metadata = source.getMetadata()
    assert metadata['sizeX'] == 128
    assert metadata['sizeY'] == 64
    assert metadata['bandCount'] == bands
    assert len(metadata.get('frames', [])) == (frames if frames > 1 else 0)
    region, _ = source.getRegion(format='numpy')
    assert region.shape == (64, 128, bands)
    if frames > 1:
        assert source.getRegion(format='numpy', frame=frames - 1)[0][0, 0, 0] == frames


def testReadNonOmeTooManyAxes(tmp_path):
    path = _writeZarr(tmp_path / 'test.zarr', {'0': np.zeros((5, 6, 64, 128), dtype=np.uint8)})
    with pytest.raises(TileSourceError):
        large_image_source_zarr.open(path)


def testReadBareArray(tmp_path):
    large_image_source_zarr._lazyImport()
    zarr = large_image_source_zarr.zarr
    data = np.full((64, 128, 3), 5, dtype=np.uint8)
    arr = zarr.zeros(data.shape, dtype=data.dtype, store=str(tmp_path / 'test.zarr'))
    arr[...] = data
    source = large_image_source_zarr.open(_zarrMetadataPath(tmp_path / 'test.zarr'))
    metadata = source.getMetadata()
    assert metadata['sizeX'] == 128
    assert metadata['sizeY'] == 64
    assert metadata['bandCount'] == 3
    assert source.getRegion(format='numpy')[0][0, 0, 0] == 5
    assert source.getAssociatedImagesList() == []


@pytest.mark.parametrize('omero', ['none', 'generic', 'named'])
def testReadOmeChannels(tmp_path, omero):
    labels = {
        'none': None,
        'generic': ['Channel 0', 'Channel 1', 'Channel 2'],
        'named': ['DAPI', 'GFP', 'RFP'],
    }[omero]
    attrs = _omeAttrs('cyx', (3, 64, 128), omero=None if labels is None else {
        'channels': [{'label': label, 'color': 'FFFFFF'} for label in labels]})
    path = _writeZarr(tmp_path / 'test.zarr', {'0': _rampData((3, 64, 128))}, {'': attrs})
    source = large_image_source_zarr.open(path)
    assert source._is_ome
    metadata = source.getMetadata()
    assert metadata['sizeX'] == 128
    if omero == 'named':
        # Labelled channels are frames
        assert metadata['bandCount'] == 1
        assert metadata['channels'] == labels
        assert len(metadata['frames']) == 3
        assert source.getRegion(format='numpy', frame=2)[0][0, 0, 0] == 3
    else:
        # Unlabelled channels are bands
        assert metadata['bandCount'] == 3
        assert 'frames' not in metadata
        assert source.getRegion(format='numpy')[0][0, 0, 2] == 3


@pytest.mark.parametrize('variant', ['no_xy_axes', 'bad_version', 'xy_conflict'])
def testReadOmeUnusable(tmp_path, variant):
    data = _rampData((2, 64, 128))
    if variant == 'no_xy_axes':
        arrays = {'0': data}
        attrs = {'': _omeAttrs('ijk', data.shape)}
    elif variant == 'bad_version':
        arrays = {'0': data}
        attrs = {'': _omeAttrs('zyx', data.shape)}
        attrs['']['multiscales'][0]['version'] = 'not a version'
    else:
        # Two identical series that also have an xy axis
        arrays = {'0/0': data, '1/0': data}
        attrs = {'0': _omeAttrs(['xy', 'y', 'x'], data.shape),
                 '1': _omeAttrs(['xy', 'y', 'x'], data.shape)}
    path = _writeZarr(tmp_path / 'test.zarr', arrays, attrs)
    with pytest.raises(TileSourceError):
        large_image_source_zarr.open(path)


def testReadOmeMultiscaleWithoutScale(tmp_path):
    data = _rampData((64, 128, 3))
    path = _writeZarr(tmp_path / 'test.zarr', {'0': data}, {'': {'ome': {
        'version': '0.5',
        'multiscales': [{
            'axes': [{'name': 'y', 'type': 'space', 'unit': 'millimeter'},
                     {'name': 'x', 'type': 'space', 'unit': 'millimeter'},
                     {'name': 'c', 'type': 'channel'}],
            'datasets': [{
                'path': '0',
                'coordinateTransformations': [
                    {'type': 'identity'},
                    {'type': 'sequence', 'transformations': [
                        {'type': 'translation', 'translation': [0, 0, 0]}]},
                ],
            }],
        }],
    }}})
    source = large_image_source_zarr.open(path)
    assert source._is_ome
    metadata = source.getMetadata()
    assert metadata['sizeX'] == 128
    assert metadata['mm_x'] is None
    assert metadata['mm_y'] is None


@pytest.mark.parametrize('variant', ['missing_level', 'mismatched_level'])
def testReadMultiSeriesLevels(tmp_path, variant):
    base = _rampData((2, 128, 256, 3))
    level1 = base[:, ::2, ::2]
    arrays = {'0/0': base, '0/1': level1, '1/0': base * 10}
    if variant == 'mismatched_level':
        arrays['1/1'] = level1[:, :-4, :-8] * 10
    attrs = {
        '0': _omeAttrs('zyxc', base.shape, levels=('0', '1')),
        '1': _omeAttrs('zyxc', base.shape, levels=('0', '1') if '1/1' in arrays else ('0',)),
    }
    path = _writeZarr(tmp_path / 'test.zarr', arrays, attrs)
    source = large_image_source_zarr.open(path)
    metadata = source.getMetadata()
    assert metadata['sizeX'] == 256
    assert metadata['sizeY'] == 128
    assert metadata['bandCount'] == 3
    # Two series times two z values
    assert len(metadata['frames']) == 4
    assert metadata['IndexRange'] == {'IndexZ': 2, 'IndexXY': 2}
    # The second level cannot be used since the series don't agree on it
    assert source._populatedLevels == 1
    for frame, value in ((0, 1), (1, 2), (2, 10), (3, 20)):
        assert source.getRegion(format='numpy', frame=frame)[0][0, 0, 0] == value
        half, _ = source.getRegion(format='numpy', frame=frame, output=dict(maxWidth=128))
        assert half.shape == (64, 128, 3)
        assert half[0, 0, 0] == value


def testAddTileInvalidAxes():
    sink = large_image_source_zarr.new()
    with pytest.raises(ValueError, match='Invalid type for axes'):
        sink.addTile(np.ones((10, 10, 1)), 0, 0, axes=123)
    with pytest.raises(ValueError, match='Must contain "y" and "x"'):
        sink.addTile(np.ones((10, 10, 1)), 0, 0, axes='abs')


def testAddTileMaskWithExtraAxes():
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1)), 0, 0, z=0)
    sink.addTile(np.ones((10, 10, 1)), 0, 0, z=1)
    mask = np.zeros((10, 10), dtype=bool)
    mask[:5] = True
    sink.addTile(np.full((10, 10, 1), 5), 0, 0, z=1, mask=mask)
    region, _ = sink.getRegion(format='numpy', frame=1)
    assert region[0, 0, 0] == 5
    assert region[9, 9, 0] == 1
    region, _ = sink.getRegion(format='numpy', frame=0)
    assert region[0, 0, 0] == 1


def testCropValidation():
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1)), 0, 0)
    sink.crop = (1, 2, 3, 4)
    assert sink.crop == (1, 2, 3, 4)
    sink.crop = None
    assert sink.crop is None
    for value in [(-1, 0, 5, 5), (0, -1, 5, 5), (0, 0, 0, 5), (0, 0, 5, 0)]:
        with pytest.raises(TileSourceError):
            sink.crop = value


def testScaleValidation():
    sink = large_image_source_zarr.new()
    sink.mm_x = 0.5
    sink.mm_y = '0.25'
    assert sink.mm_x == 0.5
    assert sink.mm_y == 0.25
    for value in [0, -1]:
        with pytest.raises(TileSourceError):
            sink.mm_x = value
        with pytest.raises(TileSourceError):
            sink.mm_y = value
    sink.mm_x = None
    sink.mm_y = None
    assert sink.mm_x is None
    assert sink.mm_y is None


def testFrameValuesValidation():
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1)), 0, 0, z=0)
    sink.addTile(np.ones((10, 10, 1)), 0, 0, z=1)
    assert sink.frameAxes is None
    with pytest.raises(ValueError, match='frameAxes must be set first'):
        sink.frameUnits = {'z': 'mm'}
    with pytest.raises(ValueError, match='frameAxes must be set first'):
        sink.frameValues = np.zeros((1, 1))
    sink.frameAxes = ['z']
    with pytest.raises(ValueError, match='frameUnits must be a dictionary'):
        sink.frameUnits = ['mm']
    with pytest.raises(ValueError, match='frameUnits must be a dictionary'):
        sink.frameUnits = {'t': 'seconds'}
    with pytest.raises(ValueError, match='must have 2 dimensions'):
        sink.frameValues = np.zeros((1,))
    sink.frameUnits = {'z': 'mm'}
    sink.frameValues = np.array([[1.5], [2.5]], dtype=object)
    assert [f['ValueZ'] for f in sink.getMetadata()['frames']] == [1.5, 2.5]


def testNotEditable(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1)), 0, 0)
    sink.write(output_file)
    written = large_image_source_zarr.open(output_file)
    with pytest.raises(TileSourceError, match='Not an editable image'):
        written.addTile(np.ones((10, 10, 1)), 0, 0)
    with pytest.raises(TileSourceError, match='Not an editable image'):
        written.crop = (0, 0, 5, 5)
    with pytest.raises(TileSourceError, match='Not an editable image'):
        written.mm_x = 1


def testGcpsInvalidElements():
    sink = large_image_source_zarr.new()
    with pytest.raises(TileSourceError, match='Each GCP must be specified'):
        sink.gcps = [5, 6]


def testGenerateLevelsWithoutData():
    sink = large_image_source_zarr.new()
    with pytest.raises(TileSourceError, match='No root data'):
        sink._generateDownsampledLevels(ResampleMethod.NP_NEAREST)


@pytest.mark.parametrize('suffix', ['.zarr', '.db'])
def testWriteOverwrite(tmp_path, suffix):
    output_file = tmp_path / f'test{suffix}'
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1), dtype=np.uint8), 0, 0)
    sink.write(output_file)
    with pytest.raises(TileSourceError, match='Output path exists'):
        sink.write(output_file, overwriteAllowed=False)
    sink.addTile(np.full((10, 10, 1), 3, dtype=np.uint8), 0, 0)
    sink.write(output_file)
    written = large_image_source_zarr.open(
        output_file / metadataFile(sink) if suffix == '.zarr' else output_file)
    assert written.getRegion(format='numpy')[0][0, 0, 0] == 3


def testEditableTileAndInternalMetadata():
    sink = large_image_source_zarr.new()
    assert sink.imageDescription is None
    assert sink.additionalMetadata is None
    sink.addTile(np.full((10, 10, 1), 3, dtype=np.uint8), 0, 0)
    # getTile validates the image when levels are unknown
    tile = sink.getTile(0, 0, 0, numpyAllowed=True)
    assert tile[0, 0, 0] == 3
    assert 'multiscales' in omeMetadata(sink)
    assert sink.channelNames is None
    assert sink.channelColors == []


def testNumpyFrameValuesAreJsonSafe(tmp_path):
    output_file = tmp_path / 'test.db'
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1), dtype=bool), 0, 0,
                 z=0, z_value=np.float32(1.5), t=0, t_value=np.bool_(True))
    sink.addTile(np.ones((10, 10, 1), dtype=bool), 0, 0,
                 z=1, z_value=np.float32(2.5), t=0, t_value=np.bool_(True))
    channel = omeMetadata(sink)['omero']['channels'][0]
    assert channel['window'] == {'min': 0, 'max': 1, 'start': 0, 'end': 1}
    sink.write(output_file, lossy=False)
    written = large_image_source_zarr.open(output_file)
    frames = written.getMetadata()['frames']
    assert [frame['ValueZ'] for frame in frames] == [1.5, 2.5]
    assert all(frame['ValueT'] is True for frame in frames)
    with pytest.raises(TypeError):
        large_image_source_zarr._jsonSafe({'x': object()})


def testReopenNewImageInProcess():
    sink = large_image_source_zarr.new()
    sink.addTile(np.ones((10, 10, 1)), 0, 0)
    other = large_image_source_zarr.open(sink.largeImagePath, noCache=True)
    assert other is not sink
    assert other._zarrFormat == sink._zarrFormat
    assert other.getMetadata()['sizeX'] == 10
    with pytest.raises(TileSourceError):
        large_image_source_zarr.new(zarr_format=4)
