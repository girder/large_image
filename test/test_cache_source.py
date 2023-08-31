import sys

import pytest

import large_image
from large_image.cache_util import cachesClear

from .datastore import datastore


@pytest.mark.singular()
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


@pytest.mark.singular()
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


@pytest.mark.skipif(sys.version_info < (3, 7),
                    reason='requires python >= 3.7 for a source with the issue')
@pytest.mark.singular()
def testCacheSourceBadStyle():
    cachesClear()
    imagePath = datastore.fetch('ITGA3Hi_export_crop2.nd2')
    ts1 = large_image.open(imagePath, style='{"bands": [{"max": 128}]}')
    tile1 = ts1.getTile(0, 0, 0)
    # With nd2 files, a bad style could cause a future segfault
    with pytest.raises(Exception):
        large_image.open(imagePath, style='{"bands": [{%,"max": 128}]}')
    ts2 = large_image.open(imagePath, style='{"bands": [{"max": 160}]}')
    tile2 = ts2.getTile(0, 0, 0)
    assert tile1 == tile2
    ts1 = ts2 = None
    cachesClear()
