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
import subprocess
import tempfile
import time

from girder import config
from girder.models.file import File
from girder.models.item import Item
from tests import base

from . import common


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


def setUpModule():
    # The mount is not done in the module setup, as the test framework clears
    # the test databasei as part of TestCase.setUp , which loses the mount
    # information.
    base.enabledPlugins.append('large_image')
    base.startServer()


def tearDownModule():
    base.stopServer()


class LargeImageGirderMountTest(common.LargeImageCommonTest):
    def setUp(self, *args, **kwargs):
        super(LargeImageGirderMountTest, self).setUp(*args, **kwargs)
        self.mountPath = tempfile.mkdtemp()
        # Start the mount
        subprocess.check_call([
            'girder', 'mount', self.mountPath, '--plugins', 'large_image',
            '-d', os.environ['GIRDER_TEST_DB'], '--quiet'])
        # Wait until it is mounted before proceeding
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            if os.path.exists(os.path.join(self.mountPath, 'user')):
                break
            time.sleep(0.1)

    def tearDown(self):
        super(LargeImageGirderMountTest, self).tearDown()
        # Even if we close all of our references, we aren't guaranteed that
        # all files are released immediately.  At this point, the data.process
        # thread (regardless of whether it is synchronous or asynchronous)
        # still has a reference to the source that was tested with canRead.
        # This seems to only be a testing artifact.  If we do a garbage
        # collection, it will properly release those references and we can
        # unmount immediately.
        import gc
        gc.collect()
        # unmount
        subprocess.check_call(['girder', 'mount', self.mountPath, '-u'])
        # Wait until finished
        endTime = time.time() + 10  # maximum time to wait
        while time.time() < endTime:
            if not os.path.exists(os.path.join(self.mountPath, 'user')):
                break
            time.sleep(0.1)
        os.rmdir(self.mountPath)


class LargeImageWithFuseGridFSTest(LargeImageGirderMountTest):
    def setUp(self):
        super(LargeImageWithFuseGridFSTest, self).setUp(assetstoreType='gridfs')

    def testGridFSAssetstore(self):
        from girder.plugins.large_image.models.image_item import ImageItem

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        item = Item().load(itemId, user=self.admin)
        # We should be able to read the metadata
        source = ImageItem().tileSource(item)
        metadata = source.getMetadata()
        self.assertEqual(metadata['sizeX'], 58368)
        self.assertEqual(metadata['sizeY'], 12288)
        self.assertEqual(metadata['levels'], 9)


class LargeImageWithFuseFSTest(LargeImageGirderMountTest):
    def testFilesystemAssetstore(self):
        from girder.plugins.large_image.models.image_item import ImageItem
        from girder.plugins.large_image.cache_util import cachesClear

        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        itemId = str(file['itemId'])
        item = Item().load(itemId, user=self.admin)
        file = File().load(item['largeImage']['fileId'], force=True)
        # With a second file, large image would prefer to use the Girder mount,
        # if available
        File().createLinkFile('second', item, 'item', 'http://nourl.com', self.admin)
        cachesClear()
        source = ImageItem().tileSource(item)
        # The file path should not be the local path, since we told it we might
        # have adjacent files.
        self.assertNotEqual(source._getLargeImagePath(), File().getLocalFilePath(file))
