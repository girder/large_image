import io
import json
import os
import struct
import tempfile

import large_image_source_tiff
import numpy as np
import pytest
import tifftools

from large_image import constants
from large_image.tilesource.utilities import ImageBytes

from . import utilities
from .datastore import datastore


def nestedUpdate(value, nvalue):
    if not isinstance(value, dict) or not isinstance(nvalue, dict):
        return nvalue
    for k, v in nvalue.items():
        value.setdefault(k, dict())
        if isinstance(v, dict):
            v = nestedUpdate(value[k], v)
        value[k] = v
    return value


def testTilesFromPTIF():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    assert large_image_source_tiff.canRead(imagePath) is False

    imagePath = datastore.fetch('sample_image.ptif')
    assert large_image_source_tiff.canRead(imagePath) is True
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 58368
    assert tileMetadata['sizeY'] == 12288
    assert tileMetadata['levels'] == 9
    tileMetadata['sparse'] = 5
    utilities.checkTilesZXY(source, tileMetadata)


def testTileIterator():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    # Ask for JPEGS
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_IMAGE,
            encoding='JPEG'):
        tileCount += 1
        assert tile['tile'][:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert tileCount == 45
    # Ask for PNGs
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_IMAGE,
            encoding='PNG'):
        tileCount += 1
        assert tile['tile'][:len(utilities.PNGHeader)] == utilities.PNGHeader
    assert tileCount == 45
    # Ask for TIFFS
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_IMAGE,
            encoding='TIFF'):
        tileCount += 1
        assert tile['tile'][:len(utilities.TIFFHeader)] == utilities.TIFFHeader
    assert tileCount == 45
    # Ask for WEBPs
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_IMAGE,
            encoding='WEBP'):
        tileCount += 1
        assert tile['tile'][8:12] == b'WEBP'
    assert tileCount == 45


def testTileIteratorRetiling():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    # Test retiling to 500 x 400
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_PIL,
            tile_size={'width': 500, 'height': 400}):
        tileCount += 1
        assert tile['tile'].size == (tile['width'], tile['height'])
        assert tile['width'] == 500 if tile['level_x'] < 7 else 148
        assert tile['height'] == 400 if tile['level_y'] < 1 else 368
    assert tileCount == 16

    # Test retiling to 300 x 275 with 50 x 40 pixels overlap with trimmed edges
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_PIL,
            tile_size={'width': 300, 'height': 275},
            tile_overlap={'x': 50, 'y': 40, 'edges': True}):
        tileCount += 1
        assert tile['tile'].size == (tile['width'], tile['height'])
        assert tile['width'] == (
            275 if not tile['level_x'] else 300
            if tile['level_x'] < 14 else 173)
        assert tile['height'] == (
            255 if not tile['level_y'] else 275
            if tile['level_y'] < 3 else 83)
        assert tile['tile_overlap']['left'] == 0 if not tile['level_x'] else 25
        assert tile['tile_overlap']['right'] == (
            25 if tile['level_x'] < 14 else 0)
        assert tile['tile_overlap']['top'] == 0 if not tile['level_y'] else 20
        assert tile['tile_overlap']['bottom'] == (
            20 if tile['level_y'] < 3 else 0)
    assert tileCount == 60

    # Test retiling to 300 x 275 with 51 x 41 pixels overlap with trimmed edges
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_PIL,
            tile_size={'width': 300, 'height': 275},
            tile_overlap={'x': 51, 'y': 41, 'edges': True}):
        tileCount += 1
        assert tile['tile'].size == (tile['width'], tile['height'])
        assert tile['width'] == (
            275 if not tile['level_x'] else 300
            if tile['level_x'] < 14 else 187)
        assert tile['height'] == (
            255 if not tile['level_y'] else 275
            if tile['level_y'] < 3 else 86)
        assert tile['tile_overlap']['left'] == 0 if not tile['level_x'] else 25
        assert tile['tile_overlap']['right'] == (
            26 if tile['level_x'] < 14 else 0)
        assert tile['tile_overlap']['top'] == 0 if not tile['level_y'] else 20
        assert tile['tile_overlap']['bottom'] == (
            21 if tile['level_y'] < 3 else 0)
    assert tileCount == 60

    # Test retiling to 300 x 275 with 51 x 41 pixels overlap without trimmed
    # edges
    tileCount = 0
    for tile in source.tileIterator(
            scale={'magnification': 2.5},
            format=constants.TILE_FORMAT_PIL,
            tile_size={'width': 300, 'height': 275},
            tile_overlap={'x': 51, 'y': 41}):
        tileCount += 1
        assert tile['tile'].size == (tile['width'], tile['height'])
        assert tile['width'] == 300 if tile['level_x'] < 14 else 162
        assert tile['height'] == 275 if tile['level_y'] < 3 else 66
        assert tile['tile_overlap']['left'] == 0 if not tile['level_x'] else 25
        assert tile['tile_overlap']['right'] == (
            26 if tile['level_x'] < 14 else 0)
        assert tile['tile_overlap']['top'] == 0 if not tile['level_y'] else 20
        assert tile['tile_overlap']['bottom'] == (
            21 if tile['level_y'] < 3 else 0)
    assert tileCount == 60


