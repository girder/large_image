import pickle

import large_image_source_vips
import pytest

import large_image

from .datastore import datastore


@pytest.mark.parametrize('protocol', range(pickle.HIGHEST_PROTOCOL + 1))
def testPickleSource(protocol):
    imagePath = datastore.fetch('sample_image.ptif')
    ts1 = large_image.open(imagePath)
    ts2 = large_image.open(imagePath, style={'max': 128})
    ts3 = large_image.open(imagePath, style={'max': 160})
    thumb1 = ts1.getThumbnail()[0]
    thumb2 = ts2.getThumbnail()[0]
    thumb3 = ts3.getThumbnail()[0]

    assert thumb1 != thumb2
    assert thumb2 != thumb3
    assert thumb3 != thumb1

    pick1 = pickle.dumps(ts1, protocol=protocol)
    pick2 = pickle.dumps(ts2, protocol=protocol)
    pick3 = pickle.dumps(ts3, protocol=protocol)

    ts1p = pickle.loads(pick1)
    ts2p = pickle.loads(pick2)
    ts3p = pickle.loads(pick3)

    thumb1p = ts1p.getThumbnail()[0]
    thumb2p = ts2p.getThumbnail()[0]
    thumb3p = ts3p.getThumbnail()[0]

    assert thumb1 == thumb1p
    assert thumb2 == thumb2p
    assert thumb3 == thumb3p


def testPickleCrossProcess():
    import subprocess

    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image.open(imagePath)
    thumb = ts.getThumbnail()[0]

    result = subprocess.check_output([
        'python', '-c',
        'import pickle\nprint(len(pickle.loads(%r).getThumbnail()[0]))' % pickle.dumps(ts)])
    assert int(result) == len(thumb)


def testPickleTile():
    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image.open(imagePath)
    pick1 = pickle.dumps(ts.getSingleTile(tile_position=1))
    tile = pickle.loads(pick1)
    assert tile['x'] == 256
    assert tile['gwidth'] == 256


def testPickleNew():
    ts_zarr = large_image.new()
    pickle.dumps(ts_zarr)

    ts_vips = large_image_source_vips.new()
    with pytest.raises(pickle.PicklingError):
        pickle.dumps(ts_vips)
