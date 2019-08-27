# -*- coding: utf-8 -*-

import os
import re

from large_image import config
import large_image_source_pil

from . import utilities


def testTilesFromPIL():
    imagePath = utilities.externaldata('data/sample_Easy1.png.sha512')
    # Test with different max size options.
    config.setConfig('max_small_image_size', 100)
    assert large_image_source_pil.PILFileTileSource.canRead(imagePath) is False

    # Allow images bigger than our test
    config.setConfig('max_small_image_size', 2048)
    assert large_image_source_pil.PILFileTileSource.canRead(imagePath) is True
    source = large_image_source_pil.PILFileTileSource(imagePath)
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


def testTileRedirects():
    # Test redirects, use a JPEG
    imagePath = utilities.externaldata('data/sample_Easy1.jpeg.sha512')
    rawimage = open(imagePath, 'rb').read()
    source = large_image_source_pil.PILFileTileSource(imagePath)
    # No encoding or redirect should just get a JPEG
    image = source.getTile(0, 0, 0)
    assert image == rawimage
    # quality 75 should work
    source = large_image_source_pil.PILFileTileSource(imagePath, jpegQuality=95)
    image = source.getTile(0, 0, 0)
    assert image == rawimage
    # redirect with a different quality shouldn't
    source = large_image_source_pil.PILFileTileSource(imagePath, jpegQuality=75)
    image = source.getTile(0, 0, 0)
    assert image != rawimage
    # redirect with a different encoding shouldn't
    source = large_image_source_pil.PILFileTileSource(imagePath, encoding='PNG')
    image = source.getTile(0, 0, 0)
    assert image != rawimage


def testReadingVariousColorFormats():
    testDir = os.path.dirname(os.path.realpath(__file__))
    files = [name for name in os.listdir(os.path.join(testDir, 'test_files'))
             if re.match(r'&test_.*\.png$', name)]
    for name in files:
        imagePath = os.path.join(testDir, 'test_files', name)
        assert large_image_source_pil.PILFileTileSource.canRead(imagePath) is True