def testTileIteratorSingleTile():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    # Test getting a single tile
    sourceRegion = {
        'width': 0.7, 'height': 0.6,
        'left': 0.15, 'top': 0.2,
        'units': 'fraction'}
    tileCount = 0
    for tile in source.tileIterator(
            region=sourceRegion,
            scale={'magnification': 5},
            tile_position=25):
        tileCount += 1
        assert tile['tile_position']['position'] == 25
        assert tile['tile_position']['level_x'] == 8
        assert tile['tile_position']['level_y'] == 2
        assert tile['tile_position']['region_x'] == 4
        assert tile['tile_position']['region_y'] == 1
        assert tile['iterator_range']['level_x_min'] == 4
        assert tile['iterator_range']['level_y_min'] == 1
        assert tile['iterator_range']['level_x_max'] == 25
        assert tile['iterator_range']['level_y_max'] == 5
        assert tile['iterator_range']['region_x_max'] == 21
        assert tile['iterator_range']['region_y_max'] == 4
        assert tile['iterator_range']['position'] == 84
    assert tileCount == 1
    tiles = list(source.tileIterator(
        region=sourceRegion, scale={'magnification': 5},
        tile_position={'position': 25}))
    assert len(tiles) == 1
    assert tiles[0]['tile_position']['position'] == 25
    tiles = list(source.tileIterator(
        region=sourceRegion, scale={'magnification': 5},
        tile_position={'level_x': 8, 'level_y': 2}))
    assert len(tiles) == 1
    assert tiles[0]['tile_position']['position'] == 25
    tiles = list(source.tileIterator(
        region=sourceRegion, scale={'magnification': 5},
        tile_position={'region_x': 4, 'region_y': 1}))
    assert len(tiles) == 1
    assert tiles[0]['tile_position']['position'] == 25
    tiles = list(source.tileIterator(
        region=sourceRegion, scale={'magnification': 5},
        tile_position={'position': 90}))
    assert len(tiles) == 0


