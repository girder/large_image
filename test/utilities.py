import math
import os
import pytest
import requests


JFIFHeader = b'\xff\xd8\xff\xe0\x00\x10JFIF'
JPEGHeader = b'\xff\xd8\xff'
PNGHeader = b'\x89PNG'
TIFFHeader = b'II\x2a\x00'


def externaldata(
        hashpath=None, hashvalue=None, destdir='externaldata', destname=None,
        sources=['https://data.kitware.com/api/v1/file/hashsum/sha512/{hashvalue}/download']):
    curDir = os.path.dirname(os.path.realpath(__file__))
    if hashpath:
        hashvalue = open(os.path.join(curDir, hashpath)).read().strip()
        if destname is None:
            destname = os.path.splitext(os.path.basename(hashpath))[0]
    realdestdir = os.path.join(os.environ.get('TOX_WORK_DIR', curDir), destdir)
    destpath = os.path.join(realdestdir, destname)
    if not os.path.exists(destpath):
        for source in sources:
            try:
                request = requests.get(source.format(hashvalue=hashvalue), stream=True)
                request.raise_for_status()
                if not os.path.exists(realdestdir):
                    os.makedirs(realdestdir)
                with open(destpath, 'wb') as out:
                    for buf in request.iter_content(65536):
                        out.write(buf)
                if os.path.getsize(destpath) == int(request.headers['content-length']):
                    break
                raise Exception('Incomplete download (got %d of %d) of %s' % (
                    os.path.getsize(destpath), int(request.headers['content-length'], destpath)))
            except Exception:
                pass
            if os.path.exists(destpath):
                os.unlink(destpath)
    if not os.path.exists(destpath):
        raise
    return destpath


def checkTilesZXY(source, metadata, tileParams={}, imgHeader=JPEGHeader):
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
