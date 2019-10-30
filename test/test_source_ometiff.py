# -*- coding: utf-8 -*-

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
    assert len(tileMetadata['frames']) == 5
    utilities.checkTilesZXY(source, tileMetadata)
