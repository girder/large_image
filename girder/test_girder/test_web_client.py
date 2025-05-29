import os

import pytest

pytestmark = [pytest.mark.girder, pytest.mark.girder_client]

try:
    from pytest_girder.web_client import runWebClientTest
except ImportError:
    # Make it easier to test without girder
    pass


@pytest.mark.singular
@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', [
    'imageViewerSpec.js',
])
def testWebClient(boundServer, fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)


@pytest.mark.singular
@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', [
    'largeImageSpec.js',
    'otherFeatures.js',
])
def testWebClientNoWorker(boundServer, fsAssetstore, db, spec):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)


@pytest.mark.singular
@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', [
    'imageViewerSpec.js',
])
def testWebClientNoStream(boundServer, fsAssetstore, db, spec, girderWorker):
    from girder.models.setting import Setting
    from girder.settings import SettingKey

    Setting().set(SettingKey.ENABLE_NOTIFICATION_STREAM, False)

    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 60000)
