# -*- coding: utf-8 -*-

import pytest

import large_image_source_nd2

from . import utilities


def testTilesFromND2():
    imagePath = utilities.externaldata('data/ITGA3Hi_export_crop2.nd2.sha512')
    source = large_image_source_nd2.ND2FileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 1024
    assert tileMetadata['sizeY'] == 1022
    assert tileMetadata['levels'] == 3
    assert tileMetadata['magnification'] == pytest.approx(47, 1)
    assert len(tileMetadata['frames']) == 232
    assert tileMetadata['frames'][201]['Frame'] == 201
    assert tileMetadata['frames'][201]['Index'] == 50
    assert tileMetadata['frames'][201]['IndexC'] == 1
    assert tileMetadata['frames'][201]['IndexXY'] == 1
    assert tileMetadata['frames'][201]['IndexZ'] == 21
    assert tileMetadata['channels'] == ['Brightfield', 'YFP', 'A594', 'DAPI']
    assert tileMetadata['IndexRange'] == {'IndexC': 4, 'IndexXY': 2, 'IndexZ': 29}
    utilities.checkTilesZXY(source, tileMetadata)


def testInternalMetadata():
    imagePath = utilities.externaldata('data/ITGA3Hi_export_crop2.nd2.sha512')
    source = large_image_source_nd2.ND2FileTileSource(imagePath)
    metadata = source.getInternalMetadata()
    assert 'nd2' in metadata
