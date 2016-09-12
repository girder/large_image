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

import numpy
import os
import PIL.Image

from girder import config
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


class LargeImageSourcesTest(common.LargeImageCommonTest):
    def testMagnification(self):
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_jp2k_33003_TCGA-CV-7242-'
            '11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs'))
        itemId = str(file['itemId'])
        item = self.model('item').load(itemId, user=self.admin)
        source = self.model('image_item', 'large_image').tileSource(item)
        mag = source.getNativeMagnification()
        self.assertEqual(mag['magnification'], 40.0)
        self.assertEqual(mag['mm_x'], 0.000252)
        self.assertEqual(mag['mm_y'], 0.000252)
        mag = source.getMagnificationForLevel()
        self.assertEqual(mag['magnification'], 40.0)
        self.assertEqual(mag['mm_x'], 0.000252)
        self.assertEqual(mag['mm_y'], 0.000252)
        self.assertEqual(mag['level'], 7)
        mag = source.getMagnificationForLevel(0)
        self.assertEqual(mag['magnification'], 0.3125)
        self.assertEqual(mag['mm_x'], 0.032256)
        self.assertEqual(mag['mm_y'], 0.032256)
        self.assertEqual(mag['level'], 0)
        self.assertEqual(source.getLevelForMagnification(), 7)
        self.assertEqual(source.getLevelForMagnification(exact=True), 7)
        self.assertEqual(source.getLevelForMagnification(40), 7)
        self.assertEqual(source.getLevelForMagnification(20), 6)
        self.assertEqual(source.getLevelForMagnification(0.3125), 0)
        self.assertEqual(source.getLevelForMagnification(15), 6)
        self.assertEqual(source.getLevelForMagnification(25), 6)
        self.assertEqual(source.getLevelForMagnification(
            15, rounding='ceil'), 6)
        self.assertEqual(source.getLevelForMagnification(
            25, rounding='ceil'), 7)
        self.assertEqual(source.getLevelForMagnification(
            15, rounding=False), 5.585)
        self.assertEqual(source.getLevelForMagnification(
            25, rounding=False), 6.3219)
        self.assertEqual(source.getLevelForMagnification(
            45, rounding=False), 7)
        self.assertEqual(source.getLevelForMagnification(
            15, rounding=None), 5.585)
        self.assertEqual(source.getLevelForMagnification(
            25, rounding=None), 6.3219)
        self.assertEqual(source.getLevelForMagnification(
            45, rounding=None), 7.1699)
        self.assertEqual(source.getLevelForMagnification(mm_x=0.0005), 6)
        self.assertEqual(source.getLevelForMagnification(
            mm_x=0.0005, mm_y=0.002), 5)
        self.assertEqual(source.getLevelForMagnification(
            mm_x=0.0005, exact=True), None)
        self.assertEqual(source.getLevelForMagnification(
            mm_x=0.000504, exact=True), 6)
        self.assertEqual(source.getLevelForMagnification(80), 7)
        self.assertEqual(source.getLevelForMagnification(80, exact=True), None)
        self.assertEqual(source.getLevelForMagnification(0.1), 0)

    def testTileIterator(self):
        from girder.plugins.large_image import tilesource

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_jp2k_33003_TCGA-CV-7242-'
            '11A-01-TS1.1838afb1-9eee-4a70-9ae3-50e3ab45e242.svs'))
        itemId = str(file['itemId'])
        item = self.model('item').load(itemId, user=self.admin)
        source = self.model('image_item', 'large_image').tileSource(item)
        tileCount = 0
        visited = {}
        for tile in source.tileIterator(output={'magnification': 5}):
            visited.setdefault(tile['level_x'], {})[tile['level_y']] = True
            tileCount += 1
            self.assertEqual(tile['tile'].size, (tile['width'], tile['height']))
            self.assertEqual(tile['width'], 256 if tile['level_x'] < 11 else 61)
            self.assertEqual(tile['height'], 256 if tile['level_y'] < 11 else 79)
        self.assertEqual(tileCount, 144)
        self.assertEqual(len(visited), 12)
        self.assertEqual(len(visited[0]), 12)
        # Check with a non-native magnfication with exact=True
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 4, 'exact': True}):
            tileCount += 1
        self.assertEqual(tileCount, 0)
        # Check with a non-native (but factor of 2) magnfication with exact=True
        for tile in source.tileIterator(
                output={'magnification': 2.5, 'exact': True}):
            tileCount += 1
        self.assertEqual(tileCount, 0)
        # Check with a native magnfication with exact=True
        for tile in source.tileIterator(
                output={'magnification': 5, 'exact': True}):
            tileCount += 1
        self.assertEqual(tileCount, 144)
        # Check with a non-native magnfication without resampling
        tileCount = 0
        for tile in source.tileIterator(output={'magnification': 2}):
            tileCount += 1
            self.assertEqual(tile['tile'].size, (tile['width'], tile['height']))
            self.assertEqual(tile['width'], 256 if tile['level_x'] < 11 else 61)
            self.assertEqual(tile['height'], 256 if tile['level_y'] < 11 else 79)
        self.assertEqual(tileCount, 144)
        # Check with a non-native magnfication with resampling
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 2}, resample=True):
            tileCount += 1
            self.assertEqual(tile['tile'].size, (tile['width'], tile['height']))
            self.assertEqual(tile['width'], 102 if tile['level_x'] < 11 else 24)
            self.assertEqual(tile['height'], 102 if tile['level_y'] < 11 else 31)
        self.assertEqual(tileCount, 144)

        # Ask for numpy array as results
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 5},
                format=tilesource.TILE_FORMAT_NUMPY):
            tileCount += 1
            self.assertTrue(isinstance(tile['tile'], numpy.ndarray))
            self.assertEqual(tile['tile'].shape, (
                256 if tile['level_y'] < 11 else 79,
                256 if tile['level_x'] < 11 else 61,
                4))
            self.assertEqual(tile['tile'].dtype, numpy.dtype('uint8'))
        self.assertEqual(tileCount, 144)
        # Ask for either PIL or IMAGE data, we should get PIL data
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 5},
                format=(tilesource.TILE_FORMAT_PIL,
                        tilesource.TILE_FORMAT_IMAGE),
                encoding='JPEG'):
            tileCount += 1
            self.assertTrue(isinstance(tile['tile'], PIL.Image.Image))
        self.assertEqual(tileCount, 144)
        # Ask for PNGs
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 5},
                format=tilesource.TILE_FORMAT_IMAGE,
                encoding='PNG'):
            tileCount += 1
            self.assertFalse(isinstance(tile['tile'], PIL.Image.Image))
            self.assertEqual(tile['tile'][:len(common.PNGHeader)],
                             common.PNGHeader)
        self.assertEqual(tileCount, 144)

        # Use a ptif to test getting tiles as images
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        item = self.model('item').load(itemId, user=self.admin)
        source = self.model('image_item', 'large_image').tileSource(item)
        # Ask for either PIL or IMAGE data, we should get image data
        tileCount = 0
        jpegTileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 2.5},
                format=(tilesource.TILE_FORMAT_PIL,
                        tilesource.TILE_FORMAT_IMAGE),
                encoding='JPEG'):
            tileCount += 1
            if not isinstance(tile['tile'], PIL.Image.Image):
                self.assertEqual(tile['tile'][:len(common.JPEGHeader)],
                                 common.JPEGHeader)
                jpegTileCount += 1
        self.assertEqual(tileCount, 45)
        self.assertGreater(jpegTileCount, 0)
        # Ask for PNGs
        tileCount = 0
        for tile in source.tileIterator(
                output={'magnification': 2.5},
                format=tilesource.TILE_FORMAT_IMAGE,
                encoding='PNG'):
            tileCount += 1
            self.assertEqual(tile['tile'][:len(common.PNGHeader)],
                             common.PNGHeader)
        self.assertEqual(tileCount, 45)
