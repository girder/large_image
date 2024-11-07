import large_image_source_openjpeg
import pytest

from . import utilities
from .datastore import datastore


def testTilesFromOpenJPEG():
    imagePath = datastore.fetch('sample_image.jp2')
    source = large_image_source_openjpeg.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 4500
    assert tileMetadata['sizeY'] == 5800
    assert tileMetadata['levels'] == 6
    assert tileMetadata['magnification'] == 40
    utilities.checkTilesZXY(source, tileMetadata)


def testAssociatedImagesFromOpenJPEG():
    imagePath = datastore.fetch('JK-kidney_B-gal_H3_4C_1-500sec.jp2')
    source = large_image_source_openjpeg.open(imagePath)

    imageList = source.getAssociatedImagesList()
    assert imageList == ['label', 'macro']
    image, mimeType = source.getAssociatedImage('macro')
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    # Test missing associated image
    assert source.getAssociatedImage('nosuchimage') is None


@pytest.mark.singular
def testBelowLevelTilesFromOpenJPEG():
    from large_image.cache_util import cachesClear

    imagePath = datastore.fetch('JK-kidney_B-gal_H3_4C_1-500sec.jp2')
    origMin = large_image_source_openjpeg.OpenjpegFileTileSource._minTileSize
    origMax = large_image_source_openjpeg.OpenjpegFileTileSource._maxTileSize
    large_image_source_openjpeg.OpenjpegFileTileSource._minTileSize = 64
    large_image_source_openjpeg.OpenjpegFileTileSource._maxTileSize = 64
    # Clear the cache to make sure we use our required max tile size.
    cachesClear()
    source = large_image_source_openjpeg.open(imagePath)
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
    imagePath = datastore.fetch('sample_image.jp2')
    source = large_image_source_openjpeg.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'ScanInfo' in metadata['xml']
