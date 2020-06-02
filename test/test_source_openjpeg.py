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


def testAssociatedImagesFromOpenJPEG():
    imagePath = utilities.externaldata('data/JK-kidney_B-gal_H3_4C_1-500sec.jp2.sha512')
    source = large_image_source_openjpeg.OpenjpegFileTileSource(imagePath)

    imageList = source.getAssociatedImagesList()
    assert imageList == ['label', 'macro']
    image, mimeType = source.getAssociatedImage('macro')
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    # Test missing associated image
    assert source.getAssociatedImage('nosuchimage') is None


def testBelowLevelTilesFromOpenJPEG():
    from large_image.cache_util import cachesClear

    imagePath = utilities.externaldata('data/JK-kidney_B-gal_H3_4C_1-500sec.jp2.sha512')
    origMin = large_image_source_openjpeg.OpenjpegFileTileSource._minTileSize
    origMax = large_image_source_openjpeg.OpenjpegFileTileSource._maxTileSize
    large_image_source_openjpeg.OpenjpegFileTileSource._minTileSize = 64
    large_image_source_openjpeg.OpenjpegFileTileSource._maxTileSize = 64
    # Clear the cache to make sure we use our required max tile size.
    cachesClear()
    source = large_image_source_openjpeg.OpenjpegFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 64
    assert tileMetadata['tileHeight'] == 64
    assert tileMetadata['sizeX'] == 16384
    assert tileMetadata['sizeY'] == 14848
    assert tileMetadata['levels'] == 9
    assert tileMetadata['magnification'] == 40
    utilities.checkTilesZXY(source, tileMetadata)
    large_image_source_openjpeg.OpenjpegFileTileSource._minTileSize = origMin
    large_image_source_openjpeg.OpenjpegFileTileSource._maxTileSize = origMax
    cachesClear()


def testInternalMetadata():
    imagePath = utilities.externaldata('data/sample_image.jp2.sha512')
    source = large_image_source_openjpeg.OpenjpegFileTileSource(imagePath)
    metadata = source.getInternalMetadata()
    assert 'ScanInfo' in metadata['xml']
