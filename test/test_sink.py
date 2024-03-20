
import large_image_source_test
import large_image_source_zarr
import numpy as np
import pytest

import large_image

TMP_DIR = 'tmp/zarr_sink'
FILE_TYPES = [
    'tiff',
    'sqlite',
    'db',
    'zip',
    'zarr',
    # "dz",
    # 'svi',
    # 'svs',
]


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


def testExtraAxis():
    sink = large_image_source_zarr.new()
    sink.addTile(np.random.random((256, 256)), 0, 0, z=1)
    metadata = sink.getMetadata()
    assert metadata.get('bandCount') == 1
    assert len(metadata.get('frames')) == 2


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
        output_file /= '.zattrs'
    written = large_image.open(output_file)
    region, _ = written.getRegion(format='numpy')
    shape = region.shape
    assert shape == (10, 10, 1)


@pytest.mark.parametrize('file_type', FILE_TYPES)
def testImageCopySmall(file_type, tmp_path):
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

    # TODO: fix these failures; unexpected metadata when reading it back
    sink.write(output_file)
    if file_type == 'zarr':
        output_file /= '.zattrs'
    written = large_image.open(output_file)
    new_metadata = written.metadata

    assert new_metadata.get('sizeX') == 512
    assert new_metadata.get('sizeY') == 1024
    assert new_metadata.get('dtype') == 'uint8'
    assert new_metadata.get('levels') == 2 or new_metadata.get('levels') == 3
    assert new_metadata.get('bandCount') == 3
    assert len(new_metadata.get('frames')) == 6


@pytest.mark.parametrize('file_type', FILE_TYPES)
def testImageCopySmallMultiband(file_type, tmp_path):
    output_file = tmp_path / f'test.{file_type}'
    sink = large_image_source_zarr.new()
    bands = (
        'red=400-12000,green=0-65535,blue=800-4000,'
        'ir1=200-24000,ir2=200-22000,gray=100-10000,other=0-65535'
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
    assert metadata.get('dtype') == 'uint16'
    assert metadata.get('levels') == 2
    assert metadata.get('bandCount') == 7
    assert len(metadata.get('frames')) == 6

    # TODO: fix these failures; unexpected metadata when reading it back
    sink.write(output_file)
    if file_type == 'zarr':
        output_file /= '.zattrs'
    written = large_image.open(output_file)
    new_metadata = written.getMetadata()

    assert new_metadata.get('sizeX') == 512
    assert new_metadata.get('sizeY') == 1024
    assert new_metadata.get('dtype') == 'uint16'
    assert new_metadata.get('levels') == 2 or new_metadata.get('levels') == 3
    assert new_metadata.get('bandCount') == 7
    assert len(new_metadata.get('frames')) == 6
