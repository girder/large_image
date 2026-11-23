import os

import pytest

pytestmark = [
    pytest.mark.girder,
    pytest.mark.skipif(os.getenv('DICOMWEB_TEST_URL') is None,
                       reason='DICOMWEB_TEST_URL is not set'),
]

try:
    from girder.models.assetstore import Assetstore
    from girder.models.file import File
    from girder.models.folder import Folder
    from girder.models.item import Item
except ImportError:
    # Make it easier to test without girder
    pass

# The example data that is uploaded to the DICOMweb server used by the CI
# configuration (see .circleci/dcm4chee).
STUDY_UID = '2.25.25644321580420796312527343668921514374'
SERIES_UID = '1.3.6.1.4.1.5962.99.1.3205815762.381594633.1639588388306.2.0'


def _respStatus(resp):
    return int(resp.output_status.split()[0])


def _publicFolder(user):
    return Folder().findOne({
        'parentId': user['_id'], 'parentCollection': 'user', 'name': 'Public'})


def _importParams(folder, **params):
    return {
        'destinationType': 'folder',
        'destinationId': str(folder['_id']),
        **params,
    }


@pytest.fixture
def dicomwebAssetstore(server):
    """
    A DICOMweb assetstore that refers to the test DICOMweb server.

    This depends on the server fixture because the dicomweb plugin must be
    loaded to register the assetstore adapter, which also validates that the
    server can be reached.
    """
    from large_image_source_dicom.assetstore import DICOMWEB_META_KEY

    token = os.getenv('DICOMWEB_TEST_TOKEN')
    return Assetstore().save({
        'type': 'dicomweb',
        'name': 'DICOMweb',
        DICOMWEB_META_KEY: {
            'url': os.environ['DICOMWEB_TEST_URL'],
            'qido_prefix': None,
            'wado_prefix': None,
            'auth_type': 'token' if token else None,
            'auth_token': token,
        },
    })


# The core assetstore import endpoint runs the import as a task, so these
# tests run tasks eagerly to see the results, including validation errors
# raised by the DICOMweb assetstore adapter, in the response.

@pytest.mark.usefixtures('eagerWorkerTasks')
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
@pytest.mark.parametrize('limit', ['1.3', '-1', '0', 'abc'])
def testImportInvalidLimit(server, admin, dicomwebAssetstore, limit):
    folder = _publicFolder(admin)
    resp = server.request(
        path='/assetstore/%s/import' % dicomwebAssetstore['_id'], method='POST',
        user=admin, params=_importParams(folder, limit=limit))
    assert _respStatus(resp) == 400
    assert resp.json['message'] == 'Invalid limit: %s' % limit
    assert Folder().findOne({'parentId': folder['_id']}) is None


@pytest.mark.usefixtures('eagerWorkerTasks')
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testImportInvalidFilters(server, admin, dicomwebAssetstore):
    folder = _publicFolder(admin)
    resp = server.request(
        path='/assetstore/%s/import' % dicomwebAssetstore['_id'], method='POST',
        user=admin, params=_importParams(folder, limit='1', filters='{'))
    assert _respStatus(resp) == 400
    assert resp.json['message'].startswith('Invalid filters')
    assert Folder().findOne({'parentId': folder['_id']}) is None


@pytest.mark.usefixtures('eagerWorkerTasks')
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testImportNoMatchingStudies(server, admin, dicomwebAssetstore):
    folder = _publicFolder(admin)
    resp = server.request(
        path='/assetstore/%s/import' % dicomwebAssetstore['_id'], method='POST',
        user=admin, params=_importParams(
            folder, limit='1', filters='{"StudyInstanceUID": "DOES_NOT_EXIST"}'))
    assert _respStatus(resp) == 400
    assert resp.json['message'] == 'No studies matching the search filters were found'
    assert Folder().findOne({'parentId': folder['_id']}) is None


@pytest.mark.usefixtures('eagerWorkerTasks')
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testImportStudy(server, admin, dicomwebAssetstore):
    folder = _publicFolder(admin)
    resp = server.request(
        path='/assetstore/%s/import' % dicomwebAssetstore['_id'], method='POST',
        user=admin, params=_importParams(
            folder, limit='1', filters='{"StudyInstanceUID": "%s"}' % STUDY_UID))
    assert _respStatus(resp) == 200

    # A folder is created for the study and an item for each series
    studyFolder = Folder().findOne({'parentId': folder['_id'], 'name': STUDY_UID})
    assert studyFolder is not None
    item = Item().findOne({'folderId': studyFolder['_id'], 'name': SERIES_UID})
    assert item is not None
    assert item['dicom_uids'] == {'study_uid': STUDY_UID, 'series_uid': SERIES_UID}
    assert 'dicomweb_meta' in item

    # The series is recognized as a large image
    assert item['largeImage']['fileId'] is not None

    # The files are references to the instances on the DICOMweb server
    files = list(File().find({'itemId': item['_id']}))
    assert len(files) > 0
    for file in files:
        assert file['assetstoreId'] == dicomwebAssetstore['_id']
        assert file['imported'] is True
        assert file['mimeType'] == 'application/dicom'
        assert file['dicom_uids']['series_uid'] == SERIES_UID

    # Importing the same study again reuses the existing folder and item
    resp = server.request(
        path='/assetstore/%s/import' % dicomwebAssetstore['_id'], method='POST',
        user=admin, params=_importParams(
            folder, limit='1', filters='{"StudyInstanceUID": "%s"}' % STUDY_UID))
    assert _respStatus(resp) == 200
    assert len(list(Folder().find({'parentId': folder['_id']}))) == 1
    assert len(list(Item().find({'folderId': studyFolder['_id']}))) == 1
    assert len(list(File().find({'itemId': item['_id']}))) == len(files)


@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testPluginImportEndpoint(server, admin, dicomwebAssetstore):
    # The plugin also provides its own synchronous import endpoint, which
    # applies the same validation.
    folder = _publicFolder(admin)
    resp = server.request(
        path='/dicomweb_assetstore/%s/import' % dicomwebAssetstore['_id'],
        method='POST', user=admin, params=_importParams(folder, limit='1.3'))
    assert _respStatus(resp) == 400
    assert resp.json['message'] == 'Invalid limit: 1.3'

    resp = server.request(
        path='/dicomweb_assetstore/%s/import' % dicomwebAssetstore['_id'],
        method='POST', user=admin, params=_importParams(
            folder, limit='1', filters='{"StudyInstanceUID": "DOES_NOT_EXIST"}'))
    assert _respStatus(resp) == 400
    assert resp.json['message'] == 'No studies matching the search filters were found'
    assert Folder().findOne({'parentId': folder['_id']}) is None
