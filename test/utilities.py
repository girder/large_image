import math

import pytest

JFIFHeader = b'\xff\xd8\xff\xe0\x00\x10JFIF'
JPEGHeader = b'\xff\xd8\xff'
PNGHeader = b'\x89PNG'
TIFFHeader = b'II\x2a\x00'
BigTIFFHeader = b'II\x2b\x00'


def checkTilesZXY(source, metadata, tileParams=None, imgHeader=JPEGHeader):
    """
    Test that the tile server is serving images.

    :param source: the tile source.
    :param metadata: tile information used to determine the expected
                     valid queries.  If 'sparse' is added to it, tiles
                     are allowed to not exist above that level.
    :param tileParams: optional parameters to send to the tile query.
    :param imgHeader: if something other than a JPEG is expected, this is
                      the first few bytes of the expected image.
    """
    if tileParams is None:
        tileParams = {}
    # We should get images for all valid levels, but only within the
    # expected range of tiles.
    for z in range(metadata.get('minLevel', 0), metadata['levels']):
        maxX = int(math.ceil(float(metadata['sizeX']) * 2 ** (
            z - metadata['levels'] + 1) / metadata['tileWidth']) - 1)
        maxY = int(math.ceil(float(metadata['sizeY']) * 2 ** (
            z - metadata['levels'] + 1) / metadata['tileHeight']) - 1)
        # Check the four corners on each level
        for (x, y) in ((0, 0), (maxX, 0), (0, maxY), (maxX, maxY)):
            try:
                image = source.getTile(x, y, z, **tileParams)
                assert image[:len(imgHeader)] == imgHeader
            except Exception:
                if not metadata.get('sparse') or z <= metadata['sparse']:
                    raise
        # Check out of range each level
        for (x, y) in ((-1, 0), (maxX + 1, 0), (0, -1), (0, maxY + 1)):
            with pytest.raises(Exception):
                source.getTile(x, y, z, **tileParams)
    # Check negative z level
    with pytest.raises(Exception):
        source.getTile(0, 0, -1, **tileParams)
    # Check non-integer z level
    with pytest.raises(Exception):
        source.getTile(0, 0, 'abc', **tileParams)
    # If we set the minLevel, test one lower than it
    if 'minLevel' in metadata:
        with pytest.raises(Exception):
            source.getTile(0, 0, metadata['minLevel'] - 1, **tileParams)
    # Check too large z level
    with pytest.raises(Exception):
        source.getTile(0, 0, metadata['levels'], **tileParams)
