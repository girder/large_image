# -*- coding: utf-8 -*-

from bson import ObjectId
import copy
import json
import math
import mock
import pytest
import random
from six.moves import range

from girder.constants import AccessType
from girder.exceptions import AccessException, ValidationException
from girder.models.item import Item
from girder.models.setting import Setting

from girder_large_image_annotation.models import annotation
from girder_large_image_annotation.models.annotation import Annotation
from girder_large_image_annotation.models.annotationelement import Annotationelement

from girder_large_image import constants

from . import girder_utilities as utilities


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


@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotation(object):
    def testAnnotationSchema(self):
        schema = annotation.AnnotationSchema
        assert schema.annotationSchema is not None
        assert schema.annotationElementSchema is not None

    def testAnnotationCreate(self, admin):
        item = Item().createItem('sample', admin, utilities.namedFolder(admin, 'Public'))
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'rectangle',
                'center': [10, 20, 0],
                'width': 5,
                'height': 10,
            }]
        }
        result = Annotation().createAnnotation(item, admin, annotation)
        assert '_id' in result
        annotId = result['_id']
        result = Annotation().load(annotId, user=admin)
        assert len(result['annotation']['elements']) == 1

    def testSimilarElementStructure(self):
        ses = Annotation()._similarElementStructure
        assert ses('a', 'a')
        assert not ses('a', 'b')
        assert ses(10, 10)
        assert ses(10, 11)
        assert not ses(10, 10.0)
        assert ses({'a': 10}, {'a': 12})
        assert not ses({'a': 10}, {'a': 'b'})
        assert not ses({'a': 10, 'b': 11}, {'a': 10})
        assert not ses({'a': 10, 'b': 11}, {'a': 10, 'c': 11})
        assert ses({'id': '012345678901234567890123'},
                   {'id': '01234567890123456789ffff'})
        assert not ses({'id': '012345678901234567890123'},
                       {'id': '01234567890123456789----'})
        assert ses([1, 2, 3, 4], [2, 3, 4, 5])
        assert not ses([1, 2, 3, 4], [2, 3, 4, 5, 6])
        assert not ses([1, 2, 3, 4], [2, 3, 4, 'a'])
        assert ses({'points': [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]}, {'points': [
            [10, 11, 12],
            [13, 14, 15],
            [16, 17, 18],
            [19, 20, 21.1],
        ]})
        assert not ses({'points': [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9],
        ]}, {'points': [
            [10, 11, 12],
            [13, 14, 15],
            [16, 17, 18],
            [19, 20, 'b'],
        ]})

    def testLoad(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')

        item = Item().createItem('sample', admin, publicFolder)
        with pytest.raises(Exception) as exc:
            Annotation().load('nosuchid')
        assert 'Invalid ObjectId' in str(exc)
        assert Annotation().load('012345678901234567890123', user=admin) is None
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        loaded = Annotation().load(annot['_id'], user=admin)
        assert (loaded['annotation']['elements'][0]['center'] ==
                annot['annotation']['elements'][0]['center'])

        annot0 = Annotation().createAnnotation(item, admin, sampleAnnotationEmpty)
        loaded = Annotation().load(annot0['_id'], user=admin)
        assert len(loaded['annotation']['elements']) == 0

    def testSave(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annot = Annotation().load(annot['_id'], region={'sort': 'size'}, user=admin)
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        saved = Annotation().save(annot)
        loaded = Annotation().load(annot['_id'], region={'sort': 'size'}, user=admin)
        assert len(saved['annotation']['elements']) == 4
        assert len(loaded['annotation']['elements']) == 4
        assert saved['annotation']['elements'][0]['type'] == 'rectangle'
        assert loaded['annotation']['elements'][0]['type'] == 'point'
        assert saved['annotation']['elements'][-1]['type'] == 'point'
        assert loaded['annotation']['elements'][-1]['type'] == 'rectangle'
        assert len(list(Annotation().versionList(saved['_id']))) == 1

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        saved['annotation']['name'] = 'New name'
        saved2 = Annotation().save(saved)
        versions = list(Annotation().versionList(saved2['_id']))
        assert len(versions) == 2
        # If we save with an old version, we should get the original id back
        assert not versions[1]['_id'] == loaded['_id']
        saved3 = Annotation().save(versions[1])
        assert saved3['_id'] == loaded['_id']

    def testUpdateAnnotaton(self, user, admin):
        publicFolder = utilities.namedFolder(user, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annot = Annotation().load(annot['_id'], region={'sort': 'size'}, user=admin)
        saved = Annotation().updateAnnotation(annot, updateUser=user)
        assert saved['updatedId'] == user['_id']

    def testRemove(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        result = Annotation().remove(annot)
        assert result.deleted_count == 1
        assert Annotation().load(annot['_id'], user=admin) is None

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        result = Annotation().remove(annot)
        assert result.modified_count == 1
        assert not Annotation().load(annot['_id'], user=admin)['_active']

    def testOnItemRemove(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        Item().remove(item)
        assert Annotation().load(annot['_id'], user=admin) is None

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        Item().remove(item)
        loaded = Annotation().load(annot['_id'], user=admin)
        assert loaded is not None
        assert not loaded['_active']

    def testValidate(self):
        annot = copy.deepcopy(sampleAnnotation)
        doc = {'annotation': annot}
        assert Annotation().validate(doc) is not None
        annot['elements'][0]['id'] = ObjectId('012345678901234567890123')
        annot['elements'].append(annot['elements'][0])
        with pytest.raises(ValidationException) as exc:
            Annotation().validate(doc)
        assert 'not unique' in str(exc)
        annot['elements'][1] = copy.deepcopy(annot['elements'][0])
        annot['elements'][1]['id'] = ObjectId('012345678901234567890124')
        assert Annotation().validate(doc) is not None

    def testVersionList(self, user, admin):
        privateFolder = utilities.namedFolder(admin, 'Private')
        # Test without history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', admin, privateFolder)
        annot = Annotation().createAnnotation(item, admin, copy.deepcopy(sampleAnnotation))
        annot['annotation']['name'] = 'First Change'
        annot = Annotation().save(annot)
        annot['annotation']['name'] = 'Second Change'
        annot = Annotation().save(annot)
        assert len(list(Annotation().versionList(annot['_id'], user=admin))) == 1
        assert len(list(Annotation().versionList(str(annot['_id']), user=admin))) == 1
        assert len(list(Annotation().versionList(str(annot['_id']), force=True))) == 1
        assert len(list(Annotation().versionList(annot['_id'], user=user))) == 0

        # Test with history
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        annot = Annotation().createAnnotation(item, admin, copy.deepcopy(sampleAnnotation))
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
        assert len(list(Annotation().versionList(annot['_id'], user=admin))) == 3
        assert len(list(Annotation().versionList(annot['_id'], user=user))) == 0
        assert len(list(Annotation().versionList(annot['_id'], user=admin, offset=1))) == 2
        assert len(list(Annotation().versionList(annot['_id'], user=admin, offset=1, limit=1))) == 1

    def testGetVersion(self, user, admin):
        privateFolder = utilities.namedFolder(admin, 'Private')
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', admin, privateFolder)
        annot = Annotation().createAnnotation(item, admin, copy.deepcopy(sampleAnnotation))
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
        versions = list(Annotation().versionList(annot['_id'], user=admin))

        with pytest.raises(AccessException):
            Annotation().getVersion(annot['_id'], versions[0]['_version'], user=user)
        assert len(Annotation().getVersion(
            annot['_id'],
            versions[0]['_version'],
            user=admin)['annotation']['elements']) == 3
        assert len(Annotation().getVersion(
            annot['_id'],
            versions[1]['_version'],
            user=admin)['annotation']['elements']) == 4
        assert len(Annotation().getVersion(
            annot['_id'],
            versions[2]['_version'],
            user=admin)['annotation']['elements']) == 1
        # We can get a version by its own id
        assert len(Annotation().getVersion(
            str(versions[1]['_id']),
            versions[1]['_version'],
            user=admin)['annotation']['elements']) == 4
        # Asking for an invalid version gets us None
        assert Annotation().getVersion(
            annot['_id'],
            versions[0]['_version'] + 1,
            user=admin) is None

    def testRevertVersion(self, admin):
        privateFolder = utilities.namedFolder(admin, 'Private')
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', admin, privateFolder)
        annot = Annotation().createAnnotation(item, admin, copy.deepcopy(sampleAnnotation))
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
        versions = list(Annotation().versionList(annot['_id'], user=admin))
        assert Annotation().revertVersion(
            annot['_id'], versions[0]['_version'] + 1, user=admin) is None
        assert len(Annotation().revertVersion(
            annot['_id'], force=True)['annotation']['elements']) == 4
        assert len(Annotation().revertVersion(
            annot['_id'], force=True)['annotation']['elements']) == 3
        assert len(Annotation().revertVersion(
            annot['_id'], versions[2]['_version'], force=True)['annotation']['elements']) == 1
        Annotation().remove(annot)
        assert len(Annotation().revertVersion(
            annot['_id'], user=admin)['annotation']['elements']) == 1

    def testAnnotationsAfterCopyItem(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        Annotation().createAnnotation(item, admin, sampleAnnotation)
        resp = server.request(
            '/annotation', user=admin, params={'itemId': item['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        resp = server.request(
            '/item/%s/copy' % item['_id'], method='POST', user=admin)
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation', user=admin, params={'itemId': resp.json['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        resp = server.request(
            '/item/%s/copy' % item['_id'], method='POST', user=admin,
            params={'copyAnnotations': 'true'})
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation', user=admin, params={'itemId': resp.json['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        resp = server.request(
            '/item/%s/copy' % item['_id'], method='POST', user=admin,
            params={'copyAnnotations': 'false'})
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation', user=admin, params={'itemId': resp.json['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 0
        resp = server.request(
            '/item/%s/copy' % item['_id'], method='POST', user=admin,
            params={'copyAnnotations': True})
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation', user=admin, params={'itemId': resp.json['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1


@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationElement(object):
    def testInitialize(self):
        # initialize should be called as we fetch the model
        assert Annotationelement().name == 'annotationelement'

    def testGetNextVersionValue(self):
        val1 = Annotationelement().getNextVersionValue()
        val2 = Annotationelement().getNextVersionValue()
        assert val2 > val1
        Annotationelement().versionId = None
        val3 = Annotationelement().getNextVersionValue()
        assert val3 > val2

    def testBoundingBox(self):
        bbox = Annotationelement()._boundingBox({'points': [[1, -2, 3], [-4, 5, -6], [7, -8, 9]]})
        assert bbox == {
            'lowx': -4, 'lowy': -8, 'lowz': -6,
            'highx': 7, 'highy': 5, 'highz': 9,
            'details': 3,
            'size': ((7 + 4)**2 + (8 + 5)**2)**0.5}
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3]})
        assert bbox == {
            'lowx': 0.5, 'lowy': -2.5, 'lowz': 3,
            'highx': 1.5, 'highy': -1.5, 'highz': 3,
            'details': 1,
            'size': 2**0.5}
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3], 'radius': 4})
        assert bbox == {
            'lowx': -3, 'lowy': -6, 'lowz': 3,
            'highx': 5, 'highy': 2, 'highz': 3,
            'details': 4,
            'size': 8 * 2**0.5}
        bbox = Annotationelement()._boundingBox({'center': [1, -2, 3], 'width': 2, 'height': 4})
        assert bbox == {
            'lowx': 0, 'lowy': -4, 'lowz': 3,
            'highx': 2, 'highy': 0, 'highz': 3,
            'details': 4,
            'size': (2**2 + 4**2)**0.5}
        bbox = Annotationelement()._boundingBox({
            'center': [1, -2, 3],
            'width': 2, 'height': 4,
            'rotation': math.pi * 0.25})
        assert bbox['size'] == pytest.approx(4, 1.0e-4)

    def testGetElements(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        largeSample = makeLargeSampleAnnotation()
        # Use a copy of largeSample so we don't just have a referecne to it
        annot = Annotation().createAnnotation(item, admin, largeSample.copy())
        # Clear existing element data, the get elements
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot)
        assert '_elementQuery' in annot
        assert len(annot['annotation']['elements']) == len(largeSample['elements'])  # 7707
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {'limit': 100})
        assert '_elementQuery' in annot
        assert annot['_elementQuery']['count'] == len(largeSample['elements'])
        assert annot['_elementQuery']['returned'] == 100
        assert len(annot['annotation']['elements']) == 100
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500})
        assert len(annot['annotation']['elements']) == 157
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'left': 3000, 'right': 4000, 'top': 4500, 'bottom': 6500,
            'minimumSize': 16})
        assert len(annot['annotation']['elements']) == 39
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {'maxDetails': 300})
        assert len(annot['annotation']['elements']) == 75
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': -1})
        elements = annot['annotation']['elements']
        assert (elements[0]['width'] * elements[0]['height'] >
                elements[-1]['width'] * elements[-1]['height'])
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {
            'maxDetails': 300, 'sort': 'size', 'sortdir': 1})
        elements = annot['annotation']['elements']
        elements = annot['annotation']['elements']
        assert (elements[0]['width'] * elements[0]['height'] <
                elements[-1]['width'] * elements[-1]['height'])

    def testRemoveWithQuery(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert len(Annotation().load(
            annot['_id'], user=admin)['annotation']['elements']) == 1
        Annotationelement().removeWithQuery({'annotationId': annot['_id']})
        assert len(Annotation().load(
            annot['_id'], user=admin)['annotation']['elements']) == 0

    def testRemoveElements(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        assert len(Annotation().load(
            annot['_id'], user=admin)['annotation']['elements']) == 1
        Annotationelement().removeElements(annot)
        assert len(Annotation().load(
            annot['_id'], user=admin)['annotation']['elements']) == 0

    def testAnnotationGroup(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
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

        annot = Annotation().createAnnotation(item, admin, annotationWithGroup)
        result = Annotation().load(annot['_id'], user=admin)
        assert result['annotation']['elements'][0]['group'] == 'a'

    #  Add tests for:
    # removeOldElements
    # updateElements


@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationRest(object):
    def testGetAnnotationSchema(self, server):
        resp = server.request('/annotation/schema')
        assert utilities.respStatus(resp) == 200
        assert '$schema' in resp.json

    def testGetAnnotation(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annotId = str(annot['_id'])
        resp = server.request(path='/annotation/%s' % annotId, user=admin)
        assert utilities.respStatus(resp) == 200
        assert (resp.json['annotation']['elements'][0]['center'] ==
                annot['annotation']['elements'][0]['center'])
        largeSample = makeLargeSampleAnnotation()
        annot = Annotation().createAnnotation(item, admin, largeSample)
        annotId = str(annot['_id'])
        resp = server.request(path='/annotation/%s' % annotId, user=admin)
        assert utilities.respStatus(resp) == 200
        assert (len(resp.json['annotation']['elements']) ==
                len(largeSample['elements']))  # 7707
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'limit': 100,
            })
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 100
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'left': 3000,
                'right': 4000,
                'top': 4500,
                'bottom': 6500,
            })
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 157
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'left': 3000,
                'right': 4000,
                'top': 4500,
                'bottom': 6500,
                'minimumSize': 16,
            })
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 39
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'maxDetails': 300,
            })
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 75
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'maxDetails': 300,
                'sort': 'size',
                'sortdir': -1,
            })
        assert utilities.respStatus(resp) == 200
        elements = resp.json['annotation']['elements']
        assert (elements[0]['width'] * elements[0]['height'] >
                elements[-1]['width'] * elements[-1]['height'])
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin, params={
                'maxDetails': 300,
                'sort': 'size',
                'sortdir': 1,
            })
        assert utilities.respStatus(resp) == 200
        elements = resp.json['annotation']['elements']
        assert (elements[0]['width'] * elements[0]['height'] <
                elements[-1]['width'] * elements[-1]['height'])

    def testAnnotationCopy(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create annotation on an item
        itemSrc = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(itemSrc, admin, sampleAnnotation)
        assert Annotation().load(annot['_id'], user=admin) is not None

        # Create a new item
        itemDest = Item().createItem('sample', admin, publicFolder)

        # Copy the annotation from one item to an other
        resp = server.request(
            path='/annotation/{}/copy'.format(annot['_id']),
            method='POST',
            user=admin,
            params={
                'itemId': itemDest.get('_id')
            }
        )
        assert utilities.respStatus(resp) == 200
        itemDest = Item().load(itemDest.get('_id'), level=AccessType.READ)

        # Check if the annotation is in the destination item
        resp = server.request(
            path='/annotation',
            method='GET',
            user=admin,
            params={
                'itemId': itemDest.get('_id'),
                'name': 'sample'
            }
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json is not None

    def testItemAnnotationEndpoints(self, server, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create two annotations on an item
        itemSrc = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(itemSrc, admin, sampleAnnotation)
        annot = Annotation().setPublic(annot, False, True)
        Annotation().createAnnotation(itemSrc, admin, sampleAnnotationEmpty)
        # Get all annotations for that item as the user
        resp = server.request(
            path='/annotation/item/{}'.format(itemSrc['_id']),
            user=user
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        assert len(resp.json[0]['annotation']['elements']) == 0

        # Get all annotations for that item as the admin
        resp = server.request(
            path='/annotation/item/{}'.format(itemSrc['_id']),
            user=admin
        )
        assert utilities.respStatus(resp) == 200
        annotList = resp.json
        assert len(annotList) == 2
        assert (annotList[0]['annotation']['elements'][0]['center'] ==
                annot['annotation']['elements'][0]['center'])
        assert len(annotList[1]['annotation']['elements']) == 0

        # Create a new item
        itemDest = Item().createItem('sample', admin, publicFolder)

        # Set the annotations on the new item
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps(annotList)
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == 2

        # Check if the annotations are in the destination item
        resp = server.request(
            path='/annotation',
            method='GET',
            user=admin,
            params={
                'itemId': itemDest.get('_id'),
                'name': 'sample'
            }
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json is not None

        # Check failure conditions
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps(['not an object'])
        )
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps([{'key': 'not an annotation'}])
        )
        assert utilities.respStatus(resp) == 400

    def testDeleteAnnotation(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annotId = str(annot['_id'])
        assert Annotation().load(annot['_id'], user=admin) is not None
        resp = server.request(path='/annotation/%s' % annotId, user=admin, method='DELETE')
        assert utilities.respStatus(resp) == 200
        assert Annotation().load(annot['_id']) is None

    def testFindAnnotatedImages(self, server, user, admin, fsAssetstore):

        def create_annotation(item, user):
            return str(Annotation().createAnnotation(item, user, sampleAnnotation)['_id'])

        def upload(name, user=user, private=False):
            file = utilities.uploadExternalFile(
                'data/sample_image.ptif.sha512', admin, fsAssetstore, name=name)
            item = Item().load(file['itemId'], level=AccessType.READ, user=admin)

            create_annotation(item, user)
            create_annotation(item, user)
            create_annotation(item, admin)

            return str(item['_id'])

        item1 = upload('image1-abcd.ptif', admin)
        item2 = upload(u'Образец Картина.ptif')
        item3 = upload('image3-ABCD.ptif')
        item4 = upload('image3-ijkl.ptif', user, True)

        # test default search
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item4, item3, item2 == item1]

        # test filtering by user
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'creatorId': user['_id']
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item4, item3 == item2]

        # test getting annotations without admin access
        resp = server.request('/annotation/images', user=user, params={
            'limit': 100
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item3, item2 == item1]

        # test sort direction
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'sortdir': 1
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item1, item2, item3 == item4]

        # test pagination
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 1
        })
        assert utilities.respStatus(resp) == 200
        assert resp.json[0]['_id'] == item4

        resp = server.request('/annotation/images', user=admin, params={
            'limit': 1,
            'offset': 3
        })
        assert utilities.respStatus(resp) == 200
        assert resp.json[0]['_id'] == item1

        # test filtering by image name
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': 'image3-aBcd.ptif'
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids == [item3]

        # test filtering by image name substring
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': 'aBc'
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item3 == item1]

        # test filtering by image name with unicode
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': u'Картина'
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids == [item2]

    def testCreateAnnotation(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        itemId = str(item['_id'])

        resp = server.request(
            '/annotation', method='POST', user=admin,
            params={'itemId': itemId}, type='application/json',
            body=json.dumps(sampleAnnotation))
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation', method='POST', user=admin,
            params={'itemId': itemId}, type='application/json', body='badJSON')
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            '/annotation', method='POST', user=admin,
            params={'itemId': itemId}, type='application/json',
            body=json.dumps({'key': 'not an annotation'}))
        assert utilities.respStatus(resp) == 400

    def testUpdateAnnotation(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        import sys
        sys.stderr.write('%r\n' % [annot])  # ##DWM::
        sys.stderr.write('%r\n' % [sampleAnnotation])
        resp = server.request(path='/annotation/%s' % annot['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        annot = resp.json
        annot['annotation']['elements'].extend([
            {'type': 'point', 'center': [20.0, 25.0, 0]},
            {'type': 'point', 'center': [10.0, 24.0, 0]},
            {'type': 'point', 'center': [25.5, 23.0, 0]},
        ])
        resp = server.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=admin,
            type='application/json', body=json.dumps(annot['annotation']))
        assert utilities.respStatus(resp) == 200
        assert resp.json['annotation']['name'] == 'sample'
        assert len(resp.json['annotation']['elements']) == 4
        # Test update without elements
        annotNoElem = copy.deepcopy(annot)
        del annotNoElem['annotation']['elements']
        annotNoElem['annotation']['name'] = 'newname'
        resp = server.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=admin,
            type='application/json', body=json.dumps(annotNoElem['annotation']))
        assert utilities.respStatus(resp) == 200
        assert resp.json['annotation']['name'] == 'newname'
        assert 'elements' not in resp.json['annotation']
        # Test with passed item id
        item2 = Item().createItem('sample2', admin, publicFolder)
        resp = server.request(
            '/annotation/%s' % annot['_id'], method='PUT', user=admin,
            params={'itemId': item2['_id']}, type='application/json',
            body=json.dumps(annot['annotation']))
        assert utilities.respStatus(resp) == 200
        assert resp.json['itemId'] == str(item2['_id'])

    def testAnnotationAccessControlEndpoints(self, server, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # Try to get ACL's as a user
        resp = server.request('/annotation/%s/access' % annot['_id'], user=user)
        assert utilities.respStatus(resp) == 403

        # Get the ACL's as an admin
        resp = server.request('/annotation/%s/access' % annot['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        access = dict(**resp.json)

        # Set the public flag to false and try to read as a user
        resp = server.request(
            '/annotation/%s/access' % annot['_id'],
            method='PUT',
            user=admin,
            params={
                'access': json.dumps(access),
                'public': False
            }
        )
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation/%s' % annot['_id'],
            user=user
        )
        assert utilities.respStatus(resp) == 403
        # The admin should still be able to get the annotation with elements
        resp = server.request(
            '/annotation/%s' % annot['_id'],
            user=admin
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 1

        # Give the user admin access
        access['users'].append({
            'login': user['login'],
            'flags': [],
            'id': str(user['_id']),
            'level': AccessType.ADMIN
        })
        resp = server.request(
            '/annotation/%s/access' % annot['_id'],
            method='PUT',
            user=admin,
            params={
                'access': json.dumps(access)
            }
        )
        assert utilities.respStatus(resp) == 200

        # Get the ACL's as a user
        resp = server.request('/annotation/%s/access' % annot['_id'], user=user)
        assert utilities.respStatus(resp) == 200

    def testAnnotationHistoryEndpoints(self, server, user, admin):
        privateFolder = utilities.namedFolder(admin, 'Private')
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        item = Item().createItem('sample', admin, privateFolder)
        # Create an annotation with some history
        annot = Annotation().createAnnotation(item, admin, copy.deepcopy(sampleAnnotation))
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
        resp = server.request('/annotation/%s/history' % annot['_id'], user=user)
        assert utilities.respStatus(resp) == 200
        assert resp.json == []
        resp = server.request('/annotation/%s/history' % annot['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 3
        versions = resp.json

        # Test getting a specific version
        resp = server.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[1]['_version']), user=user)
        assert utilities.respStatus(resp) == 403
        resp = server.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[1]['_version']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['_annotationId'] == str(annot['_id'])
        assert len(resp.json['annotation']['elements']) == 4
        resp = server.request('/annotation/%s/history/%s' % (
            annot['_id'], versions[0]['_version'] + 1), user=admin)
        assert utilities.respStatus(resp) == 400

        # Test revert
        resp = server.request('/annotation/%s/history/revert' % (
            annot['_id']), method='PUT', user=user)
        assert utilities.respStatus(resp) == 403
        resp = server.request(
            '/annotation/%s/history/revert' % (annot['_id']),
            method='PUT', user=admin, params={
                'version': versions[0]['_version'] + 1
            })
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            '/annotation/%s/history/revert' % (annot['_id']),
            method='PUT', user=admin, params={
                'version': versions[1]['_version']
            })
        assert utilities.respStatus(resp) == 200
        loaded = Annotation().load(annot['_id'], user=admin)
        assert len(loaded['annotation']['elements']) == 4

    #  Add tests for:
    # find


@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationElementGroups(object):
    def makeAnnot(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')

        self.item = Item().createItem('sample', admin, publicFolder)
        annotationModel = Annotation()

        self.noGroups = annotationModel.createAnnotation(
            self.item, admin,
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
            self.item, admin,
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
            self.item, admin,
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

    def testFindAnnotations(self, server, admin):
        self.makeAnnot(admin)
        resp = server.request('/annotation', user=admin, params={'itemId': self.item['_id']})
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 3
        for annot in resp.json:
            if annot['_id'] == str(self.noGroups['_id']):
                assert annot['groups'] == [None]
            elif annot['_id'] == str(self.notMigrated['_id']):
                assert annot['groups'] == ['a', 'b']
            elif annot['_id'] == str(self.hasGroups['_id']):
                assert annot['groups'] == ['a', 'c', None]
            else:
                raise Exception('Unexpected annot id')

    def testLoadAnnotation(self, server, admin):
        self.makeAnnot(admin)
        resp = server.request('/annotation/%s' % str(self.hasGroups['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['groups'] == ['a', 'c', None]

    def testCreateAnnotation(self, server, admin):
        self.makeAnnot(admin)
        annot = {
            'name': 'created',
            'elements': [{
                'type': 'rectangle',
                'center': [20.0, 25.0, 0],
                'width': 14.0,
                'height': 15.0,
                'group': 'a'
            }]
        }
        resp = server.request(
            '/annotation',
            user=admin,
            method='POST',
            params={'itemId': str(self.item['_id'])},
            type='application/json',
            body=json.dumps(annot)
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request('/annotation/%s' % resp.json['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['groups'] == ['a']

    def testUpdateAnnotation(self, server, admin):
        self.makeAnnot(admin)
        annot = {
            'name': 'created',
            'elements': [{
                'type': 'rectangle',
                'center': [20.0, 25.0, 0],
                'width': 14.0,
                'height': 15.0,
                'group': 'd'
            }]
        }
        resp = server.request(
            '/annotation/%s' % str(self.hasGroups['_id']),
            user=admin,
            method='PUT',
            type='application/json',
            body=json.dumps(annot)
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request('/annotation/%s' % resp.json['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['groups'] == ['d']


@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationAccessMigration(object):
    def testMigrateAnnotationAccessControl(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # assert ACL's work
        with pytest.raises(AccessException):
            Annotation().load(annot['_id'], user=user, level=AccessType.WRITE)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        Annotation().save(annot)

        # load the annotation and assert access properties were added
        annot = Annotation().load(annot['_id'], force=True)

        assert annot['access'] == publicFolder['access']
        assert annot['public'] is True

    def testLoadAnnotationWithCoreKWArgs(self, admin):
        # try to load a non-existing annotation
        with pytest.raises(ValidationException):
            Annotation().load(ObjectId(), user=admin, exc=True)

    def testMigrateAnnotationAccessControlNoItemError(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        annot['itemId'] = ObjectId()

        Annotation().save(annot)
        with mock.patch('girder_large_image_annotation.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        assert 'access' not in annot

    def testMigrateAnnotationAccessControlNoFolderError(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        Annotation().save(annot)

        # save an invalid folder id to the item
        item['folderId'] = ObjectId()
        Item().save(item)

        with mock.patch('girder_large_image_annotation.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        assert 'access' not in annot

    def testMigrateAnnotationAccessControlNoUserError(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        annot['creatorId'] = ObjectId()
        Annotation().save(annot)

        with mock.patch('girder_large_image_annotation.models.annotation.logger') as logger:
            annot = Annotation().load(annot['_id'], force=True)
            logger.warning.assert_called_once()

        assert 'access' not in annot
