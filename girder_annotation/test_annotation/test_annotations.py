import copy
import math
import random
from unittest import mock

import jsonschema
import pytest

from . import girder_utilities as utilities

pytestmark = pytest.mark.girder

try:
    from bson import ObjectId
    from girder_large_image import constants
    from girder_large_image_annotation.models import annotation
    from girder_large_image_annotation.models.annotation import Annotation
    from girder_large_image_annotation.models.annotationelement import Annotationelement

    from girder.constants import AccessType
    from girder.exceptions import AccessException, ValidationException
    from girder.models.folder import Folder
    from girder.models.group import Group
    from girder.models.item import Item
    from girder.models.setting import Setting
except ImportError:
    # Make it easier to test without girder
    pass

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
    }],
}
sampleAnnotationWithMetadata = {
    'name': 'sample',
    'attributes': {
        'key1': 'value1',
    },
    'elements': [{
        'type': 'rectangle',
        'center': [20.0, 25.0, 0],
        'width': 14.0,
        'height': 15.0,
    }],
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


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotation:
    def testAnnotationSchema(self):
        schema = annotation.AnnotationSchema
        assert schema.annotationSchema is not None
        assert schema.annotationElementSchema is not None

    def testAnnotationSchemaIsValid(self):
        schema = annotation.AnnotationSchema.annotationSchema
        assert jsonschema.Draft6Validator.check_schema(schema) is None

    def testAnnotationCreate(self, admin):
        item = Item().createItem('sample', admin, utilities.namedFolder(admin, 'Public'))
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'rectangle',
                'center': [10, 20, 0],
                'width': 5,
                'height': 10,
            }],
        }
        result = Annotation().createAnnotation(item, admin, annotation)
        assert '_id' in result
        annotId = result['_id']
        result = Annotation().load(annotId, user=admin)
        assert len(result['annotation']['elements']) == 1

    def testSimilarElementStructure(self, db):

        def ses(a, b):
            try:
                return Annotation()._similarElementStructure(a, b)
            except TypeError:
                return False

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
        with pytest.raises(Exception, match='Invalid ObjectId'):
            Annotation().load('nosuchid')
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
        assert len(list(Annotation().versionList(annot['_id']))) == 1
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
        assert versions[1]['_id'] != loaded['_id']
        saved3 = Annotation().save(versions[1])
        assert saved3['_id'] == loaded['_id']

    def testUpdateAnnotaton(self, user, admin):
        publicFolder = utilities.namedFolder(user, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annot = Annotation().load(annot['_id'], region={'sort': 'size'}, user=admin)
        saved = Annotation().updateAnnotation(annot, updateUser=user)
        assert saved['updatedId'] == user['_id']

    def testRemove(self, db, admin):
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

    def testValidate(self, db):
        annot = copy.deepcopy(sampleAnnotation)
        doc = {'annotation': annot}
        assert Annotation().validate(doc) is not None
        annot['elements'][0]['id'] = ObjectId('012345678901234567890123')
        annot['elements'].append(annot['elements'][0])
        with pytest.raises(ValidationException, match='not unique'):
            Annotation().validate(doc)
        annot['elements'][1] = copy.deepcopy(annot['elements'][0])
        annot['elements'][1]['id'] = ObjectId('012345678901234567890124')
        assert Annotation().validate(doc) is not None

    def testVersionList(self, db, user, admin):
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

    def testPermissions(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        group = Group().createGroup('Delete Me', admin)
        annot['access']['groups'].append({'id': str(group['_id']), 'level': 0, 'flags': []})
        Annotation().save(annot)
        annot = Annotation().load(annot['_id'], getElements=False, force=True)
        acl = Annotation().getFullAccessList(annot)
        assert len(annot['access']['groups']) == 1
        assert len(acl['groups']) == 1
        # If you remove the group using the remove method, the acls will be
        # pruned.  If you use removeWithQuery, they won't be, and getting the
        # access list will cause the access list to be resaved.
        Group().removeWithQuery({'_id': group['_id']})
        acl = Annotation().getFullAccessList(annot)
        assert len(acl['groups']) == 0
        assert len(annot['access']['groups']) == 0
        check = Annotation().load(annot['_id'], force=True)
        assert len(check['annotation']['elements']) > 0

    def testHeatmapAnnotation(self, db, admin, fsAssetstore):
        item = Item().createItem('sample', admin, utilities.namedFolder(admin, 'Public'))
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'heatmap',
                'points': [[random.random() for _ in range(4)] for _ in range(10240)],
            }],
        }
        annot = Annotation().createAnnotation(item, admin, annotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        result = Annotation().remove(annot)
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        assert result.deleted_count == 1
        assert Annotation().load(annot['_id'], user=admin) is None

    def testGridHeatmapAnnotation(self, db, admin, fsAssetstore):
        item = Item().createItem('sample', admin, utilities.namedFolder(admin, 'Public'))
        annotation = {
            'name': 'testAnnotation',
            'elements': [{
                'type': 'griddata',
                'interpretation': 'heatmap',
                'origin': [30, 40, 50],
                'dx': 3,
                'dy': 4,
                'gridWidth': 128,
                'values': [random.random() for _ in range(10240)],
            }],
        }
        annot = Annotation().createAnnotation(item, admin, annotation)
        assert Annotation().load(annot['_id'], user=admin) is not None
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, False)
        result = Annotation().remove(annot)
        Setting().set(constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY, True)
        assert result.deleted_count == 1
        assert Annotation().load(annot['_id'], user=admin) is None


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationElement:
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

    def testOverlayBounds(self, server, admin, fsAssetstore):
        file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
        itemId = str(file['itemId'])

        # test no transform
        lowx, highx, lowy, highy = Annotationelement()._overlayBounds({
            'type': 'image', 'girderId': itemId,
        })
        assert lowx == 0
        assert lowy == 0
        assert highx == 58368
        assert highy == 12288

        # test offset
        lowx, highx, lowy, highy = Annotationelement()._overlayBounds({
            'type': 'image', 'girderId': itemId,
            'transform': {'xoffset': 500, 'yoffset': 1000},
        })
        assert lowx == 500
        assert lowy == 1000
        assert highx == 58868
        assert highy == 13288

        # test affine matrix, scale to 50%
        lowx, highx, lowy, highy = Annotationelement()._overlayBounds({
            'type': 'image', 'girderId': itemId,
            'transform': {
                'matrix': [[0.5, 0], [0, 0.5]],
            },
        })
        assert lowx == 0
        assert lowy == 0
        assert highx == 58368 / 2
        assert highy == 12288 / 2

        # test transform and scaling
        lowx, highx, lowy, highy = Annotationelement()._overlayBounds({
            'type': 'image', 'girderId': itemId,
            'transform': {
                'xoffset': 500,
                'yoffset': 1000,
                'matrix': [[0.5, 0], [0, 0.5]],
            },
        })
        assert lowx == 500
        assert lowy == 1000
        assert highx == (58368 / 2) + 500
        assert highy == (12288 / 2) + 1000

    def testOverlayBoundingBox(self, server, admin, fsAssetstore):
        file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
        itemId = str(file['itemId'])
        bbox = Annotationelement()._boundingBox(
            {'type': 'image', 'girderId': itemId})
        assert bbox == {
            'lowx': 0, 'lowy': 0, 'lowz': 0,
            'highx': 58368, 'highy': 12288, 'highz': 0,
            'details': 1,
            'size': (58368**2 + 12288**2)**0.5}

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
        # Use a copy of largeSample so we don't just have a reference to it
        annot = Annotation().createAnnotation(item, admin, largeSample.copy())
        # Clear existing element data, the get elements
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot)
        assert '_elementQuery' in annot
        assert len(annot['annotation']['elements']) == len(largeSample['elements'])  # 7707
        assert 'centroids' not in annot['_elementQuery']
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
        assert (elements[0]['width'] * elements[0]['height'] <
                elements[-1]['width'] * elements[-1]['height'])

    def testGetElementsByCentroids(self, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        largeSample = makeLargeSampleAnnotation()
        # Use a copy of largeSample so we don't just have a reference to it
        annot = Annotation().createAnnotation(item, admin, largeSample.copy())
        # Clear existing element data, the get elements
        annot.pop('elements', None)
        annot.pop('_elementQuery', None)
        Annotationelement().getElements(annot, {'centroids': True})
        assert '_elementQuery' in annot
        assert len(annot['annotation']['elements']) == len(largeSample['elements'])  # 7707
        assert annot['_elementQuery']['centroids'] is True
        assert 'props' in annot['_elementQuery']
        elements = annot['annotation']['elements']
        assert isinstance(elements[0], list)

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
            'group': 'a',
        }, {
            'type': 'rectangle',
            'center': [40.0, 15.0, 0],
            'width': 5.0,
            'height': 5.0,
        }]
        annotationWithGroup = {
            'name': 'groups',
            'elements': elements,
        }

        annot = Annotation().createAnnotation(item, admin, annotationWithGroup)
        result = Annotation().load(annot['_id'], user=admin)
        assert result['annotation']['elements'][0]['group'] == 'a'

    #  Add tests for:
    # removeOldElements
    # updateElements


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationAccessMigration:
    def testMigrateAnnotationAccessControl(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # assert ACLs work
        with pytest.raises(AccessException):
            Annotation().load(annot['_id'], user=user, level=AccessType.WRITE)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        Annotation().save(annot)

        Annotation()._migrateDatabase()

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
            Annotation()._migrateDatabase()
            logger.debug.assert_called_once()
        annot = Annotation().load(annot['_id'], force=True)
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
            Annotation()._migrateDatabase()
            logger.debug.assert_called_once()
        annot = Annotation().load(annot['_id'], force=True)
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
            Annotation()._migrateDatabase()
            logger.debug.assert_called_once()
        annot = Annotation().load(annot['_id'], force=True)
        assert 'access' not in annot

    def testMigrateAnnotationAccessControlNullUserError(self, user, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create an annotation
        item = Item().createItem('userItem', user, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)

        # remove the access control properties and save back to the database
        del annot['access']
        del annot['public']
        annot['creatorId'] = None
        Annotation().save(annot)
        with mock.patch('girder_large_image_annotation.models.annotation.logger') as logger:
            Annotation()._migrateDatabase()
            logger.debug.assert_called_once()
        annot = Annotation().load(annot['_id'], force=True)
        assert 'access' not in annot


def testPlottableDataAccess(admin):
    import girder_large_image_annotation

    exampleData = {
        'ex1_nucleus_radius': 4.5,
        'ex1_nucleus_circularity': 0.9,
        'ex2_nuclei_radii': [4.5, 5.5, 5.1],
        'ex2_nuclei_circularity': [0.9, 0.86, 0.92],
        'ex3_nucleus': {
            'radius': 4.5,
            'circularity': 0.9,
        },
        'ex4_nucleii': {
            'radii': [4.5, 5.5, 5.1],
            'circularity': [0.9, 0.86, 0.92],
        },
        'ex5_nucleus': [{
            'radius': 4.5,
            'circularity': 0.9,
        }, {
            'radius': 5.5,
            'circularity': 0.86,
        }, {
            'radius': 5.1,
            'circularity': 0.92,
        }],
    }
    item = Item().createItem('sample', admin, utilities.namedFolder(admin, 'Public'))
    item = Item().setMetadata(item, exampleData)
    plottable = girder_large_image_annotation.utils.PlottableItemData(admin, item)
    col = plottable.columns
    # Also contains item id, name, and description
    assert len(col) == 15

    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 12
    assert len(data['data']) == 3


def testPlottableDataMultipleItems(admin):
    import girder_large_image_annotation

    folder = utilities.namedFolder(admin, 'Public')
    item1 = Item().createItem('sample1', admin, folder)
    item1 = Item().setMetadata(item1, {
        'nucleii': {
            'circularity': 0.9,
        },
    })
    item2 = Item().createItem('sample2', admin, folder)
    item2 = Item().setMetadata(item2, {
        'nucleii': {
            'circularity': 0.86,
            'extra': True,
        },
    })
    Folder().setMetadata(folder, {
        'nucleii': {
            'image_name': ['sample1', str(item2['_id'])],
            'radii': [4.5, 5.5],
        },
    })
    annot1a = Annotation().createAnnotation(item1, admin, {
        'name': 'sampleA',
        'attributes': {
            'nuclei': {
                'category': 'catA',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [20.0, 25.0, 0],
            'width': 14.0,
            'height': 15.0,
            'user': {'nuclei': {'quality': 1.1}},
        }, {
            'type': 'rectangle',
            'center': [30.0, 25.0, 0],
            'width': 11.0,
            'height': 12.0,
            'user': {'nuclei': {'quality': 1.2}},
        }]})
    Annotation().createAnnotation(item1, admin, {
        'name': 'sampleB',
        'attributes': {
            'nuclei': {
                'category': 'catB',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [20.0, 35.0, 0],
            'width': 13.0,
            'height': 16.0,
            'user': {'nuclei': {'quality': 1.3}},
        }, {
            'type': 'rectangle',
            'center': [30.0, 35.0, 0],
            'width': 17.0,
            'height': 18.0,
            'user': {'nuclei': {'quality': 1.4}},
        }]})
    annot1c = Annotation().createAnnotation(item1, admin, {
        'name': 'sampleC',
        'attributes': {
            'nuclei': {
                'category': 'catC',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [20.0, 45.0, 0],
            'width': 1.0,
            'height': 2.0,
            'user': {'nuclei': {'quality': 1.5}},
        }, {
            'type': 'rectangle',
            'center': [30.0, 45.0, 0],
            'width': 3.0,
            'height': 4.0,
            'user': {'nuclei': {'quality': 1.6}},
        }]})
    Annotation().createAnnotation(item2, admin, {
        'name': 'sampleA',
        'attributes': {
            'nuclei': {
                'category': 'catA',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [21.0, 25.0, 0],
            'width': 5.0,
            'height': 6.0,
            'user': {'nuclei': {'quality': 1.7}},
        }, {
            'type': 'rectangle',
            'center': [31.0, 25.0, 0],
            'width': 7.0,
            'height': 8.0,
            'user': {'nuclei': {'quality': 1.8}},
        }]})
    Annotation().createAnnotation(item2, admin, {
        'name': 'sampleB',
        'attributes': {
            'nuclei': {
                'category': 'catB',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [21.0, 35.0, 0],
            'width': 9.0,
            'height': 10.0,
            'user': {'nuclei': {'quality': 1.9}},
        }, {
            'type': 'rectangle',
            'center': [31.0, 35.0, 0],
            'width': 19.0,
            'height': 20.0,
            'user': {'nuclei': {'quality': 2.0}},
        }]})
    Annotation().createAnnotation(item2, admin, {
        'name': 'sampleD',
        'attributes': {
            'nuclei': {
                'category': 'catD',
            },
        },
        'elements': [{
            'type': 'rectangle',
            'center': [21.0, 45.0, 0],
            'width': 21.0,
            'height': 22.0,
            'user': {'nuclei': {'quality': 2.1}},
        }, {
            'type': 'rectangle',
            'center': [31.0, 45.0, 0],
            'width': 23.0,
            'height': 24.0,
            'user': {'nuclei': {'quality': 2.2}},
        }]})

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, sources='item')
    col = plottable.columns
    assert len(col) == 6
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 3
    assert len(data['data']) == 1

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, sources='item', adjacentItems=True)
    col = plottable.columns
    assert len(col) == 6
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 3
    assert len(data['data']) == 2

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, sources='item', adjacentItems='__all__')
    col = plottable.columns
    assert len(col) == 7
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 4
    assert len(data['data']) == 2

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1)
    col = plottable.columns
    assert len(col) == 7
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 4
    assert len(data['data']) == 3

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, adjacentItems=True)
    col = plottable.columns
    assert len(col) == 7
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 4
    assert len(data['data']) == 4

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, annotations=[str(annot1a['_id']), str(annot1c['_id'])])
    col = plottable.columns
    assert len(col) == 17
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 14
    assert len(data['data']) == 6

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, annotations=[str(annot1a['_id']), str(annot1c['_id'])], adjacentItems=True)
    col = plottable.columns
    assert len(col) == 17
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 14
    assert len(data['data']) == 8

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, annotations='__all__')
    col = plottable.columns
    assert len(col) == 17
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 14
    assert len(data['data']) == 8

    plottable = girder_large_image_annotation.utils.PlottableItemData(
        admin, item1, annotations='__all__', adjacentItems=True)
    col = plottable.columns
    assert len(col) == 17
    data = plottable.data([c['key'] for c in col])
    assert len(data['columns']) == 14
    assert len(data['data']) == 12
