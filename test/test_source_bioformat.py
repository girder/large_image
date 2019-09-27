# -*- coding: utf-8 -*-

import large_image_source_bioformats

from . import utilities


def testTilesFromSimpleBioFormat():
    imagePath = utilities.externaldata('data/sample_Easy1.png.sha512')
    assert large_image_source_bioformats.SimpleBioFormatsFileTileSource.canRead(imagePath) is True

    source = large_image_source_bioformats.SimpleBioFormatsFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 1790
    assert tileMetadata['sizeY'] == 1046
    assert tileMetadata['levels'] == 4
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    utilities.checkTilesZXY(source, tileMetadata)