def testGetSingleTile():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    sourceRegion = {
        'width': 0.7, 'height': 0.6,
        'left': 0.15, 'top': 0.2,
        'units': 'fraction'}
    sourceScale = {'magnification': 5}
    targetScale = {'magnification': 2.5}
    tile = source.getSingleTile(
        region=sourceRegion, scale=sourceScale, tile_position=25)
    assert tile['tile_position']['position'] == 25
    assert tile['tile_position']['level_x'] == 8
    assert tile['tile_position']['level_y'] == 2
    assert tile['tile_position']['region_x'] == 4
    assert tile['tile_position']['region_y'] == 1
    assert tile['iterator_range']['level_x_min'] == 4
    assert tile['iterator_range']['level_y_min'] == 1
    assert tile['iterator_range']['level_x_max'] == 25
    assert tile['iterator_range']['level_y_max'] == 5
    assert tile['iterator_range']['region_x_max'] == 21
    assert tile['iterator_range']['region_y_max'] == 4
    assert tile['iterator_range']['position'] == 84

    tile = source.getSingleTileAtAnotherScale(
        sourceRegion, sourceScale, targetScale, tile_position=25)
    assert tile['tile_position']['position'] == 25
    assert tile['tile_position']['level_x'] == 5
    assert tile['tile_position']['level_y'] == 2
    assert tile['tile_position']['region_x'] == 3
    assert tile['tile_position']['region_y'] == 2
    assert tile['iterator_range']['level_x_min'] == 2
    assert tile['iterator_range']['level_y_min'] == 0
    assert tile['iterator_range']['level_x_max'] == 13
    assert tile['iterator_range']['level_y_max'] == 3
    assert tile['iterator_range']['region_x_max'] == 11
    assert tile['iterator_range']['region_y_max'] == 3
    assert tile['iterator_range']['position'] == 33


def testTilesFromPTIFJpeg2K():
    imagePath = datastore.fetch('huron.image2_jpeg2k.tif')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 9158
    assert tileMetadata['sizeY'] == 11273
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] == 20
    utilities.checkTilesZXY(source, tileMetadata)


def testThumbnails():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()
    # Now we should be able to get a thumbnail
    image, mimeType = source.getThumbnail()
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    defaultLength = len(image)
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    image, mimeType = source.getThumbnail(encoding='TIFF')
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.TIFFHeader)] == utilities.TIFFHeader
    image, mimeType = source.getThumbnail(jpegQuality=10)
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert len(image) < defaultLength
    image, mimeType = source.getThumbnail(jpegSubsampling=2)
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert len(image) < defaultLength
    with pytest.raises(Exception):
        source.getThumbnail(encoding='unknown')
    # Test width and height using PNGs
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert max(width, height) == 256
    # We know that we are using an example where the width is greater than
    # the height
    origWidth = int(tileMetadata['sizeX'] *
                    2 ** -(tileMetadata['levels'] - 1))
    origHeight = int(tileMetadata['sizeY'] *
                     2 ** -(tileMetadata['levels'] - 1))
    image, mimeType = source.getThumbnail(encoding='PNG', width=200)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 200
    assert height == int(width * origHeight / origWidth)
    image, mimeType = source.getThumbnail(encoding='PNG', height=200)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == int(height * origWidth / origHeight)
    assert height == 200
    image, mimeType = source.getThumbnail(encoding='PNG', width=180, height=180)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 180
    assert height == int(width * origHeight / origWidth)
    # Test asking for fill values
    image, mimeType = source.getThumbnail(encoding='PNG', width=180, height=180, fill='none')
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 180
    assert height == int(width * origHeight / origWidth)
    image, mimeType = source.getThumbnail(encoding='PNG', width=180, height=180, fill='pink')
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 180
    assert height == 180
    nextimage, mimeType = source.getThumbnail(encoding='PNG', width=180, height=180, fill='#ffff00')
    (width, height) = struct.unpack('!LL', nextimage[16:24])
    assert width == 180
    assert height == 180
    assert image != nextimage
    nextimage, mimeType = source.getThumbnail(
        encoding='PNG', width=180, height=180, fill='corner:black')
    (width, height) = struct.unpack('!LL', nextimage[16:24])
    assert width == 180
    assert height == 180
    assert image != nextimage
    # Test bad parameters
    badParams = [
        ({'encoding': 'invalid'}, 'Invalid encoding'),
        ({'width': 'invalid'}, 'Invalid width or height'),
        ({'width': 0}, 'Invalid width or height'),
        ({'width': -5}, 'Invalid width or height'),
        ({'height': 'invalid'}, 'Invalid width or height'),
        ({'height': 0}, 'Invalid width or height'),
        ({'height': -5}, 'Invalid width or height'),
        ({'jpegQuality': 'invalid'}, 'ValueError'),
        ({'jpegSubsampling': 'invalid'}, 'TypeError'),
        ({'fill': 'not a color'}, 'unknown color'),
    ]
    for entry in badParams:
        with pytest.raises(Exception):
            source.getThumbnail(**entry[0])


