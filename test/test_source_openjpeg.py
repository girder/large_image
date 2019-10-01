# -*- coding: utf-8 -*-

import large_image_source_openjpeg

from . import utilities


def testTilesFromOpenJPEG():
    imagePath = utilities.externaldata('data/sample_image.jp2.sha512')
    source = large_image_source_openjpeg.OpenjpegFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 4500
    assert tileMetadata['sizeY'] == 5800
    assert tileMetadata['levels'] == 6
    assert tileMetadata['magnification'] == 40
    utilities.checkTilesZXY(source, tileMetadata)
