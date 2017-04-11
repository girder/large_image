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


class LargeImageAnnotationTest(common.LargeImageCommonTest):
    def testAnnotationSchema(self):
        from girder.plugins.large_image.models import annotation
        schema = annotation.AnnotationSchema
        self.assertIsNotNone(schema.annotationSchema)
        self.assertIsNotNone(schema.annotationElementSchema)

    def testAnnotationCreate(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_Easy1.png'))
        itemId = str(file['itemId'])
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'rectangle',
                'center': [10, 20, 0],
                'width': 5,
                'height': 10,
            }]
        }
        result = annotModel.createAnnotation({'_id': itemId}, self.admin, annotation)
        self.assertIn('_id', result)
        annotId = result['_id']
        result = annotModel.load(annotId)
        self.assertEqual(len(result['annotation']['elements']), 1)

    def testSimilarElementStructure(self):
        ses = self.model('annotation', 'large_image')._similarElementStructure
        self.assertTrue(ses('a', 'a'))
        self.assertFalse(ses('a', 'b'))
        self.assertTrue(ses(10, 10))
        self.assertTrue(ses(10, 11))
        self.assertFalse(ses(10, 10.0))
        self.assertTrue(ses({'a': 10}, {'a': 12}))
        self.assertFalse(ses({'a': 10}, {'a': 'b'}))
        self.assertFalse(ses({'a': 10, 'b': 11}, {'a': 10}))
        self.assertFalse(ses({'a': 10, 'b': 11}, {'a': 10, 'c': 11}))
        self.assertTrue(ses({'id': '012345678901234567890123'},
                            {'id': '01234567890123456789ffff'}))
        self.assertFalse(ses({'id': '012345678901234567890123'},
                             {'id': '01234567890123456789----'}))
        self.assertTrue(ses([1, 2, 3, 4], [2, 3, 4, 5]))
        self.assertFalse(ses([1, 2, 3, 4], [2, 3, 4, 5, 6]))
        self.assertFalse(ses([1, 2, 3, 4], [2, 3, 4, 'a']))
        self.assertTrue(ses({'points': [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]}, {'points': [
            [10, 11, 12],
            [13, 14, 15],
            [16, 17, 18],
            [19, 20, 21.1],
        ]}))
        self.assertFalse(ses({'points': [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]}, {'points': [
            [10, 11, 12],
            [13, 14, 15],
            [16, 17, 18],
            [19, 20, 'b'],
        ]}))

    # Add tests for:
    # load
    # remove
    # save
    # updateAnnotaton
    # validate
    # _onItemRemove