@pytest.mark.parametrize(('badParams', 'errMessage'), [
    ({'encoding': 'invalid', 'width': 10}, 'Invalid encoding'),
    ({'output': {'maxWidth': 'invalid'}}, 'ValueError'),
    ({'output': {'maxWidth': -5}}, 'Invalid output width or height'),
    ({'output': {'maxWidth': None, 'maxHeight': 'invalid'}}, 'ValueError'),
    ({'output': {'maxWidth': None, 'maxHeight': -5}}, 'Invalid output width or height'),
    ({'jpegQuality': 'invalid'}, 'ValueError'),
    ({'jpegSubsampling': 'invalid'}, 'TypeError'),
    ({'region': {'left': 'invalid'}}, 'TypeError'),
    ({'region': {'right': 'invalid'}}, 'TypeError'),
    ({'region': {'top': 'invalid'}}, 'TypeError'),
    ({'region': {'bottom': 'invalid'}}, 'TypeError'),
    ({'region': {'width': 'invalid'}}, 'TypeError'),
    ({'region': {'height': 'invalid'}}, 'TypeError'),
    ({'region': {'units': 'invalid'}}, 'Invalid units'),
    ({'region': {'unitsWH': 'invalid'}}, 'Invalid units'),
])
def testRegionBadParameters(badParams, errMessage):
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    params = {'output': {'maxWidth': 400}}
    nestedUpdate(params, badParams)
    with pytest.raises(Exception):
        source.getRegion(**params)


