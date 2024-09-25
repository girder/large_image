import copy
import json
import struct

import pytest

from . import girder_utilities as utilities
from .test_annotations import (makeLargeSampleAnnotation, sampleAnnotation,
                               sampleAnnotationEmpty,
                               sampleAnnotationWithMetadata)

pytestmark = pytest.mark.girder

try:
    from girder_large_image import constants
    from girder_large_image_annotation.models.annotation import Annotation

    from girder.constants import AccessType
    from girder.models.collection import Collection
    from girder.models.folder import Folder
    from girder.models.item import Item
    from girder.models.setting import Setting
except ImportError:
    # Make it easier to test without girder
    pass


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
class TestLargeImageAnnotationRest:
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

    def testGetAnnotationWithCentroids(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annotId = str(annot['_id'])
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin,
            params={'centroids': 'true'}, isJson=False)
        assert utilities.respStatus(resp) == 200
        result = utilities.getBody(resp, text=False)
        assert b'\x00' in result
        elements = result.split(b'\x00', 1)[1].rsplit(b'\x00', 1)[0]
        data = result.split(b'\x00', 1)[0] + result.rsplit(b'\x00', 1)[1]
        data = json.loads(data.decode())
        assert len(data['_elementQuery']['props']) == 1
        assert len(elements) == 28 * 1
        x, y, r, s = struct.unpack('<fffl', elements[12:28])
        assert x == annot['annotation']['elements'][0]['center'][0]
        assert y == annot['annotation']['elements'][0]['center'][1]
        assert s == 0
        largeSample = makeLargeSampleAnnotation()
        annot = Annotation().createAnnotation(item, admin, largeSample)
        annotId = str(annot['_id'])
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin,
            params={'centroids': 'true'}, isJson=False)
        assert utilities.respStatus(resp) == 200
        result = utilities.getBody(resp, text=False)
        elements = result.split(b'\x00', 1)[1].rsplit(b'\x00', 1)[0]
        assert len(elements) == 28 * len(largeSample['elements'])

    def testGetAnnotationWithBoundingBox(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        item = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(item, admin, sampleAnnotation)
        annotId = str(annot['_id'])
        resp = server.request(
            path='/annotation/%s' % annotId, user=admin)
        assert utilities.respStatus(resp) == 200
        assert 'bbox' not in resp.json['_elementQuery']
        assert '_bbox' not in resp.json['annotation']['elements'][0]

        resp = server.request(
            path='/annotation/%s' % annotId, user=admin,
            params={'bbox': 'true'})
        assert utilities.respStatus(resp) == 200
        assert 'bbox' in resp.json['_elementQuery']
        assert '_bbox' in resp.json['annotation']['elements'][0]

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
                'itemId': itemDest.get('_id'),
            },
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
                'name': 'sample',
            },
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
            user=user,
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 1
        assert len(resp.json[0]['annotation']['elements']) == 0

        # Get all annotations for that item as the admin
        resp = server.request(
            path='/annotation/item/{}'.format(itemSrc['_id']),
            user=admin,
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
            body=json.dumps(annotList),
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
                'name': 'sample',
            },
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json is not None

        # Check failure conditions
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps(['not an object']),
        )
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps([{'key': 'not an annotation'}]),
        )
        assert utilities.respStatus(resp) == 400

        # Delete annotations
        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='DELETE',
            user=None,
        )
        assert utilities.respStatus(resp) == 401

        resp = server.request(
            path='/annotation/item/{}'.format(itemDest['_id']),
            method='DELETE',
            user=admin,
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == 2

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
                'sample_image.ptif', admin, fsAssetstore, name=name)
            item = Item().load(file['itemId'], level=AccessType.READ, user=admin)

            create_annotation(item, user)
            create_annotation(item, user)
            create_annotation(item, admin)

            return str(item['_id'])

        item1 = upload('image1-abcd.ptif', admin)
        item2 = upload('Образец Картина.ptif')
        item3 = upload('image3-ABCD.ptif')
        item4 = upload('image3-ijkl.ptif', user, True)

        # test default search
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item4, item3, item2 == item1]

        # test filtering by user
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'creatorId': user['_id'],
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item4, item3 == item2]

        # test getting annotations without admin access
        resp = server.request('/annotation/images', user=user, params={
            'limit': 100,
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item3, item2 == item1]

        # test sort direction
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'sortdir': 1,
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item1, item2, item3 == item4]

        # test pagination
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 1,
        })
        assert utilities.respStatus(resp) == 200
        assert resp.json[0]['_id'] == item4

        resp = server.request('/annotation/images', user=admin, params={
            'limit': 1,
            'offset': 3,
        })
        assert utilities.respStatus(resp) == 200
        assert resp.json[0]['_id'] == item1

        # test filtering by image name
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': 'image3-aBcd.ptif',
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids == [item3]

        # test filtering by image name substring
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': 'aBc',
        })
        assert utilities.respStatus(resp) == 200
        ids = [image['_id'] for image in resp.json]
        assert ids, [item3 == item1]

        # test filtering by image name with unicode
        resp = server.request('/annotation/images', user=admin, params={
            'limit': 100,
            'imageName': 'Картина',
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
                'public': False,
            },
        )
        assert utilities.respStatus(resp) == 200
        resp = server.request(
            '/annotation/%s' % annot['_id'],
            user=user,
        )
        assert utilities.respStatus(resp) == 403
        # The admin should still be able to get the annotation with elements
        resp = server.request(
            '/annotation/%s' % annot['_id'],
            user=admin,
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['annotation']['elements']) == 1

        # Give the user admin access
        access['users'].append({
            'login': user['login'],
            'flags': [],
            'id': str(user['_id']),
            'level': AccessType.ADMIN,
        })
        resp = server.request(
            '/annotation/%s/access' % annot['_id'],
            method='PUT',
            user=admin,
            params={
                'access': json.dumps(access),
            },
        )
        assert utilities.respStatus(resp) == 200

        # Get the ACL's as a user
        resp = server.request('/annotation/%s/access' % annot['_id'], user=user)
        assert utilities.respStatus(resp) == 200

    @pytest.mark.singular
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
                'version': versions[0]['_version'] + 1,
            })
        assert utilities.respStatus(resp) == 400
        resp = server.request(
            '/annotation/%s/history/revert' % (annot['_id']),
            method='PUT', user=admin, params={
                'version': versions[1]['_version'],
            })
        assert utilities.respStatus(resp) == 200
        loaded = Annotation().load(annot['_id'], user=admin)
        assert len(loaded['annotation']['elements']) == 4

        # Test old
        resp = server.request('/annotation/old', method='GET', user=user)
        assert utilities.respStatus(resp) == 403
        resp = server.request('/annotation/old', method='GET', user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['abandonedVersions'] == 0
        resp = server.request(
            '/annotation/old', method='DELETE', user=admin, params={'versions': -1})
        assert utilities.respStatus(resp) == 400
        assert 'keepInactiveVersions' in resp.json['message']
        resp = server.request(
            '/annotation/old', method='GET', user=admin, params={'age': 0, 'versions': 0})
        assert utilities.respStatus(resp) == 200
        resp = server.request('/annotation/old', method='DELETE', user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['abandonedVersions'] == 0
        resp = server.request('/annotation/old', method='DELETE', user=admin, params={'age': 6})
        assert utilities.respStatus(resp) == 400
        assert 'minAgeInDays' in resp.json['message']

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
class TestLargeImageAnnotationElementGroups:
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
                    'height': 5.0,
                }],
            },
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
                    'group': 'b',
                }, {
                    'type': 'rectangle',
                    'center': [40.0, 15.0, 0],
                    'width': 5.0,
                    'height': 5.0,
                    'group': 'a',
                }],
            },
        )
        annotationModel.collection.update_one(
            {'_id': self.notMigrated['_id']},
            {'$unset': {'groups': ''}},
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
                    'group': 'a',
                }, {
                    'type': 'rectangle',
                    'center': [40.0, 15.0, 0],
                    'width': 5.0,
                    'height': 5.0,
                    'group': 'c',
                }, {
                    'type': 'rectangle',
                    'center': [50.0, 10.0, 0],
                    'width': 5.0,
                    'height': 5.0,
                }],
            },
        )
        annotationModel._migrateDatabase()

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
                msg = 'Unexpected annot id'
                raise Exception(msg)

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
                'group': 'a',
            }],
        }
        resp = server.request(
            '/annotation',
            user=admin,
            method='POST',
            params={'itemId': str(self.item['_id'])},
            type='application/json',
            body=json.dumps(annot),
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
                'group': 'd',
            }],
        }
        resp = server.request(
            '/annotation/%s' % str(self.hasGroups['_id']),
            user=admin,
            method='PUT',
            type='application/json',
            body=json.dumps(annot),
        )
        assert utilities.respStatus(resp) == 200

        resp = server.request('/annotation/%s' % resp.json['_id'], user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['groups'] == ['d']

    def testLoadAnnotationGeoJSON(self, server, admin):
        self.makeAnnot(admin)
        resp = server.request('/annotation/%s/geojson' % str(self.hasGroups['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['type'] == 'FeatureCollection'
        assert len(resp.json['features']) == 3

    def testGeoJSONRoundTrip(self, admin):
        import girder_large_image_annotation

        self.makeAnnot(admin)
        geojson = girder_large_image_annotation.utils.AnnotationGeoJSON(
            self.hasGroups['_id']).geojson
        annot = girder_large_image_annotation.utils.GeoJSONAnnotation(geojson)
        assert annot.elementCount == 3

    def testLoadAnnotationGeoJSONVariety(self, server, admin):
        self.makeAnnot(admin)
        annot = Annotation().createAnnotation(
            self.item, admin,
            {
                'name': 'sample',
                'elements': [{
                    'type': 'rectangle',
                    'center': [20.0, 25.0, 0],
                    'rotation': 0.1,
                    'width': 14.0,
                    'height': 15.0,
                }, {
                    'type': 'circle',
                    'center': [10.3, -40.0, 0],
                    'radius': 5.3,
                    'fillColor': '#0000ff',
                }, {
                    'type': 'ellipse',
                    'center': [10.3, -40.0, 0],
                    'width': 5.3,
                    'height': 17.3,
                    'rotation': 0,
                    'normal': [0, 0, 1.0],
                    'fillColor': 'rgba(0, 255, 0, 1)',
                }, {
                    'type': 'point',
                    'center': [123.3, 144.6, -123],
                }, {
                    'type': 'polyline',
                    'points': [[5, 6, 0], [-17, 6, 0], [56, -45, 6]],
                    'closed': True,
                    'holes': [[[10, 10, 0], [20, 30, 0], [10, 30, 0]]],
                    'fillColor': 'rgba(0, 255, 0, 1)',
                }, {
                    'type': 'polyline',
                    'points': [[7, 8, 0], [17, 6, 0], [27, 9, 0], [37, 14, 0], [46, 8, 0]],
                    'closed': False,
                    'fillColor': 'rgba(0, 255, 0, 1)',
                }],
            },
        )

        resp = server.request('/annotation/%s/geojson' % str(annot['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        assert resp.json['type'] == 'FeatureCollection'
        assert len(resp.json['features']) == 6

        import girder_large_image_annotation
        annot = girder_large_image_annotation.utils.GeoJSONAnnotation(resp.json)
        assert annot.elementCount == 6

        resp = server.request(
            path='/annotation/item/{}'.format(self.item['_id']),
            method='POST',
            user=admin,
            type='application/json',
            body=json.dumps(resp.json),
        )
        assert utilities.respStatus(resp) == 200
        assert resp.json == 1

    def testPlottableEndpoints(self, server, admin):
        publicFolder = utilities.namedFolder(admin, 'Public')
        # create annotation on an item
        itemSrc = Item().createItem('sample', admin, publicFolder)
        annot = Annotation().createAnnotation(itemSrc, admin, sampleAnnotation)

        resp = server.request(
            path=f'/annotation/item/{itemSrc["_id"]}/plot/list',
            method='POST',
            user=admin,
            params={
                'annotations': json.dumps([]),
            },
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) == 2

        resp = server.request(
            path=f'/annotation/item/{itemSrc["_id"]}/plot/list',
            method='POST',
            user=admin,
            params={
                'annotations': json.dumps([str(annot['_id'])]),
            },
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json) >= 5

        resp = server.request(
            path=f'/annotation/item/{itemSrc["_id"]}/plot/data',
            method='POST',
            user=admin,
            params={
                'annotations': json.dumps([]),
                'keys': 'item.name',
                'requiredKeys': 'item.name',
            },
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['columns']) >= 1

        resp = server.request(
            path=f'/annotation/item/{itemSrc["_id"]}/plot/data',
            method='POST',
            user=admin,
            params={
                'annotations': json.dumps([str(annot['_id'])]),
                'keys': 'item.name,bbox.x0',
                'requiredKeys': 'item.name',
            },
        )
        assert utilities.respStatus(resp) == 200
        assert len(resp.json['columns']) >= 2


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
def testMetadataSearch(server, admin, fsAssetstore):
    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    item = Item().load(id=itemId, force=True)
    Item().setMetadata(item, {'key1': 'value1'})
    Annotation().createAnnotation(item, admin, sampleAnnotation)

    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == {'item': []}
    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'key:key1 value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == {'item': []}
    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'key:key2 value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == {'item': []}
    Annotation().createAnnotation(item, admin, sampleAnnotationWithMetadata)
    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert resp.json != {'item': []}
    assert len(resp.json['item']) == 1
    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'key:key1 value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json['item']) == 1
    resp = server.request(
        path='/resource/search', user=admin,
        params={'q': 'key:key2 value', 'mode': 'li_annotation_metadata', 'types': '["item"]'})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json['item']) == 0


@pytest.mark.usefixtures('unbindLargeImage', 'unbindAnnotation')
@pytest.mark.plugin('large_image_annotation')
def testFolderEndpoints(server, admin, user):
    collection = Collection().createCollection(
        'collection A', user)
    colFolderA = Folder().createFolder(
        collection, 'folder A', parentType='collection',
        creator=user)
    colFolderB = Folder().createFolder(
        colFolderA, 'folder B', creator=user)
    colFolderC = Folder().createFolder(
        colFolderA, 'folder C', creator=admin, public=False)
    colFolderC = Folder().setAccessList(colFolderC, access={'users': [], 'groups': []}, save=True)
    itemA1 = Item().createItem('sample A1', user, colFolderA)
    itemA2 = Item().createItem('sample A1', user, colFolderA)
    itemB1 = Item().createItem('sample B1', user, colFolderB)
    itemB2 = Item().createItem('sample B1', user, colFolderB)
    itemC1 = Item().createItem('sample C1', admin, colFolderC)
    itemC2 = Item().createItem('sample C1', admin, colFolderC)
    Annotation().createAnnotation(itemA1, user, sampleAnnotation)
    ann = Annotation().createAnnotation(itemA1, admin, sampleAnnotation, public=False)
    Annotation().setAccessList(ann, access={'users': [], 'groups': []}, save=True)
    Annotation().createAnnotation(itemA2, user, sampleAnnotation)
    Annotation().createAnnotation(itemB1, user, sampleAnnotation)
    ann = Annotation().createAnnotation(itemB1, admin, sampleAnnotation, public=False)
    Annotation().setAccessList(ann, access={'users': [], 'groups': []}, save=True)
    Annotation().createAnnotation(itemB2, user, sampleAnnotation)
    Annotation().createAnnotation(itemC1, user, sampleAnnotation)
    ann = Annotation().createAnnotation(itemC1, admin, sampleAnnotation, public=False)
    Annotation().setAccessList(ann, access={'users': [], 'groups': []}, save=True)
    Annotation().createAnnotation(itemC2, user, sampleAnnotation)

    resp = server.request(
        path='/annotation/folder/' + str(colFolderA['_id']), user=admin,
        params={'recurse': False})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json) == 3

    resp = server.request(
        path='/annotation/folder/' + str(colFolderA['_id']), user=admin,
        params={'recurse': True})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json) == 9

    resp = server.request(
        path='/annotation/folder/' + str(colFolderA['_id']), user=user,
        params={'recurse': False})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json) == 2

    resp = server.request(
        path='/annotation/folder/' + str(colFolderA['_id']), user=user,
        params={'recurse': True})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json) == 6

    resp = server.request(
        path='/annotation/folder/' + str(colFolderC['_id']), user=user,
        params={'recurse': True})
    assert utilities.respStatus(resp) == 200
    assert len(resp.json) == 2
