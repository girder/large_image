import pytest

from large_image.cache_util import cachesClear

from . import utilities


def testTilesFromBioformats():
    import large_image_source_bioformats

    imagePath = utilities.externaldata('data/HENormalN801.czi.sha512')
    source = large_image_source_bioformats.BioformatsFileTileSource(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 50577
    assert tileMetadata['sizeY'] == 17417
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] == pytest.approx(20, 1)
    utilities.checkTilesZXY(source, tileMetadata)

    source = None
    cachesClear()


def testInternalMetadata():
    import large_image_source_bioformats

    imagePath = utilities.externaldata('data/HENormalN801.czi.sha512')
    source = large_image_source_bioformats.BioformatsFileTileSource(imagePath)
    metadata = source.getInternalMetadata()
    assert 'sizeColorPlanes' in metadata

    source = None
    cachesClear()