def testRegions():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()

    # Get a small region for testing.  Our test file is sparse, so
    # initially get a region where there is full information.
    params = {'region': {'width': 1000, 'height': 1000, 'left': 48000, 'top': 3000}}
    region = params['region']
    image, mimeType = source.getRegion(**params)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    origImage = image
    image, mimeType = source.getRegion(encoding='PNG', **params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    # Test using negative offsets
    region['left'] -= tileMetadata['sizeX']
    region['top'] -= tileMetadata['sizeY']
    image, mimeType = source.getRegion(**params)
    assert image == origImage
    # We should get the same image using right and bottom
    params['region'] = region = {
        'left': region['left'],
        'top': region['top'],
        'right': region['left'] + 1000,
        'bottom': region['top'] + 1000}
    image, mimeType = source.getRegion(**params)
    assert image == origImage
    params['region'] = {
        'width': 1000,
        'height': 1000,
        'right': region['right'],
        'bottom': region['bottom']}
    image, mimeType = source.getRegion(**params)
    assert image == origImage
    # Fractions should get us the same results
    params['region'] = {
        'width': 1000.0 / tileMetadata['sizeX'],
        'height': 1000.0 / tileMetadata['sizeY'],
        'left': 48000.0 / tileMetadata['sizeX'],
        'top': 3000.0 / tileMetadata['sizeY'],
        'units': 'fraction'}
    image, mimeType = source.getRegion(**params)
    assert image == origImage
    # We can use base_pixels for width and height and fractions for top and
    # left
    params['region'] = {
        'width': 1000,
        'height': 1000,
        'left': 48000.0 / tileMetadata['sizeX'],
        'top': 3000.0 / tileMetadata['sizeY'],
        'units': 'fraction',
        'unitsWH': 'base'}
    image, mimeType = source.getRegion(**params)
    assert image == origImage

    # 0-sized results are allowed
    params = {'region': {'width': 1000, 'height': 0, 'left': 48000, 'top': 3000}}
    image, mimeType = source.getRegion(**params)
    assert image == b''

    # Test scaling (and a sparse region from our file)
    params = {'region': {'width': 2000, 'height': 1500},
              'output': {'maxWidth': 500, 'maxHeight': 500},
              'encoding': 'PNG'}
    image, mimeType = source.getRegion(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 500
    assert height == 375

    # Test fill
    params['fill'] = 'none'
    image, mimeType = source.getRegion(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 500
    assert height == 375
    params['fill'] = '#ff00ff'
    image, mimeType = source.getRegion(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 500
    assert height == 500
    params['region']['width'] = 1500
    nextimage, mimeType = source.getRegion(**params)
    assert nextimage[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', nextimage[16:24])
    assert width == 500
    assert height == 500
    assert image != nextimage


def testRegionTiledOutputIsTiled():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    # TIFF isn't tiled and has only one layer
    params = {'output': {'maxWidth': 500, 'maxHeight': 500},
              'encoding': 'TIFF'}
    image, mimeType = source.getRegion(**params)
    info = tifftools.read_tiff(io.BytesIO(image))
    assert len(info['ifds']) == 1
    assert tifftools.Tag.StripOffsets.value in info['ifds'][0]['tags']
    assert tifftools.Tag.TileOffsets.value not in info['ifds'][0]['tags']

    # TILED is tiled and has multiple layers
    params = {'output': {'maxWidth': 500, 'maxHeight': 500},
              'encoding': 'TILED'}
    image, mimeType = source.getRegion(**params)
    info = tifftools.read_tiff(image)
    assert len(info['ifds']) == 2
    assert tifftools.Tag.StripOffsets.value not in info['ifds'][0]['tags']
    assert tifftools.Tag.TileOffsets.value in info['ifds'][0]['tags']
    os.unlink(image)

    # Bigger outputs should have more layers
    params = {'output': {'maxWidth': 3000, 'maxHeight': 3000},
              'encoding': 'TILED'}
    image, mimeType = source.getRegion(**params)
    info = tifftools.read_tiff(image)
    assert len(info['ifds']) == 5
    assert tifftools.Tag.StripOffsets.value not in info['ifds'][0]['tags']
    assert tifftools.Tag.TileOffsets.value in info['ifds'][0]['tags']
    os.unlink(image)


def testGetTiledRegionAsFile():
    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image_source_tiff.open(imagePath)
    with tempfile.TemporaryDirectory() as temp_dir:
        resultPath = os.path.join(temp_dir, 'test_files', 'region.tiff')
        region, _ = ts.getRegion(
            output=dict(maxWidth=1024, maxHeight=1024, path=resultPath),
            encoding='TILED',
        )
        large_image_source_tiff.open(str(region))
        assert region.exists()
        assert region.name == 'region.tiff'
        assert os.path.exists(resultPath)
        region.unlink()


def testRegionTiledOutputLetterbox():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    params = {'output': {'maxWidth': 500, 'maxHeight': 500},
              'fill': 'pink',
              'encoding': 'TILED'}
    image, mimeType = source.getRegion(**params)
    result = large_image_source_tiff.open(str(image))
    assert result.sizeX == 500
    assert result.sizeY == 500
    os.unlink(image)


def testPixel():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    # Test bad parameters
    badParams = [
        ({'left': 'invalid'}, 'TypeError'),
        ({'top': 'invalid'}, 'TypeError'),
        ({'units': 'invalid'}, 'Invalid units'),
    ]
    for entry in badParams:
        with pytest.raises(Exception):
            source.getPixel(region=entry[0])

    # Test a good query
    pixel = source.getPixel(region={'left': 48000, 'top': 3000})
    assert 235 < pixel['r'] < 240
    assert 246 < pixel['g'] < 250
    assert 241 < pixel['b'] < 245
    # If it is outside of the image, we get an empty result
    pixel = source.getPixel(region={'left': 148000, 'top': 3000})
    assert pixel == {}


def testTilesAssociatedImages():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)

    imageList = source.getAssociatedImagesList()
    assert imageList == ['label', 'macro']
    image, mimeType = source.getAssociatedImage('label')
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    image, mimeType = source.getAssociatedImage('label', encoding='PNG', width=256, height=256)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert max(width, height) == 256
    # Test missing associated image
    assert source.getAssociatedImage('nosuchimage') is None


def testTilesFromSCN():
    imagePath = datastore.fetch('sample_leica.scn')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 512
    assert tileMetadata['tileHeight'] == 512
    assert tileMetadata['sizeX'] == 4737
    assert tileMetadata['sizeY'] == 6338
    assert tileMetadata['levels'] == 5
    assert tileMetadata['magnification'] == 20
    utilities.checkTilesZXY(source, tileMetadata)


def testOrientations():
    testDir = os.path.dirname(os.path.realpath(__file__))
    testResults = {
        0: {'shape': (100, 66, 1), 'pixels': (0, 0, 0, 255, 0, 255, 0, 255)},
        1: {'shape': (100, 66, 1), 'pixels': (0, 0, 0, 255, 0, 255, 0, 255)},
        2: {'shape': (100, 66, 1), 'pixels': (0, 0, 133, 0, 0, 255, 255, 0)},
        3: {'shape': (100, 66, 1), 'pixels': (255, 0, 143, 0, 255, 0, 0, 0)},
        4: {'shape': (100, 66, 1), 'pixels': (0, 255, 0, 255, 255, 0, 0, 0)},
        5: {'shape': (66, 100, 1), 'pixels': (0, 0, 0, 255, 0, 255, 0, 255)},
        6: {'shape': (66, 100, 1), 'pixels': (0, 255, 0, 255, 141, 0, 0, 0)},
        7: {'shape': (66, 100, 1), 'pixels': (255, 0, 255, 0, 143, 0, 0, 0)},
        8: {'shape': (66, 100, 1), 'pixels': (0, 0, 255, 0, 0, 255, 255, 0)},
    }
    for orient in range(9):
        imagePath = os.path.join(testDir, 'test_files', 'test_orient%d.tif' % orient)
        source = large_image_source_tiff.open(imagePath)
        image, _ = source.getRegion(
            output={'maxWidth': 100, 'maxHeight': 100}, format=constants.TILE_FORMAT_NUMPY)
        assert image.shape == testResults[orient]['shape']
        assert (
            image[11][11][0], image[11][-11][0],
            image[image.shape[0] // 2][11][0], image[image.shape[0] // 2][-11][0],
            image[11][image.shape[1] // 2][0], image[-11][image.shape[1] // 2][0],
            image[-11][11][0], image[-11][-11][0],
        ) == testResults[orient]['pixels']


def testTilesFromMultipleTiledTIF():
    imagePath = datastore.fetch('JK-kidney_H3_4C_1-500sec.tif')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 16384
    assert tileMetadata['sizeY'] == 14848
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] == 40
    utilities.checkTilesZXY(source, tileMetadata)


def testStyleSwapChannels():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    # swap the green and blue channels
    sourceB = large_image_source_tiff.open(imagePath, style={'bands': [
        {'band': 'red', 'palette': ['#000', '#f00']},
        {'band': 'green', 'palette': ['#000', '#00f']},
        {'band': 'blue', 'palette': ['#000', '#0f0']},
    ]})
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    imageB = imageB[:, :, :3]
    assert np.any(image != imageB)
    assert np.all(image[:, :, 0] == imageB[:, :, 0])
    assert np.any(image[:, :, 1] != imageB[:, :, 1])
    assert np.all(image[:, :, 1] == imageB[:, :, 2])
    assert np.all(image[:, :, 2] == imageB[:, :, 1])


def testStyleClamp():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(
        imagePath, style=json.dumps({'min': 100, 'max': 200, 'clamp': True}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    sourceB = large_image_source_tiff.open(
        imagePath, style=json.dumps({'min': 100, 'max': 200, 'clamp': False}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert np.all(image[:, :, 3] == 255)
    assert np.any(imageB[:, :, 3] != 255)
    assert image[0][0][3] == 255
    assert imageB[0][0][3] == 0


def testStyleMinMaxThreshold():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(
        imagePath, style=json.dumps({'min': 'min', 'max': 'max'}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    sourceB = large_image_source_tiff.open(
        imagePath, style=json.dumps({'min': 'min:0.02', 'max': 'max:0.02'}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert np.any(image != imageB)
    assert image[0][0][0] == 252
    assert imageB[0][0][0] == 246
    sourceC = large_image_source_tiff.open(
        imagePath, style=json.dumps({'min': 'full', 'max': 'full'}))
    imageC, _ = sourceC.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert np.any(image != imageC)
    assert imageC[0][0][0] == 253


def testStyleDtypeAxis():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(
        imagePath, style=json.dumps({'dtype': 'uint16', 'axis': 1}))
    image, _ = source.getRegion(
        output={'maxWidth': 456, 'maxHeight': 96}, format=constants.TILE_FORMAT_NUMPY)
    assert image.shape[2] == 1
    assert image[0][0][0] == 65021

    source = large_image_source_tiff.open(
        imagePath, style=json.dumps({'dtype': 'source', 'axis': 1}))
    image, _ = source.getRegion(
        output={'maxWidth': 456, 'maxHeight': 96}, format=constants.TILE_FORMAT_NUMPY)
    assert image.shape[2] == 1
    assert image[0][0][0] == 253


def testStyleNoData():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(
        imagePath, style=json.dumps({'nodata': None}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    nodata = 86
    imageB = image
    # Pillow 9.0.0 changed how they decode JPEGs, so find a nodata value that
    # will cause a difference
    while np.all(imageB == image):
        nodata += 1
        sourceB = large_image_source_tiff.open(
            imagePath, style=json.dumps({'nodata': nodata}))
        imageB, _ = sourceB.getRegion(
            output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert np.all(image[:, :, 3] == 255)
    assert np.any(imageB[:, :, 3] != 255)


def testHistogram():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    hist = source.histogram(bins=8, output={'maxWidth': 1024}, resample=False)
    assert len(hist['histogram']) == 3
    assert hist['histogram'][0]['range'] == (0, 256)
    assert len(hist['histogram'][0]['bin_edges']) == 9
    assert len(list(hist['histogram'][0]['hist'])) == 8
    assert list(hist['histogram'][0]['bin_edges']) == [0, 32, 64, 96, 128, 160, 192, 224, 256]
    assert hist['histogram'][0]['samples'] == 700416

    hist = source.histogram(bins=256, output={'maxWidth': 1024},
                            resample=False, density=True)
    assert len(hist['histogram']) == 3
    assert hist['histogram'][0]['range'] == (0, 256)
    assert len(list(hist['histogram'][0]['hist'])) == 256
    assert 5e-5 < hist['histogram'][0]['hist'][128] < 7e-5
    assert hist['histogram'][0]['samples'] == 700416

    hist = source.histogram(bins=256, output={'maxWidth': 2048},
                            density=True, resample=False)
    assert hist['histogram'][0]['samples'] == 2801664
    assert 6e-5 < hist['histogram'][0]['hist'][128] < 8e-5

    hist = source.histogram(bins=512, output={'maxWidth': 2048}, resample=False)
    assert hist['histogram'][0]['range'] == (0, 256)
    assert len(hist['histogram'][0]['bin_edges']) == 513

    hist = source.histogram(bins=512, output={'maxWidth': 2048}, resample=False,
                            range='round')
    assert hist['histogram'][0]['range'] == (0, 256)
    assert len(hist['histogram'][0]['bin_edges']) == 257


def testSingleTileIteratorResample():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    tile = source.getSingleTile()
    assert tile['mm_x'] == 0.00025
    assert tile['width'] == 256
    tile = source.getSingleTile(
        tile_size={'width': 255, 'height': 255}, scale={'mm_x': 0.5e-3})
    assert tile['mm_x'] == 0.0005
    assert tile['width'] == 255
    tile = source.getSingleTile(
        tile_size={'width': 255, 'height': 255}, scale={'mm_x': 0.6e-3}, resample=False)
    assert tile['mm_x'] == 0.0005
    assert tile['width'] == 255
    assert tile['magnification'] == 20.0
    assert 'tile_mm_x' not in tile
    assert 'tile_magnification' not in tile
    tile = source.getSingleTile(
        tile_size={'width': 255, 'height': 255}, scale={'mm_x': 0.6e-3}, resample=True)
    assert tile['mm_x'] == pytest.approx(0.0006, 1e-3)
    assert tile['magnification'] == pytest.approx(16.667, 1e-3)
    assert tile['width'] == 255
    assert tile['tile_mm_x'] == 0.0005
    assert tile['tile_magnification'] == 20.0


def testInternalMetadata():
    imagePath = datastore.fetch('sample_image.ptif')
    source = large_image_source_tiff.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'xml' in metadata


def testFromTiffRGBJPEG():
    imagePath = datastore.fetch(
        'TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
    source = large_image_source_tiff.open(imagePath)
    tile = source.getSingleTile()
    # Handle ICC Profiles
    assert list(tile['tile'][0, 0]) == [243, 243, 243] or list(
        tile['tile'][0, 0]) == [242, 243, 242]


def testTilesFromMultiFrameTiff():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 2106
    assert tileMetadata['sizeY'] == 2016
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 3
    assert tileMetadata['frames'][1]['Frame'] == 1
    utilities.checkTilesZXY(source, tileMetadata)

    tile = source.getSingleTile()
    assert list(tile['tile'][0, 0]) == [7710]


def testTilesFromMultiFrameTiffWithSubIFD():
    imagePath = datastore.fetch('sample.subifd.ome.tif')
    source = large_image_source_tiff.open(imagePath, frame=1)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 2106
    assert tileMetadata['sizeY'] == 2016
    assert tileMetadata['levels'] == 5
    assert len(tileMetadata['frames']) == 3
    assert tileMetadata['frames'][1]['Frame'] == 1
    utilities.checkTilesZXY(source, tileMetadata)

    tile = source.getSingleTile()
    assert list(tile['tile'][0, 0]) == [7710]


def testTilesFromMissingLayer():
    imagePath = datastore.fetch('one_layer_missing_tiles.tiff')
    source = large_image_source_tiff.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 5477
    assert tileMetadata['sizeY'] == 4515
    assert tileMetadata['levels'] == 6
    with pytest.raises(Exception):
        utilities.checkTilesZXY(source, tileMetadata)
    utilities.checkTilesZXY(source, tileMetadata, {'sparseFallback': True})


def testTileFrames():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_tiff.open(imagePath)

    params = {'encoding': 'PNG', 'output': {'maxWidth': 200, 'maxHeight': 200}}
    image, mimeType = source.tileFrames(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 400
    assert height == 382

    params['fill'] = 'corner:black'
    image, mimeType = source.tileFrames(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 400
    assert height == 400

    params['framesAcross'] = 3
    image, mimeType = source.tileFrames(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 600
    assert height == 200

    params['frameList'] = [0, 2]
    image, mimeType = source.tileFrames(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 400
    assert height == 200

    params['frameList'] = [0]
    image, mimeType = source.tileFrames(**params)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 200
    assert height == 200

    params.pop('frameList')
    params['encoding'] = 'TILED'
    image, mimeType = source.tileFrames(**params)
    info = tifftools.read_tiff(image)
    assert len(info['ifds']) == 3
    os.unlink(image)


def testExtraOverview():
    imagePath = datastore.fetch('extraoverview.tiff')
    source = large_image_source_tiff.open(imagePath)
    assert len([d for d in source._tiffDirectories if d is not None]) == 3
