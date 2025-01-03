import os
import re

import large_image_source_pil
import pytest

from large_image import config
from large_image.cache_util import cachesClear

from . import utilities
from .datastore import datastore


# Singular because we adjust config
@pytest.mark.singular
def testTilesFromPIL():
    # Ensure this test can run in any order
    cachesClear()

    imagePath = datastore.fetch('sample_Easy1.png')
    # Test with different max size options.
    config.setConfig('max_small_image_size', 100)
    assert large_image_source_pil.canRead(imagePath) is False

    # Allow images bigger than our test
    config.setConfig('max_small_image_size', 2048)
    assert large_image_source_pil.canRead(imagePath) is True
    source = large_image_source_pil.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 1790
    assert tileMetadata['tileHeight'] == 1046
    assert tileMetadata['sizeX'] == 1790
    assert tileMetadata['sizeY'] == 1046
    assert tileMetadata['levels'] == 1
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    utilities.checkTilesZXY(source, tileMetadata)


# Singular because if we read the file in a styled manner, such as in the
# general read tests, it gets caches and therefore will be more efficiently
# read from memory than from the file for the redirect
@pytest.mark.singular
def testTileRedirects():
    # Test redirects, use a JPEG
    imagePath = datastore.fetch('sample_Easy1.jpeg')
    rawimage = open(imagePath, 'rb').read()
    source = large_image_source_pil.open(imagePath, style={'icc': False})
    # No encoding or redirect should just get a JPEG
    image = source.getTile(0, 0, 0)
    assert image == rawimage
    # quality 75 should work
    source = large_image_source_pil.open(imagePath, style={'icc': False}, jpegQuality=95)
    image = source.getTile(0, 0, 0)
    assert image == rawimage
    # redirect with a different quality shouldn't
    source = large_image_source_pil.open(imagePath, style={'icc': False}, jpegQuality=75)
    image = source.getTile(0, 0, 0)
    assert image != rawimage
    # redirect with a different encoding shouldn't
    source = large_image_source_pil.open(imagePath, style={'icc': False}, encoding='PNG')
    image = source.getTile(0, 0, 0)
    assert image != rawimage


def testReadingVariousColorFormats():
    testDir = os.path.dirname(os.path.realpath(__file__))
    files = [name for name in os.listdir(os.path.join(testDir, 'test_files'))
             if re.match(r'&test_.*\.png$', name)]
    for name in files:
        imagePath = os.path.join(testDir, 'test_files', name)
        assert large_image_source_pil.canRead(imagePath) is True


def testInternalMetadata():
    imagePath = datastore.fetch('sample_Easy1.png')
    source = large_image_source_pil.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'pil' in metadata


def testGetBandInformation():
    imagePath = datastore.fetch('sample_Easy1.png')
    source = large_image_source_pil.open(imagePath)
    bandInfo = source.getBandInformation(False)
    assert len(bandInfo) == 4
    assert bandInfo[1] == {'interpretation': 'red'}

    bandInfo = source.getBandInformation(True)
    assert len(bandInfo) == 4
    assert 'mean' in bandInfo[1]
