import large_image_source_dummy

import large_image


def testDummyTileSource():
    source = large_image_source_dummy.open()
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 0
    assert tileMetadata['tileHeight'] == 0
    assert tileMetadata['sizeX'] == 0
    assert tileMetadata['sizeY'] == 0
    assert tileMetadata['levels'] == 0
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    assert source.getTile(0, 0, 0) == b''


def testGetDummyTileSource():
    source = large_image.open('large_image://dummy')
    assert isinstance(source, large_image_source_dummy.DummyTileSource)
