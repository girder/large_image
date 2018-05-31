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

import os
import six

from girder import config
from girder.models.file import File
from girder.models.item import Item
from tests import base

from . import common


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    base.enabledPlugins.append('large_image')
    base.startServer()


def tearDownModule():
    base.stopServer()


class LargeImageWithoutFuseGridFSTest(common.LargeImageCommonTest):
    def setUp(self):
        super(LargeImageWithoutFuseGridFSTest, self).setUp(assetstoreType='gridfs')

    def testGridFSAssetstore(self):
        from girder.plugins.large_image.models.image_item import ImageItem
        from girder.plugins.large_image.tilesource import TileSourceException

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        item = Item().load(itemId, user=self.admin)
        # We should get an error that this isn't a large image
        with six.assertRaisesRegex(self, TileSourceException, 'No large image file in this item'):
            ImageItem().tileSource(item)


class LargeImageWithoutFuseFSTest(common.LargeImageCommonTest):
    def testFilesystemAssetstore(self):
        from girder.plugins.large_image.models.image_item import ImageItem

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        item = Item().load(itemId, user=self.admin)
        file = File().load(item['largeImage']['fileId'], force=True)
        # With a second file, large image would prefer to use the Girder mount,
        # if available
        File().createLinkFile('second', item, 'item', 'http://nourl.com', self.admin)
        source = ImageItem().tileSource(item)
        # The file path should just be the local path
        self.assertEqual(source._getLargeImagePath(), File().getLocalFilePath(file))
