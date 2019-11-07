import os
import pytest
from pytest_girder.web_client import runWebClientTest

from .girder_utilities import girderWorker, unbindLargeImage  # noqa


@pytest.mark.usefixtures('unbindLargeImage')  # noqa
@pytest.mark.usefixtures('girderWorker')  # noqa
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', (
    'imageViewerSpec.js',
    'largeImageSpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, spec, girderWorker):  # noqa
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec, 15000)
