import large_image

from . import utilities
from .datastore import datastore


def testTilesFromBioformats():
    import large_image_source_bioformats

    imagePath = datastore.fetch('HENormalN801.czi')
    source = large_image_source_bioformats.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 50577
    assert tileMetadata['sizeY'] == 17417
    assert tileMetadata['levels'] == 7
    # assert tileMetadata['magnification'] == pytest.approx(20, 1)
    utilities.checkTilesZXY(source, tileMetadata)


def testInternalMetadata():
    import large_image_source_bioformats

    imagePath = datastore.fetch('HENormalN801.czi')
    source = large_image_source_bioformats.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'sizeColorPlanes' in metadata


def testBioformatsJarVersion():
    import large_image_source_bioformats

    assert '.' in large_image_source_bioformats._getBioformatsVersion()


def testBioformatsDicomMonochome1():
    import large_image_source_bioformats

    imagePath = datastore.fetch('monochrome1.dcm')
    source = large_image_source_bioformats.open(imagePath)
    img, _ = source.getRegion(format=large_image.constants.TILE_FORMAT_NUMPY)
    assert img[255, 191, 0] == 618
