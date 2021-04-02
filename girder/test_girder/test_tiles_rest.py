import math
from unittest import mock
import os
import pytest
import requests
import shutil
import struct
import time

from girder.constants import SortDir
from girder.models.file import File
from girder.models.item import Item
from girder.models.setting import Setting
from girder.models.token import Token
from girder.models.user import User

from girder_jobs.constants import JobStatus
from girder_jobs.models.job import Job

from large_image import getTileSource
from girder_large_image import constants
from girder_large_image import getGirderTileSource
from girder_large_image import loadmodelcache
from girder_large_image.models.image_item import ImageItem

from . import girder_utilities as utilities


def _testTilesZXY(server, admin, itemId, metadata, tileParams=None,
                  imgHeader=utilities.JPEGHeader, token=None):
    """
    Test that the tile server is serving images.

    :param itemId: the item ID to get tiles from.
    :param metadata: tile information used to determine the expected
                     valid queries.  If 'sparse' is added to it, tiles
                     are allowed to not exist above that level.
    :param tileParams: optional parameters to send to the tile query.
    :param imgHeader: if something other than a JPEG is expected, this is
                      the first few bytes of the expected image.
    """
    if tileParams is None:
        tileParams = {}
    if token:
        kwargs = {'token': token}
    else:
        kwargs = {'user': admin}
    # We should get images for all valid levels, but only within the
    # expected range of tiles.
    for z in range(metadata.get('minLevel', 0), metadata['levels']):
        maxX = math.ceil(float(metadata['sizeX']) * 2 ** (
            z - metadata['levels'] + 1) / metadata['tileWidth']) - 1
        maxY = math.ceil(float(metadata['sizeY']) * 2 ** (
            z - metadata['levels'] + 1) / metadata['tileHeight']) - 1
        # Check the four corners on each level
        for (x, y) in ((0, 0), (maxX, 0), (0, maxY), (maxX, maxY)):
            resp = server.request(path='/item/%s/tiles/zxy/%d/%d/%d' % (
                itemId, z, x, y), params=tileParams, isJson=False,
                **kwargs)
            if (resp.output_status[:3] != b'200' and
                    metadata.get('sparse') and z > metadata['sparse']):
                assert utilities.respStatus(resp) == 404
                continue
            assert utilities.respStatus(resp) == 200
            image = utilities.getBody(resp, text=False)
            assert image[:len(imgHeader)] == imgHeader
        # Check out of range each level
        for (x, y) in ((-1, 0), (maxX + 1, 0), (0, -1), (0, maxY + 1)):
            resp = server.request(path='/item/%s/tiles/zxy/%d/%d/%d' % (
                itemId, z, x, y), params=tileParams, **kwargs)
            if x < 0 or y < 0:
                assert utilities.respStatus(resp) == 400
                assert 'must be positive integers' in resp.json['message']
            else:
                assert utilities.respStatus(resp) == 404
                assert ('does not exist' in resp.json['message'] or
                        'outside layer' in resp.json['message'])
    # Check negative z level
    resp = server.request(path='/item/%s/tiles/zxy/-1/0/0' % itemId,
                          params=tileParams, **kwargs)
    assert utilities.respStatus(resp) == 400
    assert 'must be positive integers' in resp.json['message']
    # Check non-integer z level
    resp = server.request(path='/item/%s/tiles/zxy/abc/0/0' % itemId,
                          params=tileParams, **kwargs)
    assert utilities.respStatus(resp) == 400
    assert 'must be integers' in resp.json['message']
    # If we set the minLevel, test one lower than it
    if 'minLevel' in metadata:
        resp = server.request(path='/item/%s/tiles/zxy/%d/0/0' % (
            itemId, metadata['minLevel'] - 1), params=tileParams, **kwargs)
        assert utilities.respStatus(resp) == 404
        assert 'layer does not exist' in resp.json['message']
    # Check too large z level
    resp = server.request(path='/item/%s/tiles/zxy/%d/0/0' % (
        itemId, metadata['levels']), params=tileParams, **kwargs)
    assert utilities.respStatus(resp) == 404
    assert 'layer does not exist' in resp.json['message']


