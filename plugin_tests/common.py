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
import requests
import time
from six.moves import range

from tests import base

from girder.constants import SortDir


JFIFHeader = b'\xff\xd8\xff\xe0\x00\x10JFIF'
JPEGHeader = b'\xff\xd8\xff'
PNGHeader = b'\x89PNG'
TIFFHeader = b'II\x2a\x00'


class LargeImageCommonTest(base.TestCase):
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
        user = {
            'email': 'user@email.com',
            'login': 'userlogin',
            'firstName': 'Common',
            'lastName': 'User',
            'password': 'userpassword'
        }
        self.user = self.model('user').createUser(**user)
        folders = self.model('folder').childFolders(
            self.admin, 'user', user=self.admin)
        for folder in folders:
            if folder['name'] == 'Public':
                self.publicFolder = folder
            if folder['name'] == 'Private':
                self.privateFolder = folder
        # Authorize our user for Girder Worker
        resp = self.request(
            '/system/setting', method='PUT', user=self.admin, params={
                'list': json.dumps([{
                    'key': 'worker.broker',
                    'value': 'amqp://guest@127.0.0.1/'
                    }, {
                    'key': 'worker.backend',
                    'value': 'amqp://guest@127.0.0.1/'
                    }])})
        self.assertStatusOk(resp)

    def _uploadFile(self, path, name=None):
        """
        Upload the specified path to the admin user's public folder and return
        the resulting item.

        :param path: path to upload.
        :param name: optional name for the file.
        :returns: file: the created file.
        """
        if not name:
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
                      imgHeader=JPEGHeader, token=None):
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
        if token:
            kwargs = {'token': token}
        else:
            kwargs = {'user': self.admin}
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
                    itemId, z, x, y), params=tileParams, isJson=False,
                    **kwargs)
                if (resp.output_status[:3] != b'200' and
                        metadata.get('sparse') and z > metadata['sparse']):
                    self.assertStatus(resp, 404)
                    continue
                self.assertStatusOk(resp)
                image = self.getBody(resp, text=False)
                self.assertEqual(image[:len(imgHeader)], imgHeader)
            # Check out of range each level
            for (x, y) in ((-1, 0), (maxX + 1, 0), (0, -1), (0, maxY + 1)):
                resp = self.request(path='/item/%s/tiles/zxy/%d/%d/%d' % (
                    itemId, z, x, y), params=tileParams, **kwargs)
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
                            params=tileParams, **kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('must be positive integers', resp.json['message'])
        # Check non-integer z level
        resp = self.request(path='/item/%s/tiles/zxy/abc/0/0' % itemId,
                            params=tileParams, **kwargs)
        self.assertStatus(resp, 400)
        self.assertIn('must be integers', resp.json['message'])
        # If we set the minLevel, test one lower than it
        if 'minLevel' in metadata:
            resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
                itemId, metadata['minLevel'] - 1), params=tileParams, **kwargs)
            self.assertStatus(resp, 404)
            self.assertIn('layer does not exist', resp.json['message'])
        # Check too large z level
        resp = self.request(path='/item/%s/tiles/zxy/%d/0/0' % (
            itemId, metadata['levels']), params=tileParams, **kwargs)
        self.assertStatus(resp, 404)
        self.assertIn('layer does not exist', resp.json['message'])

    def _postTileViaHttp(self, itemId, fileId, jobAction=None):
        """
        When we know we need to process a job, we have to use an actual http
        request rather than the normal simulated request to cherrypy.  This is
        required because cherrypy needs to know how it was reached so that
        girder_worker can reach it when done.

        :param itemId: the id of the item with the file to process.
        :param fileId: the id of the file that should be processed.
        :param jobAction: if 'delete', delete the job immediately.
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
        # If we ask to create the item again right away, we should be told that
        # either there is already a job running or the item has already been
        # added
        req = requests.post('http://127.0.0.1:%d/api/v1/item/%s/tiles' % (
            int(os.environ['GIRDER_PORT']), itemId), headers=headers,
            data={'fileId': fileId})
        self.assertEqual(req.status_code, 400)
        self.assertTrue('Item already has' in req.json()['message'] or
                        'Item is scheduled' in req.json()['message'])

        if jobAction == 'delete':
            jobModel = self.model('job', 'jobs')
            jobModel.remove(jobModel.find(
                {}, sort=[('_id', SortDir.DESCENDING)])[0])

        starttime = time.time()
        resp = None
        while time.time() - starttime < 30:
            try:
                resp = self.request(path='/item/%s/tiles' % itemId,
                                    user=self.admin)
                self.assertStatusOk(resp)
                break
            except AssertionError as exc:
                if 'didn\'t meet requirements' in exc.args[0]:
                    return False
                if 'No large image file' in exc.args[0]:
                    return None
                self.assertIn('is still pending creation', exc.args[0])
            time.sleep(0.1)
        self.assertStatusOk(resp)
        return resp.json
