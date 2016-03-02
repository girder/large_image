#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import json
import math
import os
import requests
import time
from six.moves import range

import girder
from girder import config
from tests import base


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('large_image')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class LargeImageTilesTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)
        admin = {
            'email': 'admin@email.com',
            'login': 'adminlogin',
            'firstName': 'Admin',
            'lastName': 'Last',
            'password': 'adminpassword',
            'admin': True
        }
        self.admin = self.model('user').createUser(**admin)
        folders = self.model('folder').childFolders(
            self.admin, 'user', user=self.admin)
        for folder in folders:
            if folder['name'] == 'Public':
                self.publicFolder = folder
        # Authorize our user for Girder Worker
        resp = self.request(
            '/system/setting', method='PUT', user=self.admin, params={
                'list': json.dumps([{
                    'key': 'worker.broker',
                    'value': 'mongodb://127.0.0.1/girder_worker'
                    }, {
                    'key': 'worker.backend',
                    'value': 'mongodb://127.0.0.1/girder_worker'
                    }])})
        self.assertStatusOk(resp)

    def _uploadFile(self, path):
        """
        Upload the specified path to the admin user's public folder and return
        the resulting item.

        :param path: path to upload.
        :returns: file: the created file.
        """
        name = os.path.basename(path)
        with open(path, 'rb') as file:
            data = file.read()
        resp = self.request(
            path='/file', method='POST', user=self.admin, params={
                'parentType': 'folder',
                'parentId': self.publicFolder['_id'],
                'name': name,
                'size': len(data)
            })
        self.assertStatusOk(resp)
        uploadId = resp.json['_id']

        fields = [('offset', 0), ('uploadId', uploadId)]
        files = [('chunk', name, data)]
        resp = self.multipartRequest(
            path='/file/chunk', fields=fields, files=files, user=self.admin)
        self.assertStatusOk(resp)
        self.assertIn('itemId', resp.json)
        return resp.json

    def _createTestTiles(self, itemId, params={}, info=None, error=None):
        """
        Discard any existing tile set on an item, then create a test tile set
        with some optional parameters.

        :param itemId: the item on which the tiles are created.
        :param params: optional parameters to use for the tiles.
        :param info: if present, the tile information must match all values in
                     this dictionary.
        :param error: if present, expect to get an error from the tile info
                      query and ensure that this string is in the error
                      message.
        :returns: the tile information dictionary.
        """
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': 'test'})
        self.assertStatusOk(resp)
        # We don't actually use the itemId to fetch test tiles
        try:
            resp = self.request(path='/item/test/tiles', user=self.admin,
                                params=params)
            if error:
                self.assertStatus(resp, 400)
                self.assertTrue(error in resp.json['message'])
                return None
        except AssertionError as exc:
            if error:
                self.assertTrue(error in exc.args[0])
                return
            else:
                raise
        self.assertStatusOk(resp)
        infoDict = resp.json
        if info:
            for key in info:
                self.assertEqual(infoDict[key], info[key])
        return infoDict

    def _testTilesZXY(self, itemId, metadata, tileParams={},
                      imgHeader='\xff\xd8\xff'):
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
        # We should get images for all valid levels, but only within the
        # expected range of tiles.
        for z in range(metadata.get('minLevel', 0), metadata['levels']):
            maxX = math.ceil(float(metadata['sizeX']) * 2 ** (
                z - metadata['levels'] + 1) / metadata['tileWidth']) - 1
            maxY = math.ceil(float(metadata['sizeY']) * 2 ** (
                z - metadata['levels'] + 1) / metadata['tileHeight']) - 1
            # Check the four corners on each level
            for (x, y) in ((0, 0), (maxX, 0), (0, maxY), (maxX, maxY)):
                resp = self.request(path='/item/%s/tiles/zxy/%d/%d/%d' % (
                    itemId, z, x, y), user=self.admin, params=tileParams,
                    isJson=False)
                if (resp.output_status[:3] != '200' and
                        metadata.get('sparse') and z > metadata['sparse']):
                    self.assertStatus(resp, 404)
                    continue
                self.assertStatusOk(resp)
                image = self.getBody(resp, text=False)
                self.assertEqual(image[:len(imgHeader)], imgHeader)
            # Check out of range each level
            for (x, y) in ((-1, 0), (maxX + 1, 0), (0, -1), (0, maxY + 1)):
                resp = self.request(path='/item/%s/tiles/zxy/%d/%d/%d' % (
                    itemId, z, x, y), user=self.admin, params=tileParams)
                if x < 0 or y < 0:
                    self.assertStatus(resp, 400)
                    self.assertTrue('must be positive integers' in
                                    resp.json['message'])
                else:
                    self.assertStatus(resp, 404)
                    self.assertTrue('does not exist' in resp.json['message'] or
                                    'outside layer' in resp.json['message'])
        # Check negative z level
        resp = self.request(path='/item/%s/tiles/zxy/-1/0/0' % itemId,
                            user=self.admin, params=tileParams)
        self.assertStatus(resp, 400)
        self.assertTrue('must be positive integers' in resp.json['message'])
        # Check non-integer z level
        resp = self.request(path='/item/%s/tiles/zxy/abc/0/0' % itemId,
                            user=self.admin, params=tileParams)
        self.assertStatus(resp, 400)
        self.assertTrue('must be integers' in resp.json['message'])
        # If we set the minLevel, test one lower than it
        if 'minLevel' in metadata:
            resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
                itemId, metadata['minLevel'] - 1), user=self.admin,
                params=tileParams)
            self.assertStatus(resp, 404)
            self.assertTrue('layer does not exist' in resp.json['message'])
        # Check too large z level
        resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
            itemId, metadata['levels']), user=self.admin, params=tileParams)
        self.assertStatus(resp, 404)
        self.assertTrue('layer does not exist' in resp.json['message'])

    def _postTileViaHttp(self, itemId, fileId):
        """
        When we know we need to process a job, we have to use an actual http
        request rather than the normal simulated request to cherrypy.  This is
        required because cherrypy needs to know how it was reached so that
        girder_worker can reach it when done.

        :param itemId: the id of the item with the file to process.
        :param fileId: the id of the file that should be processed.
        :returns: metadata from the tile if the conversion was successful,
                  False if it converted but didn't result in useable tiles, and
                  None if it failed.
        """
        headers = [('Accept', 'application/json')]
        self._buildHeaders(headers, None, self.admin, None, None, None)
        headers = {header[0]: header[1] for header in headers}
        req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles' % (
            int(os.environ['GIRDER_PORT']), itemId), headers=headers,
            data={'fileId': fileId})
        self.assertEqual(req.status_code, 200)
        starttime = time.time()
        resp = None
        while time.time() - starttime < 30:
            try:
                resp = self.request(path='/item/%s/tiles' % itemId,
                                    user=self.admin)
                self.assertStatusOk(resp)
                break
            except AssertionError as exc:
                if 'File must have at least 1 level' in exc.args[0]:
                    return False
                self.assertTrue('No large image file' in exc.args[0])
            item = self.model('item').load(itemId, user=self.admin)
            job = self.model('job', 'jobs').load(item['largeImageJobId'],
                                                 user=self.admin)
            if job['status'] == girder.plugins.jobs.constants.JobStatus.ERROR:
                return None
            time.sleep(0.1)
        self.assertStatusOk(resp)
        return resp.json

    def testTilesFromPTIF(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # We shouldn't have tile information yet
        try:
            resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
            self.assertTrue(False)
        except AssertionError as exc:
            self.assertTrue('No large image file' in exc.args[0])
        try:
            resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                                user=self.admin)
            self.assertTrue(False)
        except AssertionError as exc:
            self.assertTrue('No large image file' in exc.args[0])
        # Asking to delete the tile information succeeds but does nothing
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], False)
        # Ask to make this a tile-based item with an missing file ID
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertTrue('Missing "fileId"' in resp.json['message'])
        # Ask to make this a tile-based item with an invalid file ID
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': itemId})
        self.assertStatus(resp, 400)
        self.assertTrue('No such file' in resp.json['message'])

        # Ask to make this a tile-based item properly
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        # Now the tile request should tell us about the file.  These are
        # specific to our test file
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 58368)
        self.assertEqual(tileMetadata['sizeY'], 12288)
        self.assertEqual(tileMetadata['levels'], 9)
        tileMetadata['sparse'] = 5
        self._testTilesZXY(itemId, tileMetadata)

        # Ask to make this a tile-based item again
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatus(resp, 400)
        self.assertTrue('Item already has' in resp.json['message'])

        # We should be able to delete the large image information
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)

        # We should no longer have tile informaton
        try:
            resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
            self.assertTrue(False)
        except AssertionError as exc:
            self.assertTrue('No large image file' in exc.args[0])

        # We should be able to re-add it
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)

    def testTilesFromTest(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        items = [{'itemId': str(file['itemId']), 'fileId': str(file['_id'])}]
        # Create a second item
        resp = self.request(path='/item', method='POST', user=self.admin,
                            params={'folderId': self.publicFolder['_id'],
                                    'name': 'test'})
        self.assertStatusOk(resp)
        itemId = str(resp.json['_id'])
        items.append({'itemId': itemId})
        # Check that we can't create a tile set with another item's file
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin,
                            params={'fileId': items[0]['fileId']})
        self.assertStatus(resp, 400)
        self.assertTrue('file on the same item' in resp.json['message'])
        # Now create a test tile with the default options
        params = {'encoding': 'JPEG'}
        meta = self._createTestTiles(itemId, params, {
            'tileWidth': 256, 'tileHeight': 256,
            'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
        })
        self._testTilesZXY('test', meta, params)
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
        meta = self._createTestTiles(itemId, params, {
            'tileWidth': 160, 'tileHeight': 120,
            'sizeX': 5000, 'sizeY': 3000, 'levels': 6
        })
        meta['minLevel'] = 2
        self._testTilesZXY('test', meta, params)
        # Test the fractal tiles with PNG
        params = {'fractal': 'true'}
        meta = self._createTestTiles(itemId, params, {
            'tileWidth': 256, 'tileHeight': 256,
            'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
        })
        self._testTilesZXY('test', meta, params, '\x89PNG')
        # Test that the fractal isn't the same as the non-fractal
        resp = self.request(path='/item/test/tiles/zxy/0/0/0', user=self.admin,
                            params=params, isJson=False)
        image = self.getBody(resp, text=False)
        resp = self.request(path='/item/test/tiles/zxy/0/0/0', user=self.admin,
                            isJson=False)
        self.assertNotEqual(self.getBody(resp, text=False), image)
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
            err = ('parameter is an incorrect' if key is not 'encoding' else
                   'Invalid encoding')
            self._createTestTiles(itemId, {key: badParams[key]}, error=err)

    def testTilesFromPNG(self):
        file = self._uploadFile(os.path.join(os.path.dirname(__file__), 'data',
                                             'yb10kx5k.png'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 10000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self._testTilesZXY(itemId, tileMetadata)
        # We should be able to delete the tiles
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # We should no longer have tile informaton
        try:
            resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
            self.assertTrue(False)
        except AssertionError as exc:
            self.assertTrue('No large image file' in exc.args[0])

        # This should work with a PNG with transparency, too.
        file = self._uploadFile(os.path.join(os.path.dirname(__file__), 'data',
                                             'yb10kx5ktrans.png'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 10000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self._testTilesZXY(itemId, tileMetadata)
        # We should be able to delete the tiles
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # We should no longer have tile informaton
        try:
            resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
            self.assertTrue(False)
        except AssertionError as exc:
            self.assertTrue('No large image file' in exc.args[0])

    def testTilesFromBadFiles(self):
        # Uploading a monochrome file should result in no useful tiles.
        file = self._uploadFile(os.path.join(os.path.dirname(__file__), 'data',
                                             'small.jpg'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata, False)
        # We should be able to delete the conversion
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # Uploading a non-image file should run a job, too.
        file = self._uploadFile(os.path.join(os.path.dirname(__file__), 'data',
                                             'notanimage.txt'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata, None)
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
