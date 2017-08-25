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
import os
import shutil
import six
import struct

from girder import config
from girder.utility import assetstore_utilities
from tests import base

from . import common


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('large_image')
    base.startServer(False)


def tearDownModule():
    base.stopServer()


class LargeImageTilesTest(common.LargeImageCommonTest):
    def _testEncodings(self, itemId, path='/item/%s/tiles/zxy/0/0/0',
                       params={}, tileMetadata=None, error='raise'):
        """
        Test that different encodings are available for an endpoint.

        :param itemId: an item to test.
        :param path: the main endpoint to test.
        :param params: additional parameters to send with all queries.
        :param tileMetadata: if set, test the full tile tree.
        :param error: 'raise' if an invalid encoding will raise an exception,
            otherwise the expected status code for an invalid encoding.
        """
        params = params.copy()

        # Check that invalid encodings are rejected
        params['encoding'] = 'invalid'
        with six.assertRaisesRegex(self, Exception, 'Invalid encoding'):
            resp = self.request(path='/item/%s/tiles' % itemId,
                                user=self.admin, params=params)
        if error == 'raise':
            with six.assertRaisesRegex(self, Exception, 'Invalid encoding'):
                resp = self.request(path=path % itemId, user=self.admin,
                                    params=params)
        else:
            resp = self.request(path=path % itemId, user=self.admin,
                                params=params)
            self.assertStatus(resp, error)

        # Ask for PNGs
        params['encoding'] = 'PNG'
        if tileMetadata:
            self._testTilesZXY(itemId, tileMetadata, params, common.PNGHeader)

        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)

        # test content disposition
        if not tileMetadata:
            params['contentDisposition'] = 'inline'
            resp = self.request(path=path % itemId, user=self.admin,
                                isJson=False, params=params)
            self.assertStatusOk(resp)
            self.assertTrue(resp.headers['Content-Disposition'].startswith('inline'))
            self.assertTrue(
                resp.headers['Content-Disposition'].endswith('.png') or
                'largeImageThumbnail' in resp.headers['Content-Disposition'])
            params['contentDisposition'] = 'attachment'
            resp = self.request(path=path % itemId, user=self.admin,
                                isJson=False, params=params)
            self.assertStatusOk(resp)
            self.assertTrue(resp.headers['Content-Disposition'].startswith('attachment'))
            self.assertTrue(
                resp.headers['Content-Disposition'].endswith('.png') or
                'largeImageThumbnail' in resp.headers['Content-Disposition'])
            params['contentDisposition'] = 'other'
            resp = self.request(path=path % itemId, user=self.admin,
                                isJson=False, params=params)
            self.assertStatusOk(resp)
            self.assertTrue(
                resp.headers.get('Content-Disposition') is None or
                'largeImageThumbnail' in resp.headers['Content-Disposition'])
            del params['contentDisposition']
            resp = self.request(path=path % itemId, user=self.admin,
                                isJson=False, params=params)
            self.assertStatusOk(resp)
            self.assertTrue(
                resp.headers.get('Content-Disposition') is None or
                'largeImageThumbnail' in resp.headers['Content-Disposition'])

        # Check that JPEG options are honored.
        # JPEG is the default encoding
        del params['encoding']
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        defaultLength = len(image)
        # But it should also work explicitly
        params['encoding'] = 'JPEG'
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        self.assertEqual(image, self.getBody(resp, text=False))

        params['jpegQuality'] = 10
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        self.assertTrue(len(image) < defaultLength)
        del params['jpegQuality']

        params['jpegSubsampling'] = 2
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        self.assertTrue(len(image) < defaultLength)
        del params['jpegSubsampling']

        # Test TIFF output
        params['encoding'] = 'TIFF'
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.TIFFHeader)], common.TIFFHeader)
        defaultLength = len(image)

        params['tiffCompression'] = 'tiff_lzw'
        resp = self.request(path=path % itemId, user=self.admin, isJson=False,
                            params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.TIFFHeader)], common.TIFFHeader)
        self.assertNotEqual(len(image), defaultLength)
        del params['tiffCompression']

    def testTilesFromPTIF(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # We should already have tile information.  Ask to delete it so we can
        # do other tests
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # Now we shouldn't have tile information
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])
        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin)
        self.assertStatus(resp, 404)
        self.assertIn('No large image file', resp.json['message'])
        # Asking to delete the tile information succeeds but does nothing
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], False)
        # Ask to make this a tile-based item with an invalid file ID
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': itemId})
        self.assertStatus(resp, 400)
        self.assertIn('No such file', resp.json['message'])

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
        self.assertEqual(tileMetadata['magnification'], 40)
        self.assertEqual(tileMetadata['mm_x'], 0.00025)
        self.assertEqual(tileMetadata['mm_y'], 0.00025)
        tileMetadata['sparse'] = 5
        self._testTilesZXY(itemId, tileMetadata)

        # Check that we conditionally get JFIF headers
        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertNotEqual(image[:len(common.JFIFHeader)], common.JFIFHeader)

        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'JFIF'})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JFIFHeader)], common.JFIFHeader)

        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False,
                            additionalHeaders=[('User-Agent', 'iPad')])
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JFIFHeader)], common.JFIFHeader)

        resp = self.request(
            path='/item/%s/tiles/zxy/0/0/0' % itemId, user=self.admin,
            isJson=False, additionalHeaders=[(
                'User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X '
                '10_12_3) AppleWebKit/602.4.8 (KHTML, like Gecko) '
                'Version/10.0.3 Safari/602.4.8')])
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JFIFHeader)], common.JFIFHeader)

        resp = self.request(
            path='/item/%s/tiles/zxy/0/0/0' % itemId, user=self.admin,
            isJson=False, additionalHeaders=[(
                'User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 '
                'Safari/537.36')])
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertNotEqual(image[:len(common.JFIFHeader)], common.JFIFHeader)

        # Ask to make this a tile-based item again
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatus(resp, 400)
        self.assertIn('Item already has', resp.json['message'])

        # We should be able to delete the large image information
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)

        # We should no longer have tile information
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])

        # We should be able to re-add it (we are also testing that fileId is
        # optional if there is only one file).
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin)
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)

    def testTilesFromTest(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        items = [{'itemId': str(file['itemId']), 'fileId': str(file['_id'])}]
        # We should already have tile information.  Ask to delete it so we can
        # do other tests
        resp = self.request(path='/item/%s/tiles' % str(file['itemId']),
                            method='DELETE', user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
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
        self.assertIn('The provided file must be in the provided item',
                      resp.json['message'])
        # Now create a test tile with the default options
        params = {'encoding': 'JPEG'}
        meta = self._createTestTiles(params, {
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
        meta = self._createTestTiles(params, {
            'tileWidth': 160, 'tileHeight': 120,
            'sizeX': 5000, 'sizeY': 3000, 'levels': 6
        })
        meta['minLevel'] = 2
        self._testTilesZXY('test', meta, params)
        # Test the fractal tiles with PNG
        params = {'fractal': 'true'}
        meta = self._createTestTiles(params, {
            'tileWidth': 256, 'tileHeight': 256,
            'sizeX': 256 * 2 ** 9, 'sizeY': 256 * 2 ** 9, 'levels': 10
        })
        self._testTilesZXY('test', meta, params, common.PNGHeader)
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
            self._createTestTiles({key: badParams[key]}, error=err)

    def testTilesFromPNG(self):
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'yb10kx5k.png'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 10000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self.assertEqual(tileMetadata['magnification'], None)
        self.assertEqual(tileMetadata['mm_x'], None)
        self.assertEqual(tileMetadata['mm_y'], None)
        self._testTilesZXY(itemId, tileMetadata)
        # Ask to make this a tile-based item with an missing file ID (there are
        # now two files, so this will now fail).
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('Missing "fileId"', resp.json['message'])
        # We should be able to delete the tiles
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # We should no longer have tile informaton
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])
        # This should work with a PNG with transparency, too.
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'yb10kx5ktrans.png'))
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
        # We should no longer have tile information
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])
        # Make sure we don't auto-create a largeImage
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'yb10kx5k.png'),
            'yb10kx5k.tiff')
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])

        # Try to create an image, but delete the job and check that it fails.
        fileId = str(file['_id'])
        result = self._postTileViaHttp(itemId, fileId, jobAction='delete')
        self.assertIsNone(result)

    def testTilesFromGreyscale(self):
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'grey10kx5k.tif'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 10000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self.assertEqual(tileMetadata['magnification'], None)
        self.assertEqual(tileMetadata['mm_x'], None)
        self.assertEqual(tileMetadata['mm_y'], None)
        self._testTilesZXY(itemId, tileMetadata)

    def testTilesFromUnicodeName(self):
        # Unicode file names shouldn't cause problems when generating tiles.
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'yb10kx5k.png'))
        # Our normal testing method doesn't pass through the unicode name
        # properly, so just change it after upload.
        file = self.model('file').load(file['_id'], force=True)
        file['name'] = u'\u0441\u043b\u0430\u0439\u0434'
        file = self.model('file').save(file)
        fileId = str(file['_id'])

        itemId = str(file['itemId'])
        item = self.model('item').load(itemId, force=True)
        item['name'] = u'item \u0441\u043b\u0430\u0439\u0434'
        item = self.model('item').save(item)

        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 10000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self.assertEqual(tileMetadata['magnification'], None)
        self.assertEqual(tileMetadata['mm_x'], None)
        self.assertEqual(tileMetadata['mm_y'], None)
        self._testTilesZXY(itemId, tileMetadata)

    def testTilesWithUnicodeName(self):
        # Unicode file names shouldn't cause problems when accessing ptifs.
        # This requires an appropriate version of the python libtiff module.
        name = u'\u0441\u043b\u0430\u0439\u0434.ptif'
        origpath = os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif')
        altpath = os.path.join(os.environ['LARGE_IMAGE_DATA'], name)
        if os.path.exists(altpath):
            os.unlink(altpath)
        shutil.copy(origpath, altpath)
        item = self.model('item').createItem(
            name=name, creator=self.admin, folder=self.publicFolder,
            reuseExisting=True)
        adapter = assetstore_utilities.getAssetstoreAdapter(self.assetstore)
        adapter.importFile(item, altpath, self.user, name=name)
        resp = self.request(path='/item/%s/tiles' % item['_id'], user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 58368)
        self.assertEqual(tileMetadata['sizeY'], 12288)

    def testTilesFromBadFiles(self):
        # As of vips 8.2.4, alpha and unusual channels are removed upon
        # conversion to a JPEG-compressed tif file.  Originally, we performed a
        # test to show that these files didn't work.  They now do (though if
        # the file has a separated color space, it may not work as expected).

        # Uploading a non-image file should run a job, but not result in tiles
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'notanimage.txt'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        tileMetadata = self._postTileViaHttp(itemId, fileId)
        self.assertEqual(tileMetadata, None)
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], False)

        # Uploading a tif with a bad size shouldn't result in a usable large
        # image
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'zero_gi.tif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])

    def testTilesFromSmallFile(self):
        # Uploading a two-channel luminance-alpha ptif should work
        file = self._uploadFile(os.path.join(
            os.path.dirname(__file__), 'test_files', 'small_la.tiff'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 2)
        self.assertEqual(tileMetadata['tileHeight'], 1)
        self.assertEqual(tileMetadata['sizeX'], 2)
        self.assertEqual(tileMetadata['sizeY'], 1)
        self.assertEqual(tileMetadata['levels'], 1)
        self._testTilesZXY(itemId, tileMetadata)

    def testTilesFromSVS(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # We should already have tile information.  Ask to delete it so we can
        # do other tests
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # Ask to make this a tile-based item
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        # Now the tile request should tell us about the file.  These are
        # specific to our test file
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 240)
        self.assertEqual(tileMetadata['tileHeight'], 240)
        self.assertEqual(tileMetadata['sizeX'], 31872)
        self.assertEqual(tileMetadata['sizeY'], 13835)
        self.assertEqual(tileMetadata['levels'], 9)
        self.assertEqual(tileMetadata['magnification'], 40)
        self.assertEqual(tileMetadata['mm_x'], 0.0002457)
        self.assertEqual(tileMetadata['mm_y'], 0.0002457)
        self._testTilesZXY(itemId, tileMetadata)

        # Ask to make this a tile-based item again
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatus(resp, 400)
        self.assertIn('Item already has', resp.json['message'])

        # Test different encodings
        self._testEncodings(itemId, tileMetadata=tileMetadata)

        # Test that edge options are honored
        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG', 'edge': 'crop'})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 124)
        self.assertEqual(height, 54)
        with six.assertRaisesRegex(self, Exception, 'unknown color specifier'):
            self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                         user=self.admin, isJson=False,
                         params={'edge': 'not_a_color'})
        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG', 'edge': '#DDD'})
        self.assertStatusOk(resp)
        greyImage = self.getBody(resp, text=False)
        self.assertEqual(greyImage[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', greyImage[16:24])
        self.assertEqual(width, 240)
        self.assertEqual(height, 240)
        resp = self.request(path='/item/%s/tiles/zxy/0/0/0' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG', 'edge': 'yellow'})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        self.assertNotEqual(greyImage, image)

    def testTilesFromPowerOf3Tiles(self):
        from girder.plugins.large_image.tilesource import getTileSource
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'G10-3_pelvis_crop-powers-of-3.tif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 128)
        self.assertEqual(tileMetadata['tileHeight'], 128)
        self.assertEqual(tileMetadata['sizeX'], 3000)
        self.assertEqual(tileMetadata['sizeY'], 5000)
        self.assertEqual(tileMetadata['levels'], 7)
        self._testTilesZXY(itemId, tileMetadata)
        source = getTileSource('girder_item://' + itemId, user=self.admin)
        self.assertEqual(len(source._svslevels), 7)
        self.assertTrue(all([level['svslevel'] == 0 for level in source._svslevels]))

    def testTilesFromPTIFJpeg2K(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'huron.image2_jpeg2k.tif'))
        itemId = str(file['itemId'])
        # The tile request should tell us about the file.  These are specific
        # to our test file
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 9158)
        self.assertEqual(tileMetadata['sizeY'], 11273)
        self.assertEqual(tileMetadata['levels'], 7)
        self.assertEqual(tileMetadata['magnification'], 20)
        self._testTilesZXY(itemId, tileMetadata)

    def testTilesFromPIL(self):
        # Allow images bigger than our test
        from girder.plugins.large_image import constants
        self.model('setting').set(
            constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE, 2048)

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_Easy1.png'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # Ask to make this a tile-based item
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        # Now the tile request should tell us about the file.  These are
        # specific to our test file
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        self.assertEqual(tileMetadata['tileWidth'], 1790)
        self.assertEqual(tileMetadata['tileHeight'], 1046)
        self.assertEqual(tileMetadata['sizeX'], 1790)
        self.assertEqual(tileMetadata['sizeY'], 1046)
        self.assertEqual(tileMetadata['levels'], 1)
        self.assertEqual(tileMetadata['magnification'], None)
        self.assertEqual(tileMetadata['mm_x'], None)
        self.assertEqual(tileMetadata['mm_y'], None)
        self._testTilesZXY(itemId, tileMetadata)

        # Ask to make this a tile-based item again
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatus(resp, 400)
        self.assertIn('Item already has', resp.json['message'])

        # Test different encodings
        self._testEncodings(itemId, tileMetadata=tileMetadata)

        # Test with different max size options.
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin,
                            params={'maxSize': 100})
        self.assertStatus(resp, 400)
        self.assertIn('tile size is too large', resp.json['message'])
        resp = self.request(path='/item/%s/tiles' % itemId,
                            user=self.admin,
                            params={'maxSize': 1800})
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin,
                            params={'maxSize': 'not valid'})
        self.assertStatus(resp, 400)
        self.assertIn('maxSize must be', resp.json['message'])
        resp = self.request(
            path='/item/%s/tiles' % itemId, user=self.admin,
            params={'maxSize': json.dumps({'width': 1800, 'height': 1100})})
        self.assertStatusOk(resp)
        resp = self.request(
            path='/item/%s/tiles' % itemId, user=self.admin,
            params={'maxSize': json.dumps({'width': 1100, 'height': 1800})})
        self.assertStatus(resp, 400)
        self.assertIn('tile size is too large', resp.json['message'])

    def testDummyTileSource(self):
        # We can't actually load the dummy source via the endpoints if we have
        # all of the requirements installed, so just check that it exists and
        # will return appropriate values.
        from girder.plugins.large_image.tilesource.dummy import DummyTileSource
        dummy = DummyTileSource()
        self.assertEqual(dummy.getTile(0, 0, 0), '')
        tileMetadata = dummy.getMetadata()
        self.assertEqual(tileMetadata['tileWidth'], 0)
        self.assertEqual(tileMetadata['tileHeight'], 0)
        self.assertEqual(tileMetadata['sizeX'], 0)
        self.assertEqual(tileMetadata['sizeY'], 0)
        self.assertEqual(tileMetadata['levels'], 0)
        self.assertEqual(tileMetadata['magnification'], None)
        self.assertEqual(tileMetadata['mm_x'], None)
        self.assertEqual(tileMetadata['mm_y'], None)

    def testThumbnails(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # We should already have tile information.  Ask to delete it so we can
        # do other tests
        resp = self.request(path='/item/%s/tiles' % itemId, method='DELETE',
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['deleted'], True)
        # We shouldn't be able to get a thumbnail yet
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])
        # Ask to make this a tile-based item
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        # Get metadata to use in our thumbnail tests
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        # Now we should be able to get a thumbnail
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        defaultLength = len(image)

        # Test different encodings
        self._testEncodings(itemId, path='/item/%s/tiles/thumbnail', error=400)

        # Test width and height using PNGs
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG'})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(max(width, height), 256)
        # We know that we are using an example where the width is greater than
        # the height
        origWidth = int(tileMetadata['sizeX'] *
                        2 ** -(tileMetadata['levels'] - 1))
        origHeight = int(tileMetadata['sizeY'] *
                         2 ** -(tileMetadata['levels'] - 1))
        self.assertEqual(height, int(width * origHeight / origWidth))
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG', 'width': 200})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 200)
        self.assertEqual(height, int(width * origHeight / origWidth))
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG', 'height': 200})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(height, 200)
        self.assertEqual(width, int(height * origWidth / origHeight))
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False,
                            params={'encoding': 'PNG',
                                    'width': 180, 'height': 180})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 180)
        self.assertEqual(height, int(width * origHeight / origWidth))

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
        ]
        for entry in badParams:
            resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                                user=self.admin,
                                params=entry[0])
            self.assertStatus(resp, entry[1])
            self.assertIn(entry[2], resp.json['message'])

        # Test that we get a thumbnail from a cached file
        resp = self.request(path='/item/%s/tiles/thumbnail' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        self.assertEqual(len(image), defaultLength)

        # We should report one thumbnail
        item = self.model('item').load(itemId, user=self.admin)
        present, removed = self.model(
            'image_item', 'large_image').removeThumbnailFiles(item, keep=10)
        self.assertGreater(present, 5)

        # Remove the item, and then there should be zero files.
        self.model('item').remove(item)
        present, removed = self.model(
            'image_item', 'large_image').removeThumbnailFiles(item, keep=10)
        self.assertEqual(present, 0)

    def testRegions(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        # Get metadata to use in our tests
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
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
        ]
        for entry in badParams:
            resp = self.request(path='/item/%s/tiles/region' % itemId,
                                user=self.admin,
                                params=entry[0])
            self.assertStatus(resp, entry[1])
            self.assertIn(entry[2], resp.json['message'])

        # Get a small region for testing.  Our test file is sparse, so
        # initially get a region where there is full information.
        params = {'regionWidth': 1000, 'regionHeight': 1000,
                  'left': 48000, 'top': 3000}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = origImage = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)

        # Test different encodings
        self._testEncodings(itemId, path='/item/%s/tiles/region',
                            params=params, error=400)

        # Test using negative offsets
        params['left'] -= tileMetadata['sizeX']
        params['top'] -= tileMetadata['sizeY']
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image, origImage)
        # We should get the same image using right and bottom
        params = {
            'left': params['left'], 'top': params['top'],
            'right': params['left'] + 1000, 'bottom': params['top'] + 1000}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image, origImage)
        params = {
            'regionWidth': 1000, 'regionHeight': 1000,
            'right': params['right'], 'bottom': params['bottom']}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image, origImage)

        # Fractions should get us the same results
        params = {
            'regionWidth': 1000.0 / tileMetadata['sizeX'],
            'regionHeight': 1000.0 / tileMetadata['sizeY'],
            'left': 48000.0 / tileMetadata['sizeX'],
            'top': 3000.0 / tileMetadata['sizeY'],
            'units': 'fraction'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image, origImage)

        # 0-sized results are allowed
        params = {'regionWidth': 1000, 'regionHeight': 0,
                  'left': 48000, 'top': 3000, 'width': 1000, 'height': 1000}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(len(image), 0)

        # Test scaling (and a sparse region from our file)
        params = {'regionWidth': 2000, 'regionHeight': 1500,
                  'width': 500, 'height': 500, 'encoding': 'PNG'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 500)
        self.assertEqual(height, 375)

        # test svs image
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'))
        itemId = str(file['itemId'])
        params = {'regionWidth': 2000, 'regionHeight': 1500,
                  'width': 1000, 'height': 1000, 'encoding': 'PNG'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 1000)
        self.assertEqual(height, 750)

        # test magnification
        params = {'regionWidth': 2000, 'regionHeight': 1500,
                  'magnification': 15, 'encoding': 'PNG'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 750)
        self.assertEqual(height, 562)

        # test magnification with exact requirements
        params = {'regionWidth': 2000, 'regionHeight': 1500,
                  'magnification': 15, 'exact': True, 'encoding': 'PNG'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(len(image), 0)

        params = {'regionWidth': 2000, 'regionHeight': 1500,
                  'magnification': 10, 'exact': True, 'encoding': 'PNG'}
        resp = self.request(path='/item/%s/tiles/region' % itemId,
                            user=self.admin, isJson=False, params=params)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(width, 500)
        self.assertEqual(height, 375)

    def testGetTileSource(self):
        from girder.plugins.large_image.tilesource import getTileSource

        # Upload a PTIF and make it a large_image
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        # We should have access via getTileSource
        source = getTileSource('girder_item://' + itemId, user=self.admin)
        image, mime = source.getThumbnail(encoding='PNG', height=200)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)

        # We can also use a file with getTileSource.  The user is ignored.
        source = getTileSource(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'),
            user=self.admin, encoding='PNG')
        image, mime = source.getThumbnail(encoding='JPEG', width=200)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)

    def testTilesLoadModelCache(self):
        from girder.plugins.large_image import loadmodelcache
        loadmodelcache.invalidateLoadModelCache()
        token = self._genToken(self.admin)
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        # Now the tile request should tell us about the file.  These are
        # specific to our test file
        resp = self.request(path='/item/%s/tiles' % itemId, token=token)
        self.assertStatusOk(resp)
        tileMetadata = resp.json
        tileMetadata['sparse'] = 5
        self._testTilesZXY(itemId, tileMetadata, token=token)
        self.assertGreater(loadmodelcache.LoadModelCache[
            loadmodelcache.LoadModelCache.keys()[0]]['hits'], 70)

    def testTilesAutoSetOption(self):
        from girder.plugins.large_image import constants

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'),
            'sample_image.PTIF')
        itemId = str(file['itemId'])
        # We should already have tile information.
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        # Turn off auto-set and try again
        self.model('setting').set(
            constants.PluginSettings.LARGE_IMAGE_AUTO_SET, 'false')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatus(resp, 400)
        self.assertIn('No large image file', resp.json['message'])
        # Turn it back on
        self.model('setting').set(
            constants.PluginSettings.LARGE_IMAGE_AUTO_SET, 'true')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles' % itemId, user=self.admin)
        self.assertStatusOk(resp)

    def testTilesAssociatedImages(self):
        # Test with a PTIF image
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'),
            'sample_image.PTIF')
        itemId = str(file['itemId'])

        resp = self.request(path='/item/%s/tiles/images' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, ['label', 'macro'])
        resp = self.request(path='/item/%s/tiles/images/label' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        resp = self.request(
            path='/item/%s/tiles/images/label' % itemId, user=self.admin,
            isJson=False, params={'encoding': 'PNG', 'width': 256, 'height': 256})
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.PNGHeader)], common.PNGHeader)
        (width, height) = struct.unpack('!LL', image[16:24])
        self.assertEqual(max(width, height), 256)

        # Test different encodings
        self._testEncodings(itemId, path='/item/%s/tiles/images/label')

        # Test missing associated image
        resp = self.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

        # Test with an SVS image
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles/images' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, ['label', 'macro', 'thumbnail'])
        resp = self.request(path='/item/%s/tiles/images/macro' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        resp = self.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

        # Test with the Huron image
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'huron.image2_jpeg2k.tif'))
        itemId = str(file['itemId'])
        resp = self.request(path='/item/%s/tiles/images' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, ['label', 'macro'])
        resp = self.request(path='/item/%s/tiles/images/macro' % itemId,
                            user=self.admin, isJson=False)
        self.assertStatusOk(resp)
        image = self.getBody(resp, text=False)
        self.assertEqual(image[:len(common.JPEGHeader)], common.JPEGHeader)
        resp = self.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)

        # Test with an image that doesn't have associated images
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_Easy1.png'))
        itemId = str(file['itemId'])
        fileId = str(file['_id'])
        # Ask to make this a tile-based item
        resp = self.request(path='/item/%s/tiles' % itemId, method='POST',
                            user=self.admin, params={'fileId': fileId})
        self.assertStatusOk(resp)
        resp = self.request(path='/item/%s/tiles/images' % itemId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])
        resp = self.request(path='/item/%s/tiles/images/nosuchimage' % itemId,
                            user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, None)
