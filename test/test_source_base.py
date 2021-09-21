import os

import pytest

import large_image
from large_image.tilesource import nearPowerOfTwo

from .datastore import datastore


def testNearPowerOfTwo():
    assert nearPowerOfTwo(45808, 11456)
    assert nearPowerOfTwo(45808, 11450)
    assert not nearPowerOfTwo(45808, 11200)
    assert nearPowerOfTwo(45808, 11400)
    assert not nearPowerOfTwo(45808, 11400, 0.005)
    assert nearPowerOfTwo(45808, 11500)
    assert not nearPowerOfTwo(45808, 11500, 0.005)


def testCanRead():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    assert large_image.canRead(imagePath) is False

    imagePath = datastore.fetch('sample_image.ptif')
    assert large_image.canRead(imagePath) is True


@pytest.mark.parametrize('source', [
    'bioformats',
    'deepzoom',
    # 'dummy', # exclude - no files
    'gdal',
    'mapnik',
    'nd2',
    'ometiff',
    'openjpeg',
    'openslide',
    'pil',
    # 'test', # exclude - no files
    'tiff',
])
def testSourcesFileNotFound(source):
    large_image.tilesource.loadTileSources()
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile')
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile.ext')
