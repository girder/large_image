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

import math
import os
import random
import six
from six.moves import range

from girder import config
from girder.constants import AccessType
from tests import base

from . import common


# boiler plate to start and stop the server

os.environ['GIRDER_PORT'] = os.environ.get('GIRDER_TEST_PORT', '20200')
config.loadConfig()  # Must reload config to pickup correct port


sampleAnnotationEmpty = {
    'name': 'sample0',
    'elements': []}
sampleAnnotation = {
    'name': 'sample',
    'elements': [{
        'type': 'rectangle',
        'center': [20.0, 25.0, 0],
        'width': 14.0,
        'height': 15.0,
    }]
}


def makeLargeSampleAnnotation():
    """
    Generate a large annotation for testing.

    :returns: a large annotation
    """
    elements = []
    annotation = {'name': 'sample_large', 'elements': elements}
    skip = 0
    random.seed(0)
    for z in range(16):
        for y in range(0, 10000, 32 * 2**z):
            for x in range(0, 10000, 32 * 2**z):
                if not skip % 17:
                    elements.append({
                        'type': 'rectangle',
                        'center': [x + random.random(), y + random.random(), 0],
                        'width': (8 + random.random()) * 2 ** z,
                        'height': (8 + random.random()) * 2 ** z,
                    })
                skip += 1
    return annotation


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

    def testLoad(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        with six.assertRaisesRegex(self, Exception, 'Invalid ObjectId'):
            annotModel.load('nosuchid')
        self.assertIsNone(annotModel.load('012345678901234567890123'))
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        loaded = annotModel.load(annot['_id'])
        self.assertEqual(loaded['annotation']['elements'][0]['center'],
                         annot['annotation']['elements'][0]['center'])

        annot0 = annotModel.createAnnotation(item, self.admin,
                                             sampleAnnotationEmpty)
        loaded = annotModel.load(annot0['_id'])
        self.assertEqual(len(loaded['annotation']['elements']), 0)

    def testSave(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        annot = annotModel.load(annot['_id'], region={'sort': 'size'})
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        saved = annotModel.save(annot)
        loaded = annotModel.load(annot['_id'], region={'sort': 'size'})
        self.assertEqual(len(saved['annotation']['elements']), 4)
        self.assertEqual(len(loaded['annotation']['elements']), 4)
        self.assertEqual(saved['annotation']['elements'][0]['type'], 'rectangle')
        self.assertEqual(loaded['annotation']['elements'][0]['type'], 'point')
        self.assertEqual(saved['annotation']['elements'][-1]['type'], 'point')
        self.assertEqual(loaded['annotation']['elements'][-1]['type'], 'rectangle')

    def testRemove(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        self.assertIsNotNone(annotModel.load(annot['_id']))
        result = annotModel.remove(annot)
        self.assertEqual(result.deleted_count, 1)
        self.assertIsNone(annotModel.load(annot['_id']))

    #  Add tests for:
    # updateAnnotaton
    # validate
    # _onItemRemove


class LargeImageAnnotationElementTest(common.LargeImageCommonTest):
    def testInitialize(self):
        # initialize should be called as we fetch the model
        elemModel = self.model('annotationelement', 'large_image')
        self.assertEqual(elemModel.name, 'annotationelement')

    def testGetNextVersionValue(self):
        elemModel = self.model('annotationelement', 'large_image')
        val1 = elemModel.getNextVersionValue()
        val2 = elemModel.getNextVersionValue()
        self.assertGreater(val2, val1)
        elemModel.versionId = None
        val3 = elemModel.getNextVersionValue()
        self.assertGreater(val3, val2)

    def testBoundingBox(self):
        elemModel = self.model('annotationelement', 'large_image')
        bbox = elemModel._boundingBox({'points': [[1, -2, 3], [-4, 5, -6], [7, -8, 9]]})
        self.assertEqual(bbox, {
            'lowx': -4, 'lowy': -8, 'lowz': -6,
            'highx': 7, 'highy': 5, 'highz': 9,
            'details': 3,
            'size': ((7+4)**2 + (8+5)**2)**0.5})
        bbox = elemModel._boundingBox({'center': [1, -2, 3]})
        self.assertEqual(bbox, {
            'lowx': 0.5, 'lowy': -2.5, 'lowz': 3,
            'highx': 1.5, 'highy': -1.5, 'highz': 3,
            'details': 1,
            'size': 2**0.5})
        bbox = elemModel._boundingBox({'center': [1, -2, 3], 'radius': 4})
        self.assertEqual(bbox, {
            'lowx': -3, 'lowy': -6, 'lowz': 3,
            'highx': 5, 'highy': 2, 'highz': 3,
            'details': 4,
            'size': 8 * 2**0.5})
        bbox = elemModel._boundingBox({'center': [1, -2, 3], 'width': 2, 'height': 4})
        self.assertEqual(bbox, {
            'lowx': 0, 'lowy': -4, 'lowz': 3,
            'highx': 2, 'highy': 0, 'highz': 3,
            'details': 4,
            'size': (2**2 + 4**2)**0.5})
        bbox = elemModel._boundingBox({
            'center': [1, -2, 3],
            'width': 2, 'height': 4,
            'rotation': math.pi * 0.25})
        self.assertAlmostEqual(bbox['size'], 4, places=4)

    def testGetElements(self):
        annotModel = self.model('annotation', 'large_image')
        elemModel = self.model('annotationelement', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        largeSample = makeLargeSampleAnnotation()
        # Use a copy of largeSample so we don't just have a referecne to it
        annot = annotModel.createAnnotation(item, self.admin, largeSample.copy())
        # Clear existing element data, the get elements
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot)
        self.assertIn('_elementQuery', annot)
        self.assertEqual(len(annot['annotation']['elements']),
                         len(largeSample['elements']))  # 7707
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {'limit': 100})
        self.assertIn('_elementQuery', annot)
        self.assertEqual(annot['_elementQuery']['count'], len(largeSample['elements']))
        self.assertEqual(annot['_elementQuery']['returned'], 100)
        self.assertEqual(len(annot['annotation']['elements']), 100)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500})
        self.assertEqual(len(annot['annotation']['elements']), 157)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500,
            'minimumSize': 16})
        self.assertEqual(len(annot['annotation']['elements']), 39)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {'maxDetails': 300})
        self.assertEqual(len(annot['annotation']['elements']), 75)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': -1})
        elements = annot['annotation']['elements']
        self.assertGreater(elements[0]['width'] * elements[0]['height'],
                           elements[-1]['width'] * elements[-1]['height'])
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        elemModel.getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': 1})
        elements = annot['annotation']['elements']
        elements = annot['annotation']['elements']
        self.assertLess(elements[0]['width'] * elements[0]['height'],
                        elements[-1]['width'] * elements[-1]['height'])

    def testRemoveWithQuery(self):
        annotModel = self.model('annotation', 'large_image')
        elemModel = self.model('annotationelement', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        self.assertEqual(len(annotModel.load(annot['_id'])['annotation']['elements']), 1)
        elemModel.removeWithQuery({'annotationId': annot['_id']})
        self.assertEqual(len(annotModel.load(annot['_id'])['annotation']['elements']), 0)

    def testRemoveElements(self):
        annotModel = self.model('annotation', 'large_image')
        elemModel = self.model('annotationelement', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        self.assertEqual(len(annotModel.load(annot['_id'])['annotation']['elements']), 1)
        elemModel.removeElements(annot)
        self.assertEqual(len(annotModel.load(annot['_id'])['annotation']['elements']), 0)

    #  Add tests for:
    # removeOldElements
    # updateElements


class LargeImageAnnotationRestTest(common.LargeImageCommonTest):
    def testGetAnnotation(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        annotId = str(annot['_id'])
        resp = self.request(path='/annotation/%s' % annotId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['annotation']['elements'][0]['center'],
                         annot['annotation']['elements'][0]['center'])
        largeSample = makeLargeSampleAnnotation()
        annot = annotModel.createAnnotation(item, self.admin, largeSample)
        annotId = str(annot['_id'])
        resp = self.request(path='/annotation/%s' % annotId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']),
                         len(largeSample['elements']))  # 7707
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'limit': 100,
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']), 100)
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'left': 3000,
                'right': 4000,
                'top': 4500,
                'bottom': 6500,
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']), 157)
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'left': 3000,
                'right': 4000,
                'top': 4500,
                'bottom': 6500,
                'minimumSize': 16,
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']), 39)
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'maxDetails': 300,
            })
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']), 75)
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'maxDetails': 300,
                'sort': 'size',
                'sortdir': -1,
            })
        self.assertStatusOk(resp)
        elements = resp.json['annotation']['elements']
        self.assertGreater(elements[0]['width'] * elements[0]['height'],
                           elements[-1]['width'] * elements[-1]['height'])
        resp = self.request(
            path='/annotation/%s' % annotId, user=self.admin, params={
                'maxDetails': 300,
                'sort': 'size',
                'sortdir': 1,
            })
        self.assertStatusOk(resp)
        elements = resp.json['annotation']['elements']
        self.assertLess(elements[0]['width'] * elements[0]['height'],
                        elements[-1]['width'] * elements[-1]['height'])

    def testDeleteAnnotation(self):
        annotModel = self.model('annotation', 'large_image')
        file = self._uploadFile(os.path.join(
            os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'))
        item = self.model('item').load(file['itemId'], level=AccessType.READ,
                                       user=self.admin)
        annot = annotModel.createAnnotation(item, self.admin, sampleAnnotation)
        annotId = str(annot['_id'])
        self.assertIsNotNone(annotModel.load(annot['_id']))
        resp = self.request(path='/annotation/%s' % annotId, user=self.admin,
                            method='DELETE')
        self.assertStatusOk(resp)
        self.assertIsNone(annotModel.load(annot['_id']))

    #  Add tests for:
    # find
    # getAnnotationSchema
    # createAnnotation
    # updateAnnotation
