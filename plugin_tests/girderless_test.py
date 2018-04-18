#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
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
##############################################################################

import math
import os
import sys
import unittest

# Ensure that girder can't be imported
sys.modules['girder'] = None


JPEGHeader = b'\xff\xd8\xff'
PNGHeader = b'\x89PNG'


class LargeImageGirderlessTest(unittest.TestCase):
    def _testTilesZXY(self, source, metadata, tileParams={},
                      imgHeader=JPEGHeader):
        """
        Test that the tile source returns images.

        :param source: the tile source class to get tiles from.
        :param metadata: tile information used to determine the expected
                         valid tiles.  If 'sparse' is added to it, tiles
                         are allowed to not exist above that level.
        :param tileParams: optional parameters to send to getTile.
        :param imgHeader: if something other than a JPEG is expected, this is
                          the first few bytes of the expected image.
        """
        from large_image import tilesource
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
                except tilesource.TileSourceException:
                    image = None
                if (image is None and
                        metadata.get('sparse') and z > metadata['sparse']):
                    continue
                self.assertIsNotNone(image)
                self.assertEqual(image[:len(imgHeader)], imgHeader)
            # Check out of range each level
            for (x, y) in ((-1, 0), (maxX + 1, 0), (0, -1), (0, maxY + 1)):
                try:
                    image = source.getTile(x, y, z, **tileParams)
                except tilesource.TileSourceException:
                    image = None
                self.assertIsNone(image)
        # Check negative z level
        try:
            image = source.getTile(0, 0, -1, **tileParams)
        except tilesource.TileSourceException:
            image = None
        self.assertIsNone(image)
        # If we set the minLevel, test one lower than it
        if 'minLevel' in metadata:
            image = source.getTile(0, 0, metadata['minLevel'] - 1,
                                   **tileParams)
            self.assertIsNone(image)
        # Check too large z level
        try:
            image = source.getTile(0, 0, metadata['levels'], **tileParams)
        except tilesource.TileSourceException:
            image = None
        self.assertIsNone(image)

    def testWithoutGirder(self):
        from large_image import tilesource
        # Make sure we are running in a girderless environment
        self.assertIsNone(tilesource.girder)

    def testTilesFromPTIF(self):
        from large_image import tilesource

        canread = tilesource.AvailableTileSources['tifffile'].canRead(
            os.path.join(os.path.dirname(__file__), 'test_files',
                         'yb10kx5k.png'))
        self.assertFalse(canread)
        canread = tilesource.AvailableTileSources['tifffile'].canRead(
            os.path.join(os.environ['LARGE_IMAGE_DATA'],
                         'sample_image.ptif'))
        self.assertTrue(canread)
        source = tilesource.AvailableTileSources['tifffile'](
            os.path.join(os.environ['LARGE_IMAGE_DATA'],
                         'sample_image.ptif'))
        tileMetadata = source.getMetadata()
        self.assertEqual(tileMetadata['tileWidth'], 256)
        self.assertEqual(tileMetadata['tileHeight'], 256)
        self.assertEqual(tileMetadata['sizeX'], 58368)
        self.assertEqual(tileMetadata['sizeY'], 12288)
        self.assertEqual(tileMetadata['levels'], 9)
        tileMetadata['sparse'] = 5
        self._testTilesZXY(source, tileMetadata)

    def testTilesFromSVS(self):
        from large_image import tilesource

        canread = tilesource.AvailableTileSources['svsfile'].canRead(
            os.path.join(os.path.dirname(__file__), 'test_files',
                         'yb10kx5k.png'))
        self.assertFalse(canread)
        canread = tilesource.AvailableTileSources['svsfile'].canRead(
            os.path.join(
                os.environ['LARGE_IMAGE_DATA'],
                'sample_svs_image.TCGA-DU-6399-'
                '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'))
        self.assertTrue(canread)
        source = tilesource.AvailableTileSources['svsfile'](os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'))
        tileMetadata = source.getMetadata()
        self.assertEqual(tileMetadata['tileWidth'], 240)
        self.assertEqual(tileMetadata['tileHeight'], 240)
        self.assertEqual(tileMetadata['sizeX'], 31872)
        self.assertEqual(tileMetadata['sizeY'], 13835)
        self.assertEqual(tileMetadata['levels'], 9)
        self._testTilesZXY(source, tileMetadata)
        # We can get to the tilesource class directly, too.
        params = {'encoding': 'PNG'}
        source = tilesource.SVSFileTileSource(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'), **params)
        self._testTilesZXY(source, tileMetadata, params, PNGHeader)

    def testGetTileSource(self):
        from large_image import getTileSource, tilesource

        try:
            source = getTileSource(os.path.join(
                os.path.dirname(__file__), 'test_files', 'yb10kx5k.png'))
            self.assertTrue(False)
        except tilesource.TileSourceException:
            source = None
        self.assertIsNone(source)

        source = getTileSource(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_svs_image.TCGA-DU-6399-'
            '01A-01-TS1.e8eb65de-d63e-42db-af6f-14fefbbdf7bd.svs'),
            encoding='PNG')
        tileMetadata = source.getMetadata()
        params = {'encoding': 'PNG'}
        self._testTilesZXY(source, tileMetadata, params, PNGHeader)

        source = getTileSource(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        tileMetadata = source.getMetadata()
        tileMetadata['sparse'] = 5
        self._testTilesZXY(source, tileMetadata)

        source = getTileSource('large_image://dummy')
        self.assertEqual(source.getTile(0, 0, 0), '')
        tileMetadata = source.getMetadata()
        self.assertEqual(tileMetadata['tileWidth'], 0)
        self.assertEqual(tileMetadata['tileHeight'], 0)
        self.assertEqual(tileMetadata['sizeX'], 0)
        self.assertEqual(tileMetadata['sizeY'], 0)
        self.assertEqual(tileMetadata['levels'], 0)

        params = {
            'maxLevel': 6,
            'tileWidth': 240,
            'tileHeight': 170,
            'fractal': False,
            'encoding': 'PNG'
        }
        source = getTileSource('large_image://test', **params)
        tileMetadata = source.getMetadata()
        self.assertEqual(tileMetadata['tileWidth'], 240)
        self.assertEqual(tileMetadata['tileHeight'], 170)
        self.assertEqual(tileMetadata['sizeX'], 15360)
        self.assertEqual(tileMetadata['sizeY'], 10880)
        self.assertEqual(tileMetadata['levels'], 7)
        self._testTilesZXY(source, tileMetadata, params, PNGHeader)

    def testSVSNearPowerOfTwo(self):
        from server.tilesource import svs

        self.assertTrue(svs._nearPowerOfTwo(45808, 11456))
        self.assertTrue(svs._nearPowerOfTwo(45808, 11450))
        self.assertFalse(svs._nearPowerOfTwo(45808, 11200))
        self.assertTrue(svs._nearPowerOfTwo(45808, 11400))
        self.assertFalse(svs._nearPowerOfTwo(45808, 11400, 0.005))
        self.assertTrue(svs._nearPowerOfTwo(45808, 11500))
        self.assertFalse(svs._nearPowerOfTwo(45808, 11500, 0.005))
