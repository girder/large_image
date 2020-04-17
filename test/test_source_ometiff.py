# -*- coding: utf-8 -*-

import json
import numpy

from large_image.constants import TILE_FORMAT_NUMPY
import large_image_source_ometiff

from . import utilities


def testTilesFromOMETiff():
    imagePath = utilities.externaldata('data/sample.ome.tif.sha512')
    source = large_image_source_ometiff.OMETiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 2106
    assert tileMetadata['sizeY'] == 2016
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 3
    assert tileMetadata['frames'][1]['Frame'] == 1
    assert tileMetadata['frames'][1]['Index'] == 0
    assert tileMetadata['frames'][1]['IndexC'] == 1
    assert tileMetadata['IndexRange'] == {'IndexC': 3}
    utilities.checkTilesZXY(source, tileMetadata)


def testTilesFromStripOMETiff():
    imagePath = utilities.externaldata('data/DDX58_AXL_EGFR_well2_XY01.ome.tif.sha512')
    source = large_image_source_ometiff.OMETiffFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 1024
    assert tileMetadata['sizeY'] == 1022
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 145
    assert tileMetadata['frames'][101]['Frame'] == 101
    assert tileMetadata['frames'][101]['Index'] == 20
    assert tileMetadata['frames'][101]['IndexC'] == 1
    assert tileMetadata['frames'][101]['IndexZ'] == 20
    assert tileMetadata['channels'] == ['Brightfield', 'CY3', 'A594', 'CY5', 'DAPI']
    assert tileMetadata['IndexRange'] == {'IndexC': 5, 'IndexZ': 29}
    utilities.checkTilesZXY(source, tileMetadata)


def testOMETiffAre16Bit():
    imagePath = utilities.externaldata('data/DDX58_AXL_EGFR_well2_XY01.ome.tif.sha512')
    source = large_image_source_ometiff.OMETiffFileTileSource(imagePath)
    tile = next(source.tileIterator(format=TILE_FORMAT_NUMPY))['tile']
    assert tile.dtype == numpy.uint16
    assert tile[15][15][0] == 17852

    region, _ = source.getRegion(format=TILE_FORMAT_NUMPY)
    assert region.dtype == numpy.uint16
    assert region[300][300][0] == 17816


def testStyleAutoMinMax():
    imagePath = utilities.externaldata('data/DDX58_AXL_EGFR_well2_XY01.ome.tif.sha512')
    source = large_image_source_ometiff.OMETiffFileTileSource(imagePath)
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    sourceB = large_image_source_ometiff.OMETiffFileTileSource(
        imagePath, style=json.dumps({'min': 'auto', 'max': 'auto'}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    imageB = imageB[:, :, :1]
    assert numpy.any(image != imageB)
    assert image.shape == imageB.shape
    assert image[128][128][0] < imageB[128][128][0]
    assert image[0][128][0] < imageB[0][128][0]
    assert image[240][128][0] < imageB[240][128][0]


def testInternalMetadata():
    imagePath = utilities.externaldata('data/sample.ome.tif.sha512')
    source = large_image_source_ometiff.OMETiffFileTileSource(imagePath)
    metadata = source.getInternalMetadata()
    assert 'omeinfo' in metadata
