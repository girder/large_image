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
            import cachetools  # noqa
        except ImportError:
            self.fail('Could not import cachtools.')

        try:
            import pylibmc  # noqa
        except ImportError:
            self.fail('Could not import pylibmc.')

    def testConfigFunctions(self):
        from girder.plugins.large_image.cache_util import getConfig, setConfig
        self.assertEquals(getConfig('cache_backend'), None)
        self.assertEquals(getConfig('cache_backend', 'python'), 'python')
        self.assertTrue(isinstance(getConfig(), dict))
        setConfig('cache_backend', 'python')
        self.assertEquals(getConfig('cache_backend'), 'python')

    def _testDecorator(self, specific_cache, maxNum=100):
        from girder.plugins.large_image.cache_util import cached, strhash
        temp = Fib()
        temp.num = cached(cache=specific_cache,
                          key=strhash)(temp.num)
        temp.num(maxNum)
        if maxNum >= 3:
            self.assertEquals(temp.num(3), 2)
        if maxNum >= 100:
            self.assertEquals(temp.num(100), 354224848179261915075)

    def testLRUCacheTools(self):
        from girder.plugins.large_image.cache_util import Cache

        self._testDecorator(Cache(1000))

    def testCacheMemcached(self):
        from girder.plugins.large_image.cache_util import MemCache

        self._testDecorator(MemCache())

    def testCheckCacheMemcached(self):
        from girder.plugins.large_image.cache_util import MemCache
        # go though and check if all 100 fib numbers are in cache
        # it is stored in cache as ('fib', #)
        cache = MemCache()

        self._testDecorator(cache)

        try:
            val = cache['(2,)']
            self.assertEquals(val, 1)
            val = cache['(100,)']
            self.assertEquals(val, 354224848179261915075)
        except KeyError:
            self.fail('Could not retrieve recent fibonacci number.')

    def testBadMemcachedUrl(self):
        from girder.plugins.large_image.cache_util import MemCache
        # go though and check if all 100 fib numbers are in cache
        # it is stored in cache as ('fib', #)
        cache = MemCache(url=['192.0.2.254', '192.0.2.253'])

        self._testDecorator(cache, 3)
        with six.assertRaisesRegex(self, KeyError, '(2,)'):
            cache['(2,)']
