import json
import os
import time
from unittest import mock

import pytest

from . import girder_utilities as utilities

pytestmark = pytest.mark.girder

try:
    from girder_jobs.constants import JobStatus
    from girder_jobs.models.job import Job
    from girder_large_image import constants
    from girder_large_image.models.image_item import ImageItem
    from girder_worker.girder_plugin.status import CustomJobStatus

    from girder import events
    from girder.exceptions import ValidationException
    from girder.models.file import File
    from girder.models.item import Item
    from girder.models.setting import Setting
except ImportError:
    # Make it easier to test without girder
    pass


def _waitForJobToBeRunning(job):
    job = Job().load(id=job['_id'], force=True)
    while job['status'] != JobStatus.RUNNING:
        time.sleep(0.01)
        job = Job().load(id=job['_id'], force=True)
    return job


def _createThumbnails(server, admin, spec, cancel=False):
    params = {'spec': json.dumps(spec)}
    if cancel:
        params['logInterval'] = 0
        params['concurrent'] = 1
    resp = server.request(
        method='PUT', path='/large_image/thumbnails', user=admin, params=params)
    assert utilities.respStatus(resp) == 200
    job = resp.json
    if cancel:
        job = _waitForJobToBeRunning(job)
        job = Job().cancelJob(job)

    starttime = time.time()
    while True:
        assert time.time() - starttime < 30
        resp = server.request('/job/%s' % str(job['_id']), user=admin)
        assert utilities.respStatus(resp) == 200
        if resp.json.get('status') == JobStatus.SUCCESS:
            return True
        if resp.json.get('status') == JobStatus.ERROR:
            return False
        if resp.json.get('status') == JobStatus.CANCELED:
            return 'canceled'
        time.sleep(0.1)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testSettings(server):
    for key in (constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS,
                constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER,
                constants.PluginSettings.LARGE_IMAGE_AUTO_SET):
        Setting().set(key, 'false')
        assert not Setting().get(key)
        Setting().set(key, 'true')
        assert Setting().get(key)
        with pytest.raises(ValidationException, match='must be a boolean'):
            Setting().set(key, 'not valid')
    testExtraVal = json.dumps({'images': ['label']})
    for key in (constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC,
                constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA,
                constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN,
                constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_PUBLIC,
                constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA,
                constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_ADMIN,
                ):
        Setting().set(key, '')
        assert Setting().get(key) == ''
        Setting().set(key, testExtraVal)
        assert Setting().get(key) == testExtraVal
        with pytest.raises(ValidationException, match='must be a JSON'):
            Setting().set(key, 'not valid')
        with pytest.raises(ValidationException, match='must be a JSON'):
            Setting().set(key, '[1]')
    Setting().set(constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER, 'geojs')
    assert Setting().get(constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER) == 'geojs'
    with pytest.raises(ValidationException, match='must be a non-negative integer'):
        Setting().set(constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES, -1)
    Setting().set(constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES, 5)
    assert Setting().get(constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES) == 5
    with pytest.raises(ValidationException, match='must be a non-negative integer'):
        Setting().set(constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE, -1)
    Setting().set(constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE, 1024)
    assert Setting().get(constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE) == 1024
    # Test the large_image/settings end point
    resp = server.request('/large_image/settings', user=None)
    settings = resp.json
    # The values were set earlier
    assert settings[constants.PluginSettings.LARGE_IMAGE_DEFAULT_VIEWER] == 'geojs'
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_VIEWER] is True
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_THUMBNAILS] is True
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_PUBLIC] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_EXTRA_ADMIN] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_PUBLIC] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_SHOW_ITEM_EXTRA_ADMIN] == testExtraVal
    assert settings[constants.PluginSettings.LARGE_IMAGE_AUTO_SET] is True
    assert settings[constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES] == 5
    assert settings[constants.PluginSettings.LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE] == 1024


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testThumbnailFileJob(server, admin, user, fsAssetstore):
    file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])

    # We should report zero thumbnails
    item = Item().load(itemId, user=admin)
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 0

    # Test PUT thumbnails
    resp = server.request(method='PUT', path='/large_image/thumbnails', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(method='PUT', path='/large_image/thumbnails', user=admin)
    assert utilities.respStatus(resp) == 400
    assert '"spec" is required' in resp.json['message']
    resp = server.request(
        method='PUT', path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps({})})
    assert utilities.respStatus(resp) == 400
    assert 'must be a JSON list' in resp.json['message']

    # Run a job to create two sizes of thumbnails
    assert _createThumbnails(server, admin, [
        {'width': 160, 'height': 100},
        {'encoding': 'PNG'}
    ])

    # We should report two thumbnails
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 2

    # Run a job to create two sizes of thumbnails, one different than
    # before
    assert _createThumbnails(server, admin, [
        {'width': 160, 'height': 100},
        {'width': 160, 'height': 160},
    ])
    # We should report three thumbnails
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 3

    # Asking for a bad thumbnail specification should just do nothing
    assert not _createThumbnails(server, admin, ['not a dictionary'])
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 3

    # Test GET thumbnails
    resp = server.request(path='/large_image/thumbnails', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(
        path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps({})})
    assert utilities.respStatus(resp) == 400
    assert 'must be a JSON list' in resp.json['message']
    resp = server.request(path='/large_image/thumbnails', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 3
    resp = server.request(
        path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps([{'width': 160, 'height': 100}])})
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1

    # Test DELETE thumbnails
    resp = server.request(method='DELETE', path='/large_image/thumbnails', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(
        method='DELETE', path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps({})})
    assert utilities.respStatus(resp) == 400
    assert 'must be a JSON list' in resp.json['message']

    # Delete one set of thumbnails
    resp = server.request(
        method='DELETE', path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps([{'encoding': 'PNG'}])})
    assert utilities.respStatus(resp) == 200
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 2

    # Try to delete some that don't exist
    resp = server.request(
        method='DELETE', path='/large_image/thumbnails', user=admin,
        params={'spec': json.dumps([{'width': 200, 'height': 200}])})
    assert utilities.respStatus(resp) == 200
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 2

    # Delete them all
    resp = server.request(
        method='DELETE', path='/large_image/thumbnails', user=admin)
    assert utilities.respStatus(resp) == 200
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present == 0

    # We should be able to cancel a job
    slowList = [
        {'width': 1600, 'height': 1000},
        {'width': 3200, 'height': 2000},
        {'width': 1600, 'height': 1002},
        {'width': 1600, 'height': 1003},
        {'width': 1600, 'height': 1004},
    ]
    assert _createThumbnails(server, admin, slowList, cancel=True) == 'canceled'
    present, removed = ImageItem().removeThumbnailFiles(item, keep=10)
    assert present < 3 + len(slowList)

    # Disable saving thumbnails so a slow process won't create one while the
    # test is cleaning up.
    Setting().set(constants.PluginSettings.LARGE_IMAGE_MAX_THUMBNAIL_FILES, 0)


