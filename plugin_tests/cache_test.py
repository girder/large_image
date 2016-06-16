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
import struct
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


class Fib(object):
    def num(self, k):
        pass


class LargeImageCacheTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)


    def testCacheImport(self):
        try:
            import girder.plugins.large_image.cache
        except ImportError:
            self.fail('Could not import cache module.')

    def testCachePython(self):
        from girder.plugins.large_image.cache import cached
        Fib.num = cached(Fib.num)

        self.assertEquals(Fib().num(4), 5)



    def testCacheMemcached(self):
        pass



