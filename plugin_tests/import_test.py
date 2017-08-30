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

import os
import sys
from six.moves import reload_module

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
    def testImportErrors(self):
        # Temporarily remove third-party dependencies
        for key in ['openslide', 'PIL', 'libtiff']:
            sys.modules[key] = None

        # Force a reimport of modules that require third-party libraries
        try:
            reload_module(girder.plugins.large_image.tilesource.test)
        except ImportError as exc:
            self.assertIn('PIL', exc.args[0])
        else:
            self.fail()
        try:
            reload_module(girder.plugins.large_image.tilesource.tiff_reader)
        except ImportError as exc:
            self.assertIn('libtiff', exc.args[0])
        else:
            self.fail()
        try:
            reload_module(girder.plugins.large_image.tilesource.svs)
        except ImportError as exc:
            self.assertIn('openslide', exc.args[0])
        else:
            self.fail()

        # Importing tilesouce, when tilesource.test is unavailable, should not
        # be fatal
        sys.modules['girder.plugins.large_image.tilesource.test'] = None
        reload_module(girder.plugins.large_image.tilesource)
