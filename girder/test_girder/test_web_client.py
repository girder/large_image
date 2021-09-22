import os

import pytest
from pytest_girder.web_client import runWebClientTest


@pytest.mark.singular
@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', (
    'imageViewerSpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)


@pytest.mark.usefixtures('unbindLargeImage')
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', (
    'largeImageSpec.js',
))
def testWebClientNoWorker(boundServer, fsAssetstore, db, spec):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
