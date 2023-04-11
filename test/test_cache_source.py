import pytest

import large_image
from large_image.cache_util import cachesClear

from .datastore import datastore


@pytest.mark.singular
def testCacheSourceStyle():
    cachesClear()
    imagePath = datastore.fetch('sample_image.ptif')
    ts1 = large_image.open(imagePath)
    ts2 = large_image.open(imagePath, style={'max': 128})
    ts3 = large_image.open(imagePath, style={'max': 160})
    assert id(ts1) != id(ts2)
    assert id(ts2) != id(ts3)
    tile1 = ts1.getTile(0, 0, 4)
    assert ts1.getTile(0, 0, 4) is not None
    assert ts2.getTile(0, 0, 4) is not None
    assert ts3.getTile(0, 0, 4) is not None
    cachesClear()
    assert ts1.getTile(0, 0, 4) == tile1
    del ts1
    assert ts2.getTile(1, 0, 4) is not None
    cachesClear()
    assert ts2.getTile(2, 0, 4) is not None
    ts1 = large_image.open(imagePath)
    assert ts1.getTile(0, 0, 4) == tile1


@pytest.mark.singular
def testCacheSourceStyleFirst():
    cachesClear()
    imagePath = datastore.fetch('sample_image.ptif')
    ts2 = large_image.open(imagePath, style={'max': 128})
    ts1 = large_image.open(imagePath)
    assert id(ts1) != id(ts2)
    tile1 = ts1.getTile(0, 0, 4)
    assert ts1.getTile(0, 0, 4) is not None
    assert ts2.getTile(0, 0, 4) is not None
    del ts1
    assert ts2.getTile(1, 0, 4) is not None
    cachesClear()
    assert ts2.getTile(2, 0, 4) is not None
    ts1 = large_image.open(imagePath)
    assert ts1.getTile(0, 0, 4) == tile1
