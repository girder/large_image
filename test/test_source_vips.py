import os
import shutil
import tempfile

import large_image_source_vips
import numpy as np
import pytest
import pyvips

import large_image
from large_image.exceptions import TileSourceError

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
    assert source.bandFormat == pyvips.enums.BandFormat.FLOAT
    assert source.mm_x == pytest.approx(0.08467, 4)
    assert source.mm_y == pytest.approx(0.08467, 4)
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

    assert out.bandFormat == pyvips.enums.BandFormat.UCHAR
    assert out.bandRanges['min'][0] > 10
    assert out.mm_x is None
    assert out.mm_y is None
    out.mm_x = source.getNativeMagnification()['mm_x']
    out.mm_y = source.getNativeMagnification()['mm_y']
    assert out.mm_x == 0.00025
    assert out.mm_y == 0.00025
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


def testNewAndWriteCrop():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    out = large_image_source_vips.new()
    assert out.crop is None
    out.crop = 10, 10, 2000, 2000
    assert out.crop is not None
    out.crop = None
    assert out.crop is None
    with pytest.raises(TileSourceError):
        out.crop = -1, -1, -1, -1
    out.crop = 10, 10, 2000, 2000
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])

    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.tiff')
    try:
        out.write(outputPath)
        result = large_image.open(outputPath)
        resultMetadata = result.getMetadata()
        assert resultMetadata['sizeX'] == 2000
        assert resultMetadata['sizeY'] == 1990
    finally:
        shutil.rmtree(tmpdir)


def testNewAndWriteMinSize():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    out = large_image_source_vips.new()
    assert out.minWidth is None
    assert out.minHeight is None
    out.minWidth = 4030
    out.minHeight = 2030
    assert out.minWidth is not None
    assert out.minHeight is not None
    out.minWidth = None
    out.minHeight = None
    assert out.minWidth is None
    assert out.minHeight is None
    with pytest.raises(TileSourceError):
        out.minWidth = -1
    with pytest.raises(TileSourceError):
        out.minHeight = -1
    out.minWidth = 4030
    out.minHeight = 2030
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])

    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.tiff')
    try:
        out.write(outputPath)
        result = large_image.open(outputPath)
        resultMetadata = result.getMetadata()
        assert resultMetadata['sizeX'] == 4030
        assert resultMetadata['sizeY'] == 2030

        outputPath2 = os.path.join(tmpdir, 'temp2.tiff')
        out.minWidth = 2000
        out.minHeight = 1000
        out.write(outputPath2)
        result = large_image.open(outputPath2)
        resultMetadata = result.getMetadata()
        assert resultMetadata['sizeX'] == 4000
        assert resultMetadata['sizeY'] == 2000
    finally:
        shutil.rmtree(tmpdir)


def testNewAndWriteJPEG():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    # Update this if it doesn't direct to vips source
    out = large_image.new()
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'])
    tmpdir = tempfile.mkdtemp()
    outputPath = os.path.join(tmpdir, 'temp.jpeg')
    try:
        out.write(outputPath, vips_kwargs=dict(Q=80))
        assert os.path.getsize(outputPath) > 50000
        image = open(outputPath, 'rb').read()
        assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    finally:
        shutil.rmtree(tmpdir)


def testNewAndWriteWithMask():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image.open(imagePath)
    out = large_image_source_vips.new()
    for tile in source.tileIterator(
        format=large_image.constants.TILE_FORMAT_NUMPY,
        region=dict(right=4000, bottom=2000),
    ):
        if tile['tile_position']['position']:
            mask = tile['tile'] > 128
        else:
            mask = None
        out.addTile(tile['tile'], x=tile['x'], y=tile['y'], mask=mask)

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


def testNewAndWriteNegative():
    out = large_image_source_vips.new()
    out.addTile(np.full((4, 4, 3), 1, dtype=np.uint8), x=0, y=0)
    out.addTile(np.full((5, 4, 3), 2, dtype=np.uint8), x=-2, y=1)
    with tempfile.TemporaryDirectory() as tmpdir:
        outputPath = os.path.join(tmpdir, 'temp.tiff')
        out.write(outputPath, lossy=False)
        region = out.getRegion(format=large_image.constants.TILE_FORMAT_NUMPY)[0]
        assert (region[:, :, 0] == np.array([
            [0, 0, 1, 1, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 0, 0],
            [2, 2, 2, 2, 0, 0]])).all()

        ts = large_image.open(outputPath)
        region = ts.getRegion(format=large_image.constants.TILE_FORMAT_NUMPY)[0]
        assert (region[:, :, 0] == np.array([
            [0, 0, 1, 1, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 1, 1],
            [2, 2, 2, 2, 0, 0],
            [2, 2, 2, 2, 0, 0]])).all()
