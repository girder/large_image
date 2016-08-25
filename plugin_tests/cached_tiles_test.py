#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import json
import math
import os
import time
from six.moves import range

from girder import config
from tests import base


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port

JPEGHeader = '\xff\xd8\xff'
PNGHeader = '\x89PNG'


def setUpModule():
    curConfig = config.getConfig()
    curConfig.setdefault('large_image', {})
    curConfig['large_image']['cache_backend'] = os.environ.get(
        'LARGE_IMAGE_CACHE_BACKEND')
    base.enabledPlugins.append('large_image')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class LargeImageCachedTilesTest(base.TestCase):
    def _monitorTileCounts(self):
        if hasattr(self, 'tileCounter'):
            return
        from girder.plugins.large_image.tilesource.test import TestTileSource
        originalGetTile = TestTileSource.getTile
        originalWrapKey = TestTileSource.wrapKey
        self.tileCounter = 0
        self.keyPrefix = str(time.time())

        def countGetTile(ttsself, *args, **kwargs):
            # Increment the counter after the call, so that exceptions won't
            # increment it.
            result = originalGetTile(ttsself, *args, **kwargs)
            self.tileCounter += 1
            return result

        def wrapKey(*args, **kwargs):
            # Ensure that this test has unique keys
            return self.keyPrefix + originalWrapKey(*args, **kwargs)

        TestTileSource.getTile = countGetTile
        TestTileSource.wrapKey = wrapKey

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

    def setUp(self):
        self._monitorTileCounts()
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

    def _createTestTiles(self, params={}, info=None, error=None):
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
        try:
            resp = self.request(path='/item/test/tiles', user=self.admin,
                                params=params)
            if error:
                self.assertStatus(resp, 400)
                self.assertIn(error, resp.json['message'])
                return None
        except AssertionError as exc:
            if error:
                self.assertIn(error, exc.args[0])
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
                      imgHeader=JPEGHeader):
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
        self.assertIn('must be positive integers', resp.json['message'])
        # Check non-integer z level
        resp = self.request(path='/item/%s/tiles/zxy/abc/0/0' % itemId,
                            user=self.admin, params=tileParams)
        self.assertStatus(resp, 400)
        self.assertIn('must be integers', resp.json['message'])
        # If we set the minLevel, test one lower than it
        if 'minLevel' in metadata:
            resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
                itemId, metadata['minLevel'] - 1), user=self.admin,
                params=tileParams)
            self.assertStatus(resp, 404)
            self.assertIn('layer does not exist', resp.json['message'])
        # Check too large z level
        resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
            itemId, metadata['levels']), user=self.admin, params=tileParams)
        self.assertStatus(resp, 404)
        self.assertIn('layer does not exist', resp.json['message'])

    def testTilesFromTest(self):
        # Create a test tile with the default options
        params = {'encoding': 'JPEG'}
        meta = self._createTestTiles(params, {
            'tileWidth': 256, 'tileHeight': 256,
            'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
        })
        self._testTilesZXY('test', meta, params)
        # We should have generated tiles
        self.assertGreater(self.tileCounter, 0)
        counter1 = self.tileCounter
        # Running a second time should take entirely from cache
        self._testTilesZXY('test', meta, params)
        self.assertEqual(self.tileCounter, counter1)

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
        meta = self._createTestTiles(params, {
            'tileWidth': 160, 'tileHeight': 120,
            'sizeX': 5000, 'sizeY': 3000, 'levels': 6
        })
        meta['minLevel'] = 2
        self._testTilesZXY('test', meta, params)
        # We should have generated tiles
        self.assertGreater(self.tileCounter, counter1)
        counter2 = self.tileCounter
        # Running a second time should take entirely from cache
        self._testTilesZXY('test', meta, params)
        self.assertEqual(self.tileCounter, counter2)

        # Test the fractal tiles with PNG
        params = {'fractal': 'true'}
        meta = self._createTestTiles(params, {
            'tileWidth': 256, 'tileHeight': 256,
            'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
        })
        self._testTilesZXY('test', meta, params, PNGHeader)
        # We should have generated tiles
        self.assertGreater(self.tileCounter, counter2)
        counter3 = self.tileCounter
        # Running a second time should take entirely from cache
        self._testTilesZXY('test', meta, params, PNGHeader)
        self.assertEqual(self.tileCounter, counter3)

    def testLargeRegion(self):
        # Create a test tile with the default options
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_jp2k_33003_TCGA-CV-7242-'
            '11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs'))
        itemId = str(file['itemId'])
        # Get metadata to use in our tests
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json

        params = {
            'regionWidth': min(10000, tileMetadata['sizeX']),
            'regionHeight': min(10000, tileMetadata['sizeY']),
            'width': 480,
            'height': 480,
            'encoding': 'PNG'
        }
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)


class MemcachedCache(LargeImageCachedTilesTest):
    pass


class PythonCache(LargeImageCachedTilesTest):
    pass