@pytest.mark.singular
@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testDeleteIncompleteTile(server, admin, user, fsAssetstore, unavailableWorker):
    # Test the large_image/settings end point
    resp = server.request(
        method='DELETE', path='/large_image/tiles/incomplete', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(
        method='DELETE', path='/large_image/tiles/incomplete', user=admin)
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert results['removed'] == 0

    file = utilities.uploadTestFile('yb10kx5k.png', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(
        method='POST', path='/item/%s/tiles' % itemId, user=admin)
    resp = server.request(
        method='DELETE', path='/large_image/tiles/incomplete',
        user=admin)
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert results['removed'] == 1

    def preventCancel(evt):
        job = evt.info['job']
        params = evt.info['params']
        if (params.get('status') and
                params.get('status') != job['status'] and
                params['status'] in (JobStatus.CANCELED, CustomJobStatus.CANCELING)):
            evt.preventDefault()

    # Prevent a job from cancelling
    events.bind('jobs.job.update', 'testDeleteIncompleteTile', preventCancel)
    # Create a job and mark it as running
    resp = server.request(
        method='POST', path='/item/%s/tiles' % itemId, user=admin)
    job = Job().load(id=resp.json['_id'], force=True)
    Job().updateJob(job, status=JobStatus.RUNNING)

    resp = server.request(
        method='DELETE', path='/large_image/tiles/incomplete',
        user=admin)
    events.unbind('jobs.job.update', 'testDeleteIncompleteTile')
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert results['removed'] == 0
    assert 'could not be canceled' in results['message']
    # Now we should be able to cancel the job
    resp = server.request(
        method='DELETE', path='/large_image/tiles/incomplete',
        user=admin)
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert results['removed'] == 1


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testCaches(server, admin):
    resp = server.request(path='/large_image/cache', user=admin)
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert 'tilesource' in results
    resp = server.request(path='/large_image/cache/clear', method='PUT', user=admin)
    assert utilities.respStatus(resp) == 200
    results = resp.json
    assert 'cacheCleared' in results


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testAssociateImageCaching(server, admin, user, fsAssetstore):
    file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles/images/label' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    # Test GET associated_images
    resp = server.request(path='/large_image/associated_images', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(path='/large_image/associated_images', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1
    resp = server.request(path='/large_image/associated_images', user=admin, params={
        'imageKey': 'label'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1
    resp = server.request(path='/large_image/associated_images', user=admin, params={
        'imageKey': 'macro'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == 0
    # Test DELETE associated_images
    resp = server.request(
        method='DELETE', path='/large_image/associated_images', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(
        method='DELETE', path='/large_image/associated_images', user=admin, params={
            'imageKey': 'macro'})
    assert utilities.respStatus(resp) == 200
    assert resp.json == 0
    resp = server.request(
        method='DELETE', path='/large_image/associated_images', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1
    resp = server.request(path='/large_image/associated_images', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 0


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testListSources(server):
    resp = server.request(path='/large_image/sources')
    assert resp.json['tiff']['extensions']['tiff'] > 0
    assert resp.json['tiff']['version'] is not None


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testGetLargeImagePath(server, admin, fsAssetstore):
    file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    item = Item().load(itemId, user=admin)
    ts = ImageItem().tileSource(item)

    with mock.patch.object(File(), 'getGirderMountFilePath', return_value='mockmount'):
        path = ts._getLargeImagePath()
        abspath = os.path.abspath(path)
        assert path != file['path']
        assert path.endswith(file['path'])
        ts._mayHaveAdjacentFiles = True
        path = ts._getLargeImagePath()
        assert path == 'mockmount'
        origFile = file
        file['imported'] = True
        file['path'] = abspath
        file = File().save(file)
        path = ts._getLargeImagePath()
        assert path == abspath
        file = File().save(origFile)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
def testHistogramCaching(server, admin, user, fsAssetstore):
    file = utilities.uploadExternalFile('sample_image.ptif', admin, fsAssetstore)
    itemId = str(file['itemId'])
    resp = server.request(path='/item/%s/tiles/histogram' % itemId,
                          user=admin, isJson=False)
    assert utilities.respStatus(resp) == 200
    # Test GET histograms
    resp = server.request(path='/large_image/histograms', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(path='/large_image/histograms', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1
    # Test DELETE histograms
    resp = server.request(
        method='DELETE', path='/large_image/histograms', user=user)
    assert utilities.respStatus(resp) == 403
    resp = server.request(
        method='DELETE', path='/large_image/histograms', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 1
    resp = server.request(path='/large_image/histograms', user=admin)
    assert utilities.respStatus(resp) == 200
    assert resp.json == 0
