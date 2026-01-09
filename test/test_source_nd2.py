import contextlib

with contextlib.suppress(ImportError):
    import large_image_source_nd2

import pytest

from . import utilities
from .datastore import datastore


def testTilesFromND2():
    imagePath = datastore.fetch('ITGA3Hi_export_crop2.nd2')
    source = large_image_source_nd2.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1022
    assert tileMetadata['sizeX'] == 1024
    assert tileMetadata['sizeY'] == 1022
    assert tileMetadata['levels'] == 1
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
    imagePath = datastore.fetch('ITGA3Hi_export_crop2.nd2')
    source = large_image_source_nd2.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'nd2' in metadata
