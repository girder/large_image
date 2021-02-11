import hashlib
import math
import os
import pytest
import requests


JFIFHeader = b'\xff\xd8\xff\xe0\x00\x10JFIF'
JPEGHeader = b'\xff\xd8\xff'
PNGHeader = b'\x89PNG'
TIFFHeader = b'II\x2a\x00'

_checkedPaths = {}


def deleteIfWrongHash(destpath, hashvalue):
    """
    Check if a file at a path has a particular sha512 hash.  If not, delete it.
    If the file has been checked once, don't check it again.

    :param destpath: the file path.
    :param hashvalue: the sha512 hash hexdigest.
    """
    if os.path.exists(destpath) and destpath not in _checkedPaths and hashvalue:
        sha512 = hashlib.sha512()
        with open(destpath, 'rb') as f:
            while True:
                data = f.read(1024 * 1024)
                if not data:
                    break
                sha512.update(data)
        if sha512.hexdigest() != hashvalue:
            os.unlink(destpath)
        else:
            _checkedPaths[destpath] = True


def externaldata(
        hashpath=None, hashvalue=None, destdir='externaldata', destname=None,
        sources='https://data.kitware.com/api/v1/file/hashsum/sha512/{hashvalue}/download'):
    """
    Get a file from an external data source.  If the file has already been
    downloaded, check that it has the correct hash.

    :param hashpath: an optional path to a file that contains the hash value.
        There may be white space before or after the hashvalue.
    :param hashvalue: if no hashpath is specified, use this as a hash value.
    :param destdir: the location to store downloaded files.
    :param destname: if specified, the name of the file.  If hashpath is used
        and this is None, the basename of the hashpath is used for the
        destination name.
    :param sources: a string or list of strings that are url templates.
        `{hashvalue}` is replaced with the hashvalue.
    :returns: the path to the downloaded file.
    """
    if isinstance(sources, str):
        sources = [sources]
    curDir = os.path.dirname(os.path.realpath(__file__))
    if hashpath:
        hashvalue = open(os.path.join(curDir, hashpath)).read().strip()
        if destname is None:
            destname = os.path.splitext(os.path.basename(hashpath))[0]
    realdestdir = os.path.join(os.environ.get('TOX_WORK_DIR', curDir), destdir)
    destpath = os.path.join(realdestdir, destname)
    deleteIfWrongHash(destpath, hashvalue)
    if not os.path.exists(destpath):
        for source in sources:
            try:
                request = requests.get(source.format(hashvalue=hashvalue), stream=True)
                request.raise_for_status()
                if not os.path.exists(realdestdir):
                    os.makedirs(realdestdir)
                sha512 = hashlib.sha512()
                with open(destpath, 'wb') as out:
                    for buf in request.iter_content(65536):
                        out.write(buf)
                        sha512.update(buf)
                if os.path.getsize(destpath) == int(request.headers['content-length']):
                    if hashvalue and sha512.hexdigest() != hashvalue:
                        raise Exception('Download has wrong hash value - %s' % destpath)
                    break
                raise Exception('Incomplete download (got %d of %d) of %s' % (
                    os.path.getsize(destpath), int(request.headers['content-length']), destpath))
            except Exception:
                pass
            if os.path.exists(destpath):
                os.unlink(destpath)
    if not os.path.exists(destpath):
        raise Exception('Failed to get external data %s' % destpath)
    return destpath


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
