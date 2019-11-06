# -*- coding: utf-8 -*-

import json
import numpy
import os
import pytest
import struct

from large_image import constants
import large_image_source_tiff

from . import utilities


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
    assert large_image_source_tiff.TiffFileTileSource.canRead(imagePath) is False

    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    assert large_image_source_tiff.TiffFileTileSource.canRead(imagePath) is True
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 58368
    assert tileMetadata['sizeY'] == 12288
    assert tileMetadata['levels'] == 9
    tileMetadata['sparse'] = 5
    utilities.checkTilesZXY(source, tileMetadata)


def testTileIterator():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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


def testTileIteratorRetiling():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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
    imagePath = utilities.externaldata('data/huron.image2_jpeg2k.tif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 9158
    assert tileMetadata['sizeY'] == 11273
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] == 20
    utilities.checkTilesZXY(source, tileMetadata)


def testThumbnails():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    # Now we should be able to get a thumbnail
    image, mimeType = source.getThumbnail()
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    defaultLength = len(image)
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    image, mimeType = source.getThumbnail(encoding='TIFF')
    assert image[:len(utilities.TIFFHeader)] == utilities.TIFFHeader
    image, mimeType = source.getThumbnail(jpegQuality=10)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert len(image) < defaultLength
    image, mimeType = source.getThumbnail(jpegSubsampling=2)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert len(image) < defaultLength
    with pytest.raises(Exception):
        source.getThumbnail(encoding='unknown')
    # Test width and height using PNGs
    image, mimeType = source.getThumbnail(encoding='PNG')
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


def testRegions():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    # Test bad parameters
    badParams = [
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
    ]
    for entry in badParams:
        with pytest.raises(Exception):
            params = {'output': {'maxWidth': 400}}
            nestedUpdate(params, entry[0])
            source.getRegion(**params)

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


def testPixel():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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
    assert pixel == {'r': 237, 'g': 248, 'b': 242}
    # If it is outside of the image, we get an empty result
    pixel = source.getPixel(region={'left': 148000, 'top': 3000})
    assert pixel == {}


def testTilesAssociatedImages():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)

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
    imagePath = utilities.externaldata('data/sample_leica.scn.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
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
        source = large_image_source_tiff.TiffFileTileSource(imagePath)
        image, _ = source.getRegion(
            output={'maxWidth': 100, 'maxHeight': 100}, format=constants.TILE_FORMAT_NUMPY)
        assert image.shape == testResults[orient]['shape']
        assert (
            image[11][11][0], image[11][-11][0],
            image[image.shape[0] // 2][11][0], image[image.shape[0] // 2][-11][0],
            image[11][image.shape[1] // 2][0], image[-11][image.shape[1] // 2][0],
            image[-11][11][0], image[-11][-11][0]
        ) == testResults[orient]['pixels']


def testTilesFromMultipleTiledTIF():
    imagePath = utilities.externaldata('data/JK-kidney_H3_4C_1-500sec.tif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 16384
    assert tileMetadata['sizeY'] == 14848
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] == 40
    utilities.checkTilesZXY(source, tileMetadata)


def testStyleSwapChannels():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(imagePath)
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    # swap the green and blue channels
    sourceB = large_image_source_tiff.TiffFileTileSource(imagePath, style=json.dumps({'bands': [
        {'band': 'red', 'palette': ['#000', '#f00']},
        {'band': 'green', 'palette': ['#000', '#00f']},
        {'band': 'blue', 'palette': ['#000', '#0f0']},
    ]}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    imageB = imageB[:, :, :3]
    assert numpy.any(image != imageB)
    assert numpy.all(image[:, :, 0] == imageB[:, :, 0])
    assert numpy.any(image[:, :, 1] != imageB[:, :, 1])
    assert numpy.all(image[:, :, 1] == imageB[:, :, 2])
    assert numpy.all(image[:, :, 2] == imageB[:, :, 1])


def testStyleClamp():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(
        imagePath, style=json.dumps({'min': 100, 'max': 200, 'clamp': True}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    sourceB = large_image_source_tiff.TiffFileTileSource(
        imagePath, style=json.dumps({'min': 100, 'max': 200, 'clamp': False}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert numpy.all(image[:, :, 3] == 255)
    assert numpy.any(imageB[:, :, 3] != 255)
    assert image[0][0][3] == 255
    assert imageB[0][0][3] == 0


def testStyleNoData():
    imagePath = utilities.externaldata('data/sample_image.ptif.sha512')
    source = large_image_source_tiff.TiffFileTileSource(
        imagePath, style=json.dumps({'nodata': None}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    sourceB = large_image_source_tiff.TiffFileTileSource(
        imagePath, style=json.dumps({'nodata': 101}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=constants.TILE_FORMAT_NUMPY)
    assert numpy.all(image[:, :, 3] == 255)
    assert numpy.any(imageB[:, :, 3] != 255)
    assert image[12][215][3] == 255
    assert imageB[12][215][3] != 255
