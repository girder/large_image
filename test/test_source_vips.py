import os
import shutil
import tempfile

import large_image_source_vips
import pytest

import large_image

from . import utilities
from .datastore import datastore


def testTilesFromVips():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_vips.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 58368
    assert tileMetadata['sizeY'] == 12288
    assert tileMetadata['levels'] == 9
    assert tileMetadata['magnification'] == pytest.approx(40, 1)
    utilities.checkTilesZXY(source, tileMetadata)


def testInternalMetadata():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_vips.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'vips-loader' in metadata


def testNewAndWrite():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    sourceMetadata = source.getMetadata()
    out = large_image_source_vips.new()
    for tile in source.tileIterator(format=large_image.constants.TILE_FORMAT_NUMPY):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])

    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.tiff')
    try:
        out.write(outputPath)
        assert os.path.getsize(outputPath) > 500000
        result = large_image.open(outputPath)
        resultMetadata = result.getMetadata()
        assert sourceMetadata['sizeX'] == resultMetadata['sizeX']
    finally:
        shutil.rmtree(tmpdir)
