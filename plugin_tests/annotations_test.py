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

import copy
import json
import math
import os
import random

from bson import ObjectId
import mock
import six
from six.moves import range

from girder import config
from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.item import Item
from girder.models.setting import Setting

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
        from girder.plugins.large_image.models.annotation import Annotation
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'rectangle',
                'center': [10, 20, 0],
                'width': 5,
                'height': 10,
            }]
        }
        result = Annotation().createAnnotation(item, self.admin, annotation)
        self.assertIn('_id', result)
        annotId = result['_id']
        result = Annotation().load(annotId, user=self.admin)
        self.assertEqual(len(result['annotation']['elements']), 1)

    def testSimilarElementStructure(self):
        from girder.plugins.large_image.models.annotation import Annotation
        ses = Annotation()._similarElementStructure
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
        from girder.plugins.large_image.models.annotation import Annotation

        item = Item().createItem('sample', self.admin, self.publicFolder)
        with six.assertRaisesRegex(self, Exception, 'Invalid ObjectId'):
            Annotation().load('nosuchid')
        self.assertIsNone(Annotation().load('012345678901234567890123', user=self.admin))
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        loaded = Annotation().load(annot['_id'], user=self.admin)
        self.assertEqual(loaded['annotation']['elements'][0]['center'],
                         annot['annotation']['elements'][0]['center'])

        annot0 = Annotation().createAnnotation(item, self.admin, sampleAnnotationEmpty)
        loaded = Annotation().load(annot0['_id'], user=self.admin)
        self.assertEqual(len(loaded['annotation']['elements']), 0)

    def testSave(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annot = Annotation().load(annot['_id'], region={'sort': 'size'}, user=self.admin)
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        saved = Annotation().save(annot)
        loaded = Annotation().load(annot['_id'], region={'sort': 'size'}, user=self.admin)
        self.assertEqual(len(saved['annotation']['elements']), 4)
        self.assertEqual(len(loaded['annotation']['elements']), 4)
        self.assertEqual(saved['annotation']['elements'][0]['type'], 'rectangle')
        self.assertEqual(loaded['annotation']['elements'][0]['type'], 'point')
        self.assertEqual(saved['annotation']['elements'][-1]['type'], 'point')
        self.assertEqual(loaded['annotation']['elements'][-1]['type'], 'rectangle')
        self.assertEqual(len(list(Annotation().versionList(saved['_id']))), 1)

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        saved['annotation']['name'] = 'New name'
        saved2 = Annotation().save(saved)
        versions = list(Annotation().versionList(saved2['_id']))
        self.assertEqual(len(versions), 2)
        # If we save with an old version, we should get the original id back
        self.assertNotEqual(versions[1]['_id'], loaded['_id'])
        saved3 = Annotation().save(versions[1])
        self.assertEqual(saved3['_id'], loaded['_id'])

    def testUpdateAnnotaton(self):
        from girder.plugins.large_image.models.annotation import Annotation

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annot = Annotation().load(annot['_id'], region={'sort': 'size'}, user=self.admin)
        saved = Annotation().updateAnnotation(annot, updateUser=self.user)
        self.assertEqual(saved['updatedId'], self.user['_id'])

    def testRemove(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))
        result = Annotation().remove(annot)
        self.assertEqual(result.deleted_count, 1)
        self.assertIsNone(Annotation().load(annot['_id'], user=self.admin))

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))
        result = Annotation().remove(annot)
        self.assertEqual(result.modified_count, 1)
        self.assertFalse(Annotation().load(annot['_id'], user=self.admin)['_active'])

    def testOnItemRemove(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))
        Item().remove(item)
        self.assertIsNone(Annotation().load(annot['_id'], user=self.admin))

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))
        Item().remove(item)
        loaded = Annotation().load(annot['_id'], user=self.admin)
        self.assertIsNotNone(loaded)
        self.assertFalse(loaded['_active'])

    def testValidate(self):
        from girder.plugins.large_image.models.annotation import Annotation

        annot = copy.deepcopy(sampleAnnotation)
        doc = {'annotation': annot}
        self.assertIsNotNone(Annotation().validate(doc))
        annot['elements'][0]['id'] = ObjectId('012345678901234567890123')
        annot['elements'].append(annot['elements'][0])
        with six.assertRaisesRegex(self, ValidationException, 'not unique'):
            Annotation().validate(doc)
        annot['elements'][1] = copy.deepcopy(annot['elements'][0])
        annot['elements'][1]['id'] = ObjectId('012345678901234567890124')
        self.assertIsNotNone(Annotation().validate(doc))

    def testVersionList(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', self.admin, self.privateFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annot['annotation']['name'] = 'First Change'
        annot = Annotation().save(annot)
        annot['annotation']['name'] = 'Second Change'
        annot = Annotation().save(annot)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.admin))), 1)
        self.assertEqual(len(list(Annotation().versionList(
            str(annot['_id']), user=self.admin))), 1)
        self.assertEqual(len(list(Annotation().versionList(
            str(annot['_id']), force=True))), 1)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.user))), 0)

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annot['annotation']['name'] = 'First Change'
        annot = Annotation().save(annot)
        # simulate a concurrent save
        dup = Annotation().findOne({'_id': annot['_id']})
        dup['_annotationId'] = dup.pop('_id')
        dup['_active'] = False
        Annotation().collection.insert_one(dup)
        # Save again
        annot['annotation']['name'] = 'Second Change'
        annot = Annotation().save(annot)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.admin))), 3)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.user))), 0)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.admin, offset=1))), 2)
        self.assertEqual(len(list(Annotation().versionList(
            annot['_id'], user=self.admin, offset=1, limit=1))), 1)

    def testGetVersion(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', self.admin, self.privateFolder)
        annot = Annotation().createAnnotation(item, self.admin, copy.deepcopy(sampleAnnotation))
        annot['annotation']['name'] = 'First Change'
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        annot = Annotation().save(annot)
        annot['annotation']['name'] = 'Second Change'
        annot['annotation']['elements'].pop(2)
        annot = Annotation().save(annot)
        versions = list(Annotation().versionList(annot['_id'], user=self.admin))

        with self.assertRaises(AccessException):
            Annotation().getVersion(annot['_id'], versions[0]['_version'], user=self.user)
        self.assertEqual(len(Annotation().getVersion(
            annot['_id'],
            versions[0]['_version'],
            user=self.admin)['annotation']['elements']), 3)
        self.assertEqual(len(Annotation().getVersion(
            annot['_id'],
            versions[1]['_version'],
            user=self.admin)['annotation']['elements']), 4)
        self.assertEqual(len(Annotation().getVersion(
            annot['_id'],
            versions[2]['_version'],
            user=self.admin)['annotation']['elements']), 1)
        # We can get a version by its own id
        self.assertEqual(len(Annotation().getVersion(
            str(versions[1]['_id']),
            versions[1]['_version'],
            user=self.admin)['annotation']['elements']), 4)
        # Asking for an invalid version gets us None
        self.assertIsNone(Annotation().getVersion(
            annot['_id'],
            versions[0]['_version'] + 1,
            user=self.admin))

    def testRevertVersion(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', self.admin, self.privateFolder)
        annot = Annotation().createAnnotation(item, self.admin, copy.deepcopy(sampleAnnotation))
        annot['annotation']['name'] = 'First Change'
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        annot = Annotation().save(annot)
        annot['annotation']['name'] = 'Second Change'
        annot['annotation']['elements'].pop(2)
        annot = Annotation().save(annot)
        versions = list(Annotation().versionList(annot['_id'], user=self.admin))
        self.assertIsNone(Annotation().revertVersion(
            annot['_id'], versions[0]['_version'] + 1, user=self.admin))
        self.assertEqual(len(Annotation().revertVersion(
            annot['_id'], force=True)['annotation']['elements']), 4)
        self.assertEqual(len(Annotation().revertVersion(
            annot['_id'], force=True)['annotation']['elements']), 3)
        self.assertEqual(len(Annotation().revertVersion(
            annot['_id'], versions[2]['_version'], force=True)['annotation']['elements']), 1)
        Annotation().remove(annot)
        self.assertEqual(len(Annotation().revertVersion(
            annot['_id'], user=self.admin)['annotation']['elements']), 1)

    def testAnnotationsAfterCopyItem(self):
        from girder.plugins.large_image.models.annotation import Annotation
        item = Item().createItem('sample', self.admin, self.publicFolder)
        Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        resp = self.request(
            '/annotation', user=self.admin, params={'itemId': item['_id']})
        self.assertStatusOk(resp)
        self.assertTrue(len(resp.json) == 1)
        resp = self.request(
            '/item/%s/copy' % item['_id'], method='POST', user=self.admin)
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation', user=self.admin, params={'itemId': resp.json['_id']})
        self.assertStatusOk(resp)
        self.assertTrue(len(resp.json) == 1)
        resp = self.request(
            '/item/%s/copy' % item['_id'], method='POST', user=self.admin,
            params={'copyAnnotations': 'true'})
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation', user=self.admin, params={'itemId': resp.json['_id']})
        self.assertStatusOk(resp)
        self.assertTrue(len(resp.json) == 1)
        resp = self.request(
            '/item/%s/copy' % item['_id'], method='POST', user=self.admin,
            params={'copyAnnotations': 'false'})
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation', user=self.admin, params={'itemId': resp.json['_id']})
        self.assertStatusOk(resp)
        self.assertTrue(len(resp.json) == 0)
        resp = self.request(
            '/item/%s/copy' % item['_id'], method='POST', user=self.admin,
            params={'copyAnnotations': True})
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation', user=self.admin, params={'itemId': resp.json['_id']})
        self.assertStatusOk(resp)
        self.assertTrue(len(resp.json) == 1)


class LargeImageAnnotationElementTest(common.LargeImageCommonTest):
    def testInitialize(self):
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        # initialize should be called as we fetch the model
        self.assertEqual(Annotationelement().name, 'annotationelement')

    def testGetNextVersionValue(self):
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        val1 = Annotationelement().getNextVersionValue()
        val2 = Annotationelement().getNextVersionValue()
        self.assertGreater(val2, val1)
        Annotationelement().versionId = None
        val3 = Annotationelement().getNextVersionValue()
        self.assertGreater(val3, val2)

    def testBoundingBox(self):
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        bbox = Annotationelement()._boundingBox({'points': [[1, -2, 3], [-4, 5, -6], [7, -8, 9]]})
        self.assertEqual(bbox, {
            'lowx': -4, 'lowy': -8, 'lowz': -6,
            'highx': 7, 'highy': 5, 'highz': 9,
            'details': 3,
            'size': ((7+4)**2 + (8+5)**2)**0.5})
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3]})
        self.assertEqual(bbox, {
            'lowx': 0.5, 'lowy': -2.5, 'lowz': 3,
            'highx': 1.5, 'highy': -1.5, 'highz': 3,
            'details': 1,
            'size': 2**0.5})
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3], 'radius': 4})
        self.assertEqual(bbox, {
            'lowx': -3, 'lowy': -6, 'lowz': 3,
            'highx': 5, 'highy': 2, 'highz': 3,
            'details': 4,
            'size': 8 * 2**0.5})
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3], 'width': 2, 'height': 4})
        self.assertEqual(bbox, {
            'lowx': 0, 'lowy': -4, 'lowz': 3,
            'highx': 2, 'highy': 0, 'highz': 3,
            'details': 4,
            'size': (2**2 + 4**2)**0.5})
        bbox = Annotationelement()._boundingBox({
            'center': [1, -2, 3],
            'width': 2, 'height': 4,
            'rotation': math.pi * 0.25})
        self.assertAlmostEqual(bbox['size'], 4, places=4)

    def testGetElements(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        item = Item().createItem('sample', self.admin, self.publicFolder)
        largeSample = makeLargeSampleAnnotation()
        # Use a copy of largeSample so we don't just have a referecne to it
        annot = Annotation().createAnnotation(item, self.admin, largeSample.copy())
        # Clear existing element data, the get elements
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot)
        self.assertIn('_elementQuery', annot)
        self.assertEqual(len(annot['annotation']['elements']),
                         len(largeSample['elements']))  # 7707
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {'limit': 100})
        self.assertIn('_elementQuery', annot)
        self.assertEqual(annot['_elementQuery']['count'], len(largeSample['elements']))
        self.assertEqual(annot['_elementQuery']['returned'], 100)
        self.assertEqual(len(annot['annotation']['elements']), 100)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500})
        self.assertEqual(len(annot['annotation']['elements']), 157)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500,
            'minimumSize': 16})
        self.assertEqual(len(annot['annotation']['elements']), 39)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {'maxDetails': 300})
        self.assertEqual(len(annot['annotation']['elements']), 75)
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': -1})
        elements = annot['annotation']['elements']
        self.assertGreater(elements[0]['width'] * elements[0]['height'],
                           elements[-1]['width'] * elements[-1]['height'])
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': 1})
        elements = annot['annotation']['elements']
        elements = annot['annotation']['elements']
        self.assertLess(elements[0]['width'] * elements[0]['height'],
                        elements[-1]['width'] * elements[-1]['height'])

    def testRemoveWithQuery(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertEqual(len(Annotation().load(
            annot['_id'], user=self.admin)['annotation']['elements']), 1)
        Annotationelement().removeWithQuery({'annotationId': annot['_id']})
        self.assertEqual(len(Annotation().load(
            annot['_id'], user=self.admin)['annotation']['elements']), 0)

    def testRemoveElements(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image.models.annotationelement import Annotationelement

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        self.assertEqual(len(Annotation().load(
            annot['_id'], user=self.admin)['annotation']['elements']), 1)
        Annotationelement().removeElements(annot)
        self.assertEqual(len(Annotation().load(
            annot['_id'], user=self.admin)['annotation']['elements']), 0)

    def testAnnotationGroup(self):
        from girder.plugins.large_image.models.annotation import Annotation

        item = Item().createItem('sample', self.admin, self.publicFolder)
        elements = [{
            'type': 'rectangle',
            'center': [20.0, 25.0, 0],
            'width': 14.0,
            'height': 15.0,
            'group': 'a'
        }, {
            'type': 'rectangle',
            'center': [40.0, 15.0, 0],
            'width': 5.0,
            'height': 5.0
        }]
        annotationWithGroup = {
            'name': 'groups',
            'elements': elements
        }

        annot = Annotation().createAnnotation(item, self.admin, annotationWithGroup)
        result = Annotation().load(annot['_id'], user=self.admin)
        self.assertEqual(result['annotation']['elements'][0]['group'], 'a')

    #  Add tests for:
    # removeOldElements
    # updateElements


class LargeImageAnnotationRestTest(common.LargeImageCommonTest):
    def testGetAnnotationSchema(self):
        resp = self.request('/annotation/schema')
        self.assertStatusOk(resp)
        self.assertIn('$schema', resp.json)

    def testGetAnnotation(self):
        from girder.plugins.large_image.models.annotation import Annotation

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annotId = str(annot['_id'])
        resp = self.request(path='/annotation/%s' % annotId, user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['annotation']['elements'][0]['center'],
                         annot['annotation']['elements'][0]['center'])
        largeSample = makeLargeSampleAnnotation()
        annot = Annotation().createAnnotation(item, self.admin, largeSample)
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

    def testAnnotationCopy(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create annotation on an item
        itemSrc = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(itemSrc, self.admin, sampleAnnotation)
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))

        # Create a new item
        itemDest = Item().createItem('sample', self.admin, self.publicFolder)

        # Copy the annotation from one item to an other
        resp = self.request(
            path='/annotation/{}/copy'.format(annot['_id']),
            method='POST',
            user=self.admin,
            params={
                'itemId': itemDest.get('_id')
            }
        )
        self.assertStatusOk(resp)
        itemDest = Item().load(itemDest.get('_id'), level=AccessType.READ)

        # Check if the annotation is in the destination item
        resp = self.request(
            path='/annotation',
            method='GET',
            user=self.admin,
            params={
                'itemId': itemDest.get('_id'),
                'name': 'sample'
            }
        )
        self.assertStatusOk(resp)
        self.assertIsNotNone(resp.json)

    def testItemAnnotationEndpoints(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create two annotations on an item
        itemSrc = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(itemSrc, self.admin, sampleAnnotation)
        annot = Annotation().setPublic(annot, False, True)
        Annotation().createAnnotation(itemSrc, self.admin, sampleAnnotationEmpty)
        # Get all annotations for that item as the user
        resp = self.request(
            path='/annotation/item/{}'.format(itemSrc['_id']),
            user=self.user
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(len(resp.json[0]['annotation']['elements']), 0)

        # Get all annotations for that item as the admin
        resp = self.request(
            path='/annotation/item/{}'.format(itemSrc['_id']),
            user=self.admin
        )
        self.assertStatusOk(resp)
        annotList = resp.json
        self.assertEqual(len(annotList), 2)
        self.assertEqual(annotList[0]['annotation']['elements'][0]['center'],
                         annot['annotation']['elements'][0]['center'])
        self.assertEqual(len(annotList[1]['annotation']['elements']), 0)

        # Create a new item
        itemDest = Item().createItem('sample', self.admin, self.publicFolder)

        # Set the annotations on the new item
        resp = self.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=self.admin,
            type='application/json',
            body=json.dumps(annotList)
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 2)

        # Check if the annotations are in the destination item
        resp = self.request(
            path='/annotation',
            method='GET',
            user=self.admin,
            params={
                'itemId': itemDest.get('_id'),
                'name': 'sample'
            }
        )
        self.assertStatusOk(resp)
        self.assertIsNotNone(resp.json)

        # Check failure conditions
        resp = self.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=self.admin,
            type='application/json',
            body=json.dumps(['not an object'])
        )
        self.assertStatus(resp, 400)
        resp = self.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=self.admin,
            type='application/json',
            body=json.dumps([{'key': 'not an annotation'}])
        )
        self.assertStatus(resp, 400)

        # Delete annotations
        resp = self.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='DELETE',
            user=None
        )
        self.assertStatus(resp, 401)

        resp = self.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='DELETE',
            user=self.admin
        )
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, 2)

    def testDeleteAnnotation(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        annotId = str(annot['_id'])
        self.assertIsNotNone(Annotation().load(annot['_id'], user=self.admin))
        resp = self.request(path='/annotation/%s' % annotId, user=self.admin, method='DELETE')
        self.assertStatusOk(resp)
        self.assertIsNone(Annotation().load(annot['_id']))

    def testFindAnnotatedImages(self):

        def create_annotation(item, user):
            from girder.plugins.large_image.models.annotation import Annotation

            return str(Annotation().createAnnotation(item, user, sampleAnnotation)['_id'])

        def upload(name, user=self.user, private=False):
            file = self._uploadFile(os.path.join(
                os.environ['LARGE_IMAGE_DATA'], 'sample_image.ptif'), name, private=private)
            item = Item().load(file['itemId'], level=AccessType.READ, user=self.admin)

            create_annotation(item, user)
            create_annotation(item, user)
            create_annotation(item, self.admin)

            return str(item['_id'])

        item1 = upload('image1-abcd.ptif', self.admin)
        item2 = upload(u'Образец Картина.ptif')
        item3 = upload('image3-ABCD.ptif')
        item4 = upload('image3-ijkl.ptif', self.user, True)

        # test default search
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item4, item3, item2, item1])

        # test filtering by user
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100,
            'creatorId': self.user['_id']
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item4, item3, item2])

        # test getting annotations without admin access
        resp = self.request('/annotation/images', user=self.user, params={
            'limit': 100
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item3, item2, item1])

        # test sort direction
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100,
            'sortdir': 1
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item1, item2, item3, item4])

        # test pagination
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 1
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item4)

        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 1,
            'offset': 3
        })
        self.assertStatusOk(resp)
        self.assertEqual(resp.json[0]['_id'], item1)

        # test filtering by image name
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100,
            'imageName': 'image3-aBcd.ptif'
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item3])

        # test filtering by image name substring
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100,
            'imageName': 'aBc'
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item3, item1])

        # test filtering by image name with unicode
        resp = self.request('/annotation/images', user=self.admin, params={
            'limit': 100,
            'imageName': u'Картина'
        })
        self.assertStatusOk(resp)
        ids = [image['_id'] for image in resp.json]
        self.assertEqual(ids, [item2])

    def testCreateAnnotation(self):
        item = Item().createItem('sample', self.admin, self.publicFolder)
        itemId = str(item['_id'])

        resp = self.request(
            '/annotation', method='POST', user=self.admin,
            params={'itemId': itemId}, type='application/json',
            body=json.dumps(sampleAnnotation))
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation', method='POST', user=self.admin,
            params={'itemId': itemId}, type='application/json', body='badJSON')
        self.assertStatus(resp, 400)
        resp = self.request(
            '/annotation', method='POST', user=self.admin,
            params={'itemId': itemId}, type='application/json',
            body=json.dumps({'key': 'not an annotation'}))
        self.assertStatus(resp, 400)

    def testUpdateAnnotation(self):
        from girder.plugins.large_image.models.annotation import Annotation

        item = Item().createItem('sample', self.admin, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)
        resp = self.request(path='/annotation/%s' % annot['_id'], user=self.admin)
        self.assertStatusOk(resp)
        annot = resp.json
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        resp = self.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=self.admin,
            type='application/json', body=json.dumps(annot['annotation']))
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['annotation']['name'], 'sample')
        self.assertEqual(len(resp.json['annotation']['elements']), 4)
        # Test update without elements
        annotNoElem = copy.deepcopy(annot)
        del annotNoElem['annotation']['elements']
        annotNoElem['annotation']['name'] = 'newname'
        resp = self.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=self.admin,
            type='application/json', body=json.dumps(annotNoElem['annotation']))
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['annotation']['name'], 'newname')
        self.assertNotIn('elements', resp.json['annotation'])
        # Test with passed item id
        item2 = Item().createItem('sample2', self.admin, self.publicFolder)
        resp = self.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=self.admin,
            params={'itemId': item2['_id']}, type='application/json',
            body=json.dumps(annot['annotation']))
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['itemId'], str(item2['_id']))

    def testAnnotationAccessControlEndpoints(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create an annotation
        item = Item().createItem('userItem', self.user, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)

        # Try to get ACL's as a user
        resp = self.request('/annotation/%s/access' % annot['_id'], user=self.user)
        self.assertStatus(resp, 403)

        # Get the ACL's as an admin
        resp = self.request('/annotation/%s/access' % annot['_id'], user=self.admin)
        self.assertStatusOk(resp)
        access = dict(**resp.json)

        # Set the public flag to false and try to read as a user
        resp = self.request(
            '/annotation/%s/access' % annot['_id'],
            method='PUT',
            user=self.admin,
            params={
                'access': json.dumps(access),
                'public': False
            }
        )
        self.assertStatusOk(resp)
        resp = self.request(
            '/annotation/%s' % annot['_id'],
            user=self.user
        )
        self.assertStatus(resp, 403)
        # The admin should still be able to get the annotation with elements
        resp = self.request(
            '/annotation/%s' % annot['_id'],
            user=self.admin
        )
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json['annotation']['elements']), 1)

        # Give the user admin access
        access['users'].append({
            'login': self.user['login'],
            'flags': [],
            'id': str(self.user['_id']),
            'level': AccessType.ADMIN
        })
        resp = self.request(
            '/annotation/%s/access' % annot['_id'],
            method='PUT',
            user=self.admin,
            params={
                'access': json.dumps(access)
            }
        )
        self.assertStatusOk(resp)

        # Get the ACL's as a user
        resp = self.request('/annotation/%s/access' % annot['_id'], user=self.user)
        self.assertStatusOk(resp)

    def testAnnotationHistoryEndpoints(self):
        from girder.plugins.large_image.models.annotation import Annotation
        from girder.plugins.large_image import constants

        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', self.admin, self.privateFolder)
        # Create an annotation with some history
        annot = Annotation().createAnnotation(item, self.admin, copy.deepcopy(sampleAnnotation))
        annot['annotation']['name'] = 'First Change'
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        annot = Annotation().save(annot)
        # simulate a concurrent save
        dup = Annotation().findOne({'_id': annot['_id']})
        dup['_annotationId'] = dup.pop('_id')
        dup['_active'] = False
        Annotation().collection.insert_one(dup)
        # Save again
        annot['annotation']['name'] = 'Second Change'
        annot['annotation']['elements'].pop(2)
        annot = Annotation().save(annot)

        # Test the list of versions
        resp = self.request('/annotation/%s/history' % annot['_id'], user=self.user)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json, [])
        resp = self.request('/annotation/%s/history' % annot['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        versions = resp.json

        # Test getting a specific version
        resp = self.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[1]['_version']), user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[1]['_version']), user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['_annotationId'], str(annot['_id']))
        self.assertEqual(len(resp.json['annotation']['elements']), 4)
        resp = self.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[0]['_version'] + 1), user=self.admin)
        self.assertStatus(resp, 400)

        # Test revert
        resp = self.request('/annotation/%s/history/revert' % (
            annot['_id']), method='PUT', user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request('/annotation/%s/history/revert' % (
            annot['_id']), method='PUT', user=self.admin, params={
                'version': versions[0]['_version'] + 1
            })
        self.assertStatus(resp, 400)
        resp = self.request('/annotation/%s/history/revert' % (
            annot['_id']), method='PUT', user=self.admin, params={
                'version': versions[1]['_version']
            })
        self.assertStatusOk(resp)
        loaded = Annotation().load(annot['_id'], user=self.admin)
        self.assertEqual(len(loaded['annotation']['elements']), 4)

        # Test old
        resp = self.request('/annotation/old', method='GET', user=self.user)
        self.assertStatus(resp, 403)
        resp = self.request('/annotation/old', method='GET', user=self.admin)
        self.assertStatus(resp, 200)
        self.assertEqual(resp.json['abandonedVersions'], 0)
        resp = self.request('/annotation/old', method='DELETE', user=self.admin)
        self.assertStatus(resp, 200)
        self.assertEqual(resp.json['abandonedVersions'], 0)

    #  Add tests for:
    # find


class LargeImageAnnotationElementGroups(common.LargeImageCommonTest):
    def setUp(self):
        from girder.plugins.large_image.models.annotation import Annotation

        super(LargeImageAnnotationElementGroups, self).setUp()

        self.item = Item().createItem('sample', self.admin, self.publicFolder)
        annotationModel = Annotation()

        self.noGroups = annotationModel.createAnnotation(
            self.item, self.admin,
            {
                'name': 'nogroups',
                'elements': [{
                    'type': 'rectangle',
                    'center': [20.0, 25.0, 0],
                    'width': 14.0,
                    'height': 15.0,
                }, {
                    'type': 'rectangle',
                    'center': [40.0, 15.0, 0],
                    'width': 5.0,
                    'height': 5.0
                }]
            }
        )

        self.notMigrated = annotationModel.createAnnotation(
            self.item, self.admin,
            {
                'name': 'notmigrated',
                'elements': [{
                    'type': 'rectangle',
                    'center': [20.0, 25.0, 0],
                    'width': 14.0,
                    'height': 15.0,
                    'group': 'b'
                }, {
                    'type': 'rectangle',
                    'center': [40.0, 15.0, 0],
                    'width': 5.0,
                    'height': 5.0,
                    'group': 'a'
                }]
            }
        )
        annotationModel.collection.update_one(
            {'_id': self.notMigrated['_id']},
            {'$unset': {'groups': ''}}
        )

        self.hasGroups = annotationModel.createAnnotation(
            self.item, self.admin,
            {
                'name': 'hasgroups',
                'elements': [{
                    'type': 'rectangle',
                    'center': [20.0, 25.0, 0],
                    'width': 14.0,
                    'height': 15.0,
                    'group': 'a'
                }, {
                    'type': 'rectangle',
                    'center': [40.0, 15.0, 0],
                    'width': 5.0,
                    'height': 5.0,
                    'group': 'c'
                }, {
                    'type': 'rectangle',
                    'center': [50.0, 10.0, 0],
                    'width': 5.0,
                    'height': 5.0
                }]
            }
        )

    def testFindAnnotations(self):
        resp = self.request('/annotation', user=self.admin, params={'itemId': self.item['_id']})
        self.assertStatusOk(resp)
        self.assertEqual(len(resp.json), 3)
        for annotation in resp.json:
            if annotation['_id'] == str(self.noGroups['_id']):
                self.assertEqual(annotation['groups'], [None])
            elif annotation['_id'] == str(self.notMigrated['_id']):
                self.assertEqual(annotation['groups'], ['a', 'b'])
            elif annotation['_id'] == str(self.hasGroups['_id']):
                self.assertEqual(annotation['groups'], ['a', 'c', None])
            else:
                raise Exception('Unexpected annotation id')

    def testLoadAnnotation(self):
        resp = self.request('/annotation/%s' % str(self.hasGroups['_id']), user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['groups'], ['a', 'c', None])

    def testCreateAnnotation(self):
        annotation = {
            'name': 'created',
            'elements': [{
                'type': 'rectangle',
                'center': [20.0, 25.0, 0],
                'width': 14.0,
                'height': 15.0,
                'group': 'a'
            }]
        }
        resp = self.request(
            '/annotation',
            user=self.admin,
            method='POST',
            params={'itemId': str(self.item['_id'])},
            type='application/json',
            body=json.dumps(annotation)
        )
        self.assertStatusOk(resp)

        resp = self.request('/annotation/%s' % resp.json['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['groups'], ['a'])

    def testUpdateAnnotation(self):
        annotation = {
            'name': 'created',
            'elements': [{
                'type': 'rectangle',
                'center': [20.0, 25.0, 0],
                'width': 14.0,
                'height': 15.0,
                'group': 'd'
            }]
        }
        resp = self.request(
            '/annotation/%s' % str(self.hasGroups['_id']),
            user=self.admin,
            method='PUT',
            type='application/json',
            body=json.dumps(annotation)
        )
        self.assertStatusOk(resp)

        resp = self.request('/annotation/%s' % resp.json['_id'], user=self.admin)
        self.assertStatusOk(resp)
        self.assertEqual(resp.json['groups'], ['d'])


class LargeImageAnnotationAccessMigrationTest(common.LargeImageCommonTest):

    def testMigrateAnnotationAccessControl(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create an annotation
        item = Item().createItem('userItem', self.user, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)

        # assert ACL's work
        with self.assertRaises(AccessException):
            Annotation().load(annot['_id'], user=self.user, level=AccessType.WRITE)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        Annotation().save(annot)

        # load the annotation and assert access properties were added
        annot = Annotation().load(annot['_id'], force=True)

        self.assertEqual(annot['access'], self.publicFolder['access'])
        self.assertEqual(annot['public'], True)

    def testLoadAnnotationWithCoreKWArgs(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # try to load a non-existing annotation
        with self.assertRaises(ValidationException):
            Annotation().load(ObjectId(), user=self.admin, exc=True)

    def testMigrateAnnotationAccessControlNoItemError(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create an annotation
        item = Item().createItem('userItem', self.user, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        annot['itemId'] = ObjectId()

        Annotation().save(annot)
        with mock.patch('girder.plugins.large_image.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        self.assertNotIn('access', annot)

    def testMigrateAnnotationAccessControlNoFolderError(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create an annotation
        item = Item().createItem('userItem', self.user, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        Annotation().save(annot)

        # save an invalid folder id to the item
        item['folderId'] = ObjectId()
        Item().save(item)

        with mock.patch('girder.plugins.large_image.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        self.assertNotIn('access', annot)

    def testMigrateAnnotationAccessControlNoUserError(self):
        from girder.plugins.large_image.models.annotation import Annotation

        # create an annotation
        item = Item().createItem('userItem', self.user, self.publicFolder)
        annot = Annotation().createAnnotation(item, self.admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        annot['creatorId'] = ObjectId()
        Annotation().save(annot)

        with mock.patch('girder.plugins.large_image.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        self.assertNotIn('access', annot)