def _createTestTiles(server, admin, params=None, info=None, error=None):
    """
    Discard any existing tile set on an item, then create a test tile set
    with some optional parameters.

    :param params: optional parameters to use for the tiles.
    :param info: if present, the tile information must match all values in
                 this dictionary.
    :param error: if present, expect to get an error from the tile info
                  query and ensure that this string is in the error
                  message.
    :returns: the tile information dictionary.
    """
    if params is None:
        params = {}
    try:
        resp = server.request(path='/item/test/tiles', user=admin,
                              params=params)
        if error:
            assert utilities.respStatus(resp) == 400
            assert error in resp.json['message']
            return None
    except AssertionError as exc:
        if error:
            assert error in exc.args[0]
            return
        else:
            raise
    assert utilities.respStatus(resp) == 200
    infoDict = resp.json
    if info:
        for key in info:
            assert infoDict[key] == info[key]
    return infoDict


def _postTileViaHttp(server, admin, itemId, fileId, jobAction=None, data=None, convert=False):
    """
    When we know we need to process a job, we have to use an actual http
    request rather than the normal simulated request to cherrypy.  This is
    required because cherrypy needs to know how it was reached so that
    girder_worker can reach it when done.

    :param itemId: the id of the item with the file to process.
    :param fileId: the id of the file that should be processed.
    :param jobAction: if 'delete', delete the job immediately.
    :param data: if not None, pass this as the data to the POST request.  If
        specified, fileId is ignored (pass as part of the data dictionary if
        it is required).
    :returns: metadata from the tile if the conversion was successful,
              False if it converted but didn't result in useable tiles, and
              None if it failed.
    """
    headers = {
        'Accept': 'application/json',
        'Girder-Token': str(Token().createToken(admin)['_id'])
    }
    req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles' % (
        server.boundPort, itemId), headers=headers,
        data={'fileId': fileId} if data is None else data)
    assert req.status_code == 200

    if jobAction == 'delete':
        Job().remove(Job().find({}, sort=[('_id', SortDir.DESCENDING)])[0])
        # Wait for the job to be complete
        starttime = time.time()
        while time.time() - starttime < 30:
            req = requests.get(
                'http://127.0.0.1:%d/api/v1/worker/status' % server.boundPort, headers=headers)
            resp = req.json()
            if resp.get('active') and not len(next(iter(resp['active'].items()))[1]):
                resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
                if (utilities.respStatus(resp) == 400 and
                        'No large image file' in resp.json['message']):
                    break
            time.sleep(0.1)
    else:
        # If we ask to create the item again right away, we should be told that
        # either there is already a job running or the item has already been
        # added
        req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles' % (
            server.boundPort, itemId), headers=headers,
            data={'fileId': fileId} if data is None else data)
        assert req.status_code == 400
        assert ('Item already has' in req.json()['message'] or
                'Item is scheduled' in req.json()['message'])

    starttime = time.time()
    resp = None
    while time.time() - starttime < 30:
        try:
            resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
            assert utilities.respStatus(resp) == 200
            break
        except AssertionError:
            result = resp.json['message']
            if "didn't meet requirements" in result:
                return False
            if 'No large image file' in result:
                return None
            assert 'is still pending creation' in result
        time.sleep(0.1)
    assert utilities.respStatus(resp) == 200
    return resp.json


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromPTIF(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    # We should already have tile information.  Ask to delete it so we can
    # do other tests
    resp = server.request(path='/item/%s/tiles' % itemId, method='DELETE',
                          user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True
    # Now we shouldn't have tile information
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId, user=admin)
    assert utilities.respStatus(resp) == 404
    assert 'No large image file' in resp.json['message']
    # Asking to delete the tile information succeeds but does nothing
    resp = server.request(path='/item/%s/tiles' % itemId, method='DELETE',
                          user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is False
    # Ask to make this a tile-based item with an invalid file ID
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin, params={'fileId': itemId})
    assert utilities.respStatus(resp) == 400
    assert 'No such file' in resp.json['message']

    # Ask to make this a tile-based item properly
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin, params={'fileId': fileId})
    assert utilities.respStatus(resp) == 200
    # Now the tile request should tell us about the file.  These are
    # specific to our test file
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 58368
    assert tileMetadata['sizeY'] == 12288
    assert tileMetadata['levels'] == 9
    assert tileMetadata['magnification'] == 40
    assert tileMetadata['mm_x'] == 0.00025
    assert tileMetadata['mm_y'] == 0.00025
    tileMetadata['sparse'] = 5
    _testTilesZXY(server, admin, itemId, tileMetadata)

    # Check that we conditionally get JFIF headers
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JFIFHeader)] != utilities.JFIFHeader

    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False,
                          params={'encoding': 'JFIF'})
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JFIFHeader)] == utilities.JFIFHeader

    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False,
                          additionalHeaders=[('User-Agent', 'iPad')])
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JFIFHeader)] == utilities.JFIFHeader

    resp = server.request(
        path='/item/%s/tiles/zxy/0/0/0' % itemId, user=admin,
        isJson=False, additionalHeaders=[(
            'User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X '
            '10_12_3) AppleWebKit/602.4.8 (KHTML, like Gecko) '
            'Version/10.0.3 Safari/602.4.8')])
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JFIFHeader)] == utilities.JFIFHeader

    resp = server.request(
        path='/item/%s/tiles/zxy/0/0/0' % itemId, user=admin,
        isJson=False, additionalHeaders=[(
            'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
            'Safari/537.36')])
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JFIFHeader)] != utilities.JFIFHeader

    # Ask to make this a tile-based item again
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin, params={'fileId': fileId})
    assert utilities.respStatus(resp) == 400
    assert 'Item already has' in resp.json['message']

    # We should be able to delete the large image information
    resp = server.request(path='/item/%s/tiles' % itemId, method='DELETE',
                          user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True

    # We should no longer have tile information
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']

    # We should be able to re-add it (we are also testing that fileId is
    # optional if there is only one file).
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin)
    assert utilities.respStatus(resp) == 200
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromTest(server, admin, fsAssetstore):
    publicFolder = utilities.namedFolder(admin, 'Public')
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    items = [{'itemId': str(file['itemId']), 'fileId': str(file['_id'])}]
    # We should already have tile information.  Ask to delete it so we can
    # do other tests
    resp = server.request(path='/item/%s/tiles' % str(file['itemId']),
                          method='DELETE', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True
    # Create a second item
    resp = server.request(path='/item', method='POST', user=admin,
                          params={'folderId': publicFolder['_id'],
                                  'name': 'test'})
    assert utilities.respStatus(resp) == 200
    itemId = str(resp.json['_id'])
    items.append({'itemId': itemId})
    # Check that we can't create a tile set with another item's file
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin,
                          params={'fileId': items[0]['fileId']})
    assert utilities.respStatus(resp) == 400
    assert 'The provided file must be in the provided item' in resp.json['message']
    # Now create a test tile with the default options
    params = {'encoding': 'JPEG'}
    meta = _createTestTiles(server, admin, params, {
        'tileWidth': 256, 'tileHeight': 256,
        'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
    })
    _testTilesZXY(server, admin, 'test', meta, params)
    # Test most of our parameters in a single special case
    params = {
        'minLevel': 2,
        'maxLevel': 5,
        'tileWidth': 160,
        'tileHeight': 120,
        'sizeX': 5000,
        'sizeY': 3000,
        'encoding': 'JPEG'
    }
    meta = _createTestTiles(server, admin, params, {
        'tileWidth': 160, 'tileHeight': 120,
        'sizeX': 5000, 'sizeY': 3000, 'levels': 6
    })
    meta['minLevel'] = 2
    _testTilesZXY(server, admin, 'test', meta, params)
    # Test the fractal tiles with PNG
    params = {'fractal': 'true'}
    meta = _createTestTiles(server, admin, params, {
        'tileWidth': 256, 'tileHeight': 256,
        'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
    })
    _testTilesZXY(server, admin, 'test', meta, params, utilities.PNGHeader)
    # Test that the fractal isn't the same as the non-fractal
    resp = server.request(path='/item/test/tiles/zxy/0/0/0', user=admin,
                          params=params, isJson=False)
    image = utilities.getBody(resp, text=False)
    resp = server.request(path='/item/test/tiles/zxy/0/0/0', user=admin,
                          isJson=False)
    assert utilities.getBody(resp, text=False) != image
    # Test each property with an invalid value
    badParams = {
        'minLevel': 'a',
        'maxLevel': False,
        'tileWidth': (),
        'tileHeight': [],
        'sizeX': {},
        'sizeY': 1.3,
        'encoding': 2,
    }
    for key in badParams:
        err = ('parameter is an incorrect' if key != 'encoding' else
               'Invalid encoding')
        _createTestTiles(server, admin, {key: badParams[key]}, error=err)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromPNG(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)
    # Ask to make this a tile-based item with an missing file ID (there are
    # now two files, so this will now fail).
    resp = boundServer.request(path='/item/%s/tiles' % itemId, method='POST', user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'Missing "fileId"' in resp.json['message']
    # We should be able to delete the tiles
    resp = boundServer.request(path='/item/%s/tiles' % itemId, method='DELETE', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True
    # We should no longer have tile informaton
    resp = boundServer.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']
    # This should work with a PNG with transparency, too.
    file = utilities.uploadTestFile('yb10kx5ktrans.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)
    # We should be able to delete the tiles
    resp = boundServer.request(path='/item/%s/tiles' % itemId, method='DELETE', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True
    # We should no longer have tile information
    resp = boundServer.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesDeleteJob(boundServer, admin, fsAssetstore, girderWorker):
    # Make sure we don't auto-create a largeImage
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore, name='yb10kx5k.tiff')
    itemId = str(file['itemId'])
    resp = boundServer.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']

    # Try to create an image, but delete the job and check that it fails.
    fileId = str(file['_id'])
    result = _postTileViaHttp(boundServer, admin, itemId, fileId, jobAction='delete',
                              data={'countdown': 10, 'fileId': fileId})
    assert result is None
    # If we end the test here, girder_worker may upload a file that gets
    # discarded, but do so in a manner that interfers with cleaning up the test
    # temp directory.  By running other tasks, this is less likely to occur.

    # Creating it again should work
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['levels'] == 7


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromGreyscale(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile('grey10kx5k.tif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromUnicodeName(boundServer, admin, fsAssetstore, girderWorker):
    # Unicode file names shouldn't cause problems when generating tiles.
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    # Our normal testing method doesn't pass through the unicode name
    # properly, so just change it after upload.
    file = File().load(file['_id'], force=True)
    file['name'] = '\u0441\u043b\u0430\u0439\u0434'
    file = File().save(file)
    fileId = str(file['_id'])

    itemId = str(file['itemId'])
    item = Item().load(itemId, force=True)
    item['name'] = 'item \u0441\u043b\u0430\u0439\u0434'
    item = Item().save(item)

    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesWithUnicodeName(server, admin, fsAssetstore):
    # Unicode file names shouldn't cause problems when accessing ptifs.
    # This requires an appropriate version of the python libtiff module.
    name = '\u0441\u043b\u0430\u0439\u0434.ptif'
    origpath = utilities.datastore.fetch('sample_image.ptif')
    altpath = os.path.join(os.path.dirname(origpath), name)
    if os.path.exists(altpath):
        os.unlink(altpath)
    shutil.copy(origpath, altpath)
    file = utilities.uploadFile(altpath, admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 58368
    assert tileMetadata['sizeY'] == 12288


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromBadFiles(boundServer, admin, fsAssetstore, girderWorker):
    # As of vips 8.2.4, alpha and unusual channels are removed upon
    # conversion to a JPEG-compressed tif file.  Originally, we performed a
    # test to show that these files didn't work.  They now do (though if
    # the file has a separated color space, it may not work as expected).

    # Uploading a non-image file should run a job, but not result in tiles
    file = utilities.uploadTestFile('notanimage.txt', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata is None
    resp = boundServer.request(path='/item/%s/tiles' % itemId,
                               method='DELETE', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is False


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testThumbnails(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    # We should already have tile information.  Ask to delete it so we can
    # do other tests
    resp = server.request(path='/item/%s/tiles' % itemId, method='DELETE',
                          user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['deleted'] is True
    # We shouldn't be able to get a thumbnail yet
    resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                          user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']
    # Ask to make this a tile-based item
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST',
                          user=admin, params={'fileId': fileId})
    assert utilities.respStatus(resp) == 200
    # Get metadata to use in our thumbnail tests
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json
    # Now we should be able to get a thumbnail
    resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    defaultLength = len(image)

    # Test width and height using PNGs
    resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                          user=admin, isJson=False,
                          params={'encoding': 'PNG'})
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert max(width, height) == 256
    # We know that we are using an example where the width is greater than
    # the height
    origWidth = int(tileMetadata['sizeX'] *
                    2 ** -(tileMetadata['levels'] - 1))
    origHeight = int(tileMetadata['sizeY'] *
                     2 ** -(tileMetadata['levels'] - 1))
    assert height == int(width * origHeight / origWidth)
    resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                          user=admin, isJson=False,
                          params={'encoding': 'PNG', 'width': 200})
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 200
    assert height == int(width * origHeight / origWidth)

    # Test bad parameters
    badParams = [
        ({'encoding': 'invalid'}, 400, 'Invalid encoding'),
        ({'width': 'invalid'}, 400, 'incorrect type'),
        ({'width': 0}, 400, 'Invalid width or height'),
        ({'width': -5}, 400, 'Invalid width or height'),
        ({'height': 'invalid'}, 400, 'incorrect type'),
        ({'height': 0}, 400, 'Invalid width or height'),
        ({'height': -5}, 400, 'Invalid width or height'),
        ({'jpegQuality': 'invalid'}, 400, 'incorrect type'),
        ({'jpegSubsampling': 'invalid'}, 400, 'incorrect type'),
        ({'fill': 'not a color'}, 400, 'unknown color'),
    ]
    for entry in badParams:
        resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                              user=admin,
                              params=entry[0])
        assert utilities.respStatus(resp) == entry[1]
        assert entry[2] in resp.json['message']

    # Test that we get a thumbnail from a cached file
    resp = server.request(path='/item/%s/tiles/thumbnail' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    assert len(image) == defaultLength

    # We should report some thumbnails
    item = Item().load(itemId, user=admin)
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present > 2

    # Remove the item, and then there should be zero files.
    Item().remove(item)
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 0


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testContentDisposition(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    params = {'encoding': 'PNG', 'width': 200}
    path = '/item/%s/tiles/thumbnail' % itemId
    params['contentDisposition'] = 'inline'
    resp = server.request(path=path, user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    assert resp.headers['Content-Disposition'].startswith('inline')
    assert (
        resp.headers['Content-Disposition'].endswith('.png') or
        'largeImageThumbnail' in resp.headers['Content-Disposition'])
    params['contentDisposition'] = 'attachment'
    resp = server.request(path=path, user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    assert resp.headers['Content-Disposition'].startswith('attachment')
    assert (
        resp.headers['Content-Disposition'].endswith('.png') or
        'largeImageThumbnail' in resp.headers['Content-Disposition'])
    params['contentDisposition'] = 'other'
    resp = server.request(path=path, user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    assert (
        resp.headers.get('Content-Disposition') is None or
        'largeImageThumbnail' in resp.headers['Content-Disposition'])
    del params['contentDisposition']
    resp = server.request(path=path, user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    assert (
        resp.headers.get('Content-Disposition') is None or
        'largeImageThumbnail' in resp.headers['Content-Disposition'])


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testRegions(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    # Get metadata to use in our tests
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json

    # Test bad parameters
    badParams = [
        ({'encoding': 'invalid', 'width': 10}, 400, 'Invalid encoding'),
        ({'width': 'invalid'}, 400, 'incorrect type'),
        ({'width': -5}, 400, 'Invalid output width or height'),
        ({'height': 'invalid'}, 400, 'incorrect type'),
        ({'height': -5}, 400, 'Invalid output width or height'),
        ({'jpegQuality': 'invalid', 'width': 10}, 400, 'incorrect type'),
        ({'jpegSubsampling': 'invalid', 'width': 10}, 400,
         'incorrect type'),
        ({'left': 'invalid'}, 400, 'incorrect type'),
        ({'right': 'invalid'}, 400, 'incorrect type'),
        ({'top': 'invalid'}, 400, 'incorrect type'),
        ({'bottom': 'invalid'}, 400, 'incorrect type'),
        ({'regionWidth': 'invalid'}, 400, 'incorrect type'),
        ({'regionHeight': 'invalid'}, 400, 'incorrect type'),
        ({'units': 'invalid'}, 400, 'Invalid units'),
        ({'unitsWH': 'invalid'}, 400, 'Invalid units'),
    ]
    for entry in badParams:
        resp = server.request(path='/item/%s/tiles/region' % itemId,
                              user=admin,
                              params=entry[0])
        assert utilities.respStatus(resp) == entry[1]
        assert entry[2] in resp.json['message']

    # Get a small region for testing.  Our test file is sparse, so
    # initially get a region where there is full information.
    params = {'regionWidth': 1000, 'regionHeight': 1000,
              'left': 48000, 'top': 3000}
    resp = server.request(path='/item/%s/tiles/region' % itemId,
                          user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    image = origImage = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader

    # We can use base_pixels for width and height and fractions for top and
    # left
    params = {
        'regionWidth': 1000,
        'regionHeight': 1000,
        'left': 48000.0 / tileMetadata['sizeX'],
        'top': 3000.0 / tileMetadata['sizeY'],
        'units': 'fraction',
        'unitsWH': 'base'}
    resp = server.request(path='/item/%s/tiles/region' % itemId,
                          user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image == origImage

    # 0-sized results are allowed
    params = {'regionWidth': 1000, 'regionHeight': 0,
              'left': 48000, 'top': 3000, 'width': 1000, 'height': 1000}
    resp = server.request(path='/item/%s/tiles/region' % itemId,
                          user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert len(image) == 0

    # Test scaling (and a sparse region from our file)
    params = {'regionWidth': 2000, 'regionHeight': 1500,
              'width': 500, 'height': 500, 'encoding': 'PNG'}
    resp = server.request(path='/item/%s/tiles/region' % itemId,
                          user=admin, isJson=False, params=params)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 500
    assert height == 375


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testPixel(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    # Test bad parameters
    badParams = [
        ({'left': 'invalid'}, 400, 'incorrect type'),
        ({'top': 'invalid'}, 400, 'incorrect type'),
        ({'units': 'invalid'}, 400, 'Invalid units'),
    ]
    for entry in badParams:
        resp = server.request(path='/item/%s/tiles/pixel' % itemId,
                              user=admin,
                              params=entry[0])
        assert utilities.respStatus(resp) == entry[1]
        assert entry[2] in resp.json['message']

    # Test a good query
    resp = server.request(
        path='/item/%s/tiles/pixel' % itemId, user=admin,
        params={'left': 48000, 'top': 3000})
    assert utilities.respStatus(resp) == 200
    assert resp.json == {'r': 237, 'g': 248, 'b': 242}

    # If it is outside of the image, we get an empty result
    resp = server.request(
        path='/item/%s/tiles/pixel' % itemId, user=admin,
        params={'left': 148000, 'top': 3000})
    assert utilities.respStatus(resp) == 200
    assert resp.json == {}


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testGetTileSource(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    # We should have access via getGirderTileSource
    source = getGirderTileSource(itemId, user=admin)
    image, mime = source.getThumbnail(encoding='PNG', height=200)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader

    # We can also use a file with getTileSource.  The user is ignored.
    imagePath = utilities.datastore.fetch('sample_image.ptif')
    source = getTileSource(imagePath, user=admin, encoding='PNG')
    image, mime = source.getThumbnail(encoding='JPEG', width=200)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader

    # Test the level0 thumbnail code path
    image, mime = source.getThumbnail(
        encoding='PNG', width=200, height=100, levelZero=True, fill='blue')
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 200
    assert height == 100


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesLoadModelCache(server, admin, fsAssetstore):
    loadmodelcache.invalidateLoadModelCache()
    token = str(Token().createToken(admin)['_id'])
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    # Now the tile request should tell us about the file.  These are
    # specific to our test file
    resp = server.request(path='/item/%s/tiles' % itemId, token=token)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json
    tileMetadata['sparse'] = 5
    _testTilesZXY(server, admin, itemId, tileMetadata, token=token)
    assert next(iter(loadmodelcache.LoadModelCache.values()))['hits'] > 70


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesModelLookupCache(server, user, admin, fsAssetstore):
    User().load = mock.Mock(wraps=User().load)
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    token = str(Token().createToken(user)['_id'])
    lastCount = User().load.call_count
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          token=token, isJson=False)
    assert utilities.respStatus(resp) == 200
    assert User().load.call_count == lastCount + 1
    lastCount = User().load.call_count
    resp = server.request(path='/item/%s/tiles/zxy/1/0/0' % itemId,
                          token=token, isJson=False)
    assert utilities.respStatus(resp) == 200
    assert User().load.call_count == lastCount


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesDZIEndpoints(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    tileMetadata = resp.json
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    xml = utilities.getBody(resp)
    assert 'Width="%d"' % tileMetadata['sizeX'] in xml
    assert 'Overlap="0"' in xml
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, params={
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    xml = utilities.getBody(resp)
    assert 'Width="%d"' % tileMetadata['sizeX'] in xml
    assert 'Overlap="4"' in xml
    resp = server.request(path='/item/%s/tiles/dzi_files/8/0_0.png' % itemId, params={
        'encoding': 'PNG'
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 228
    assert height == 48
    resp = server.request(path='/item/%s/tiles/dzi_files/8/0_0.png' % itemId, params={
        'encoding': 'PNG',
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    assert utilities.getBody(resp, text=False) == image
    # Test bad queries
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, params={
        'encoding': 'TIFF'
    }, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, params={
        'tilesize': 128
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, params={
        'tilesize': 129
    }, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi.dzi' % itemId, params={
        'overlap': -1
    }, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/8/0_0.png' % itemId, params={
        'tilesize': 128
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    resp = server.request(path='/item/%s/tiles/dzi_files/8/0_0.png' % itemId, params={
        'tilesize': 129
    }, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/8/0_0.png' % itemId, params={
        'overlap': -1
    }, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/0/0_0.png' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/20/0_0.png' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/12/0_3.png' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    resp = server.request(path='/item/%s/tiles/dzi_files/12/15_0.png' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    # Test tile sizes
    resp = server.request(path='/item/%s/tiles/dzi_files/12/0_0.png' % itemId, params={
        'encoding': 'PNG',
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 260
    assert height == 260
    resp = server.request(path='/item/%s/tiles/dzi_files/12/0_1.png' % itemId, params={
        'encoding': 'PNG',
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 260
    assert height == 264
    resp = server.request(path='/item/%s/tiles/dzi_files/12/2_1.png' % itemId, params={
        'encoding': 'PNG',
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 264
    assert height == 264
    resp = server.request(path='/item/%s/tiles/dzi_files/12/14_2.png' % itemId, params={
        'encoding': 'PNG',
        'overlap': 4
    }, user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    (width, height) = struct.unpack('!LL', image[16:24])
    assert width == 68
    assert height == 260


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesAfterCopyItem(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)
    item = Item().load(itemId, force=True)
    newItem = Item().copyItem(item, admin)
    assert item['largeImage']['fileId'] != newItem['largeImage']['fileId']
    Item().remove(item)
    _testTilesZXY(boundServer, admin, str(newItem['_id']), tileMetadata)


@pytest.mark.plugin('large_image')
def testTilesAutoSetOption(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore,
        name='sample_image.PTIF')
    itemId = str(file['itemId'])
    # We should already have tile information.
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    # Turn off auto-set and try again
    Setting().set(constants.PluginSettings.LARGE_IMAGE_AUTO_SET, 'false')
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 400
    assert 'No large image file' in resp.json['message']
    # Turn it back on
    Setting().set(constants.PluginSettings.LARGE_IMAGE_AUTO_SET, 'true')
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesAssociatedImages(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    resp = server.request(path='/item/%s/tiles/images' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == ['label', 'macro']
    resp = server.request(path='/item/%s/tiles/images/label' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    resp = server.request(
        path='/item/%s/tiles/images/label' % itemId, user=admin,
        isJson=False, params={'encoding': 'PNG', 'width': 256, 'height': 256})
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    (width, height) = struct.unpack('!LL', image[16:24])
    assert max(width, height) == 256
    resp = server.request(path='/item/%s/tiles/images/label/metadata' % itemId,
                          user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json['sizeX'] == 819
    assert resp.json['sizeY'] == 800
    assert resp.json['format'] == 'JPEG'
    assert resp.json['mode'] == 'RGB'

    # Test missing associated image
    resp = server.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image == b''
    resp = server.request(path='/item/%s/tiles/images/nosuchimage/metadata' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == {}

    # Test with an image that doesn't have associated images
    file = utilities.uploadExternalFile(
        'sample_Easy1.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles' % itemId, method='POST', user=admin)
    assert utilities.respStatus(resp) == 200

    resp = server.request(path='/item/%s/tiles/images' % itemId, user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == []
    resp = server.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image = utilities.getBody(resp, text=False)
    assert image == b''


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesWithFrameNumbers(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample.ome.tif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    # Test that we can get frames via either tiles/zxy or tiles/fzxy and
    # that the frames are different
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    image0 = utilities.getBody(resp, text=False)
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False, params={'frame': 0})
    assert utilities.respStatus(resp) == 200
    assert utilities.getBody(resp, text=False) == image0
    resp = server.request(path='/item/%s/tiles/fzxy/0/0/0/0' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    assert utilities.getBody(resp, text=False) == image0
    resp = server.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                          user=admin, isJson=False, params={'frame': 1})
    assert utilities.respStatus(resp) == 200
    image1 = utilities.getBody(resp, text=False)
    assert image1 != image0
    resp = server.request(path='/item/%s/tiles/fzxy/1/0/0/0' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    assert utilities.getBody(resp, text=False) == image1


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesHistogram(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(
        path='/item/%s/tiles/histogram' % itemId,
        params={'width': 2048, 'height': 2048, 'resample': False})
    assert len(resp.json) == 3
    assert len(resp.json[0]['hist']) == 256
    assert resp.json[1]['samples'] == 2801664
    assert resp.json[1]['hist'][128] == 176


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesInternalMetadata(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile(
        'sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles/internal_metadata' % itemId)
    assert resp.json['tilesource'] == 'tiff'


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromMultipleDotName(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile(
        'yb10kx5k.png', admin, fsAssetstore, name='A name with...dots.png')
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesForcedConversion(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadExternalFile(
        'landcover_sample_1000.tif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    # We should already have tile information.  Ask to delete it so we can
    # force convert it
    boundServer.request(path='/item/%s/tiles' % itemId, method='DELETE', user=admin)
    # Ask to do a forced conversion
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, None, data={'force': True})
    assert tileMetadata['levels'] == 3
    item = Item().load(itemId, force=True)
    assert item['largeImage']['fileId'] != fileId


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesFromWithOptions(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    fileId = str(file['_id'])
    tileMetadata = _postTileViaHttp(boundServer, admin, itemId, fileId, data={'tileSize': 1024})
    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 5


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesConvertLocal(boundServer, admin, fsAssetstore):
    file = utilities.uploadTestFile('grey10kx5k.tif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    headers = {
        'Accept': 'application/json',
        'Girder-Token': str(Token().createToken(admin)['_id'])
    }
    req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles/convert' % (
        boundServer.boundPort, itemId), headers=headers)
    assert req.status_code == 200
    job = req.json()
    while job['status'] not in (JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED):
        time.sleep(0.1)
        job = Job().load(job['_id'], force=True)
    item = Item().findOne({'name': 'grey10kx5k.tiff'}, sort=[('created', SortDir.DESCENDING)])
    itemId = item['_id']
    tileMetadata = ImageItem().getMetadata(item)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testTilesConvertRemote(boundServer, admin, fsAssetstore, girderWorker):
    file = utilities.uploadTestFile('grey10kx5k.tif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    headers = {
        'Accept': 'application/json',
        'Girder-Token': str(Token().createToken(admin)['_id'])
    }
    req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles/convert' % (
        boundServer.boundPort, itemId), headers=headers,
        data={'localJob': 'false'})
    assert req.status_code == 200
    job = req.json()
    while job['status'] not in (JobStatus.SUCCESS, JobStatus.ERROR, JobStatus.CANCELED):
        time.sleep(0.1)
        job = Job().load(job['_id'], force=True)
    item = Item().findOne({'name': 'grey10kx5k.tiff'}, sort=[('created', SortDir.DESCENDING)])
    itemId = item['_id']
    tileMetadata = ImageItem().getMetadata(item)
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 10000
    assert tileMetadata['sizeY'] == 5000
    assert tileMetadata['levels'] == 7
    assert tileMetadata['magnification'] is None
    assert tileMetadata['mm_x'] is None
    assert tileMetadata['mm_y'] is None
    _testTilesZXY(boundServer, admin, itemId, tileMetadata)
