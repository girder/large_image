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


import os

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


class Fib(object):
    def num(self, k):
        if k > 2:

            return self.num(k - 1) + self.num(k - 2)
        else:
            return 1


class LargeImageCacheTest(base.TestCase):
    def setUp(self):
        base.TestCase.setUp(self)

    def testCacheImport(self):
        try:

            reload_module(girder.plugins.large_image.cache_util.memcache)
        except ImportError:
            self.fail('Could not import memcache module.')
        try:
            import cachetools  # noqa
        except ImportError:
            self.fail('Could not import cachtools')

        try:
            reload_module(girder.plugins.large_image.cache_util.cache)
        except ImportError:
            self.fail("Could not import the cache module")
        try:
            import pylibmc  # noqa
        except ImportError:
            self.fail("Could not import pylibmc")

    def testCache(self):
        self._testCacheMemcached()
        self._testLRUCacheTools()

    def _testDecorator(self, specific_cache):
        from server.cache_util import cached, strhash
        temp = Fib()
        temp.num = cached(cache=specific_cache,
                          key=strhash)(temp.num)

        self.assertEquals(temp.num(100), 354224848179261915075)

    def _testLRUCacheTools(self):
        from server.cache_util import Cache

        self._testDecorator(Cache(1000))

    def _testCacheMemcached(self):
        from server.cache_util import MemCache

        self._testDecorator(MemCache())

    def testcheckCacheMemcached(self):

        from server.cache_util import MemCache
        # go though and check if all 100 fib numbers are in cache
        # it is stored in cache as ('fib', #)
        self._testCacheMemcached()

        cache = MemCache()
        try:
            val = cache['(2,)']
            self.assertEquals(val, 1)
            val = cache['(100,)']
            self.assertEquals(val, 354224848179261915075)
        except KeyError:
            self.fail('could not retrieve recent fibonacci number ')
