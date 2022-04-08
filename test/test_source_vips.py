import os
import shutil
import tempfile

import large_image_source_vips

import large_image

from . import utilities
from .datastore import datastore


def testTilesFromVips():
    imagePath = datastore.fetch('d042-353.crop.small.float32.tif')
    source = large_image_source_vips.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 480
    assert tileMetadata['sizeY'] == 320
    assert tileMetadata['levels'] == 2
    utilities.checkTilesZXY(source, tileMetadata)


def testInternalMetadata():
    imagePath = datastore.fetch('d042-353.crop.small.float32.tif')
    source = large_image_source_vips.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'vips-loader' in metadata


def testNewAndWrite():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    out = large_image_source_vips.new()
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])

    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.tiff')
    try:
        out.write(outputPath)
        assert os.path.getsize(outputPath) > 50000
        result = large_image.open(outputPath)
        resultMetadata = result.getMetadata()
        assert resultMetadata['sizeX'] == 4000
    finally:
        shutil.rmtree(tmpdir)


def testNewAndWriteLossless():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    out = large_image_source_vips.new()
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])

    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.tiff')
    try:
        out.write(outputPath, lossy=False)
        assert os.path.getsize(outputPath) > 50000
        result = large_image.open(outputPath)
        resultMetadata = result.getMetadata()
        assert resultMetadata['sizeX'] == 4000
    finally:
        shutil.rmtree(tmpdir)
