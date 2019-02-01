import os
import pytest
from pytest_girder.web_client import runWebClientTest

from .girder_utilities import girderWorker  # noqa


@pytest.mark.usefixtures('girderWorker')  # noqa
@pytest.mark.plugin('large_image')
@pytest.mark.parametrize('spec', (
    'imageViewerSpec.js',
    'largeImageSpec.js',
))
def testWebClient(boundServer, fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec)


@pytest.mark.usefixtures('girderWorker')  # noqa
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('large_image_annotation')
@pytest.mark.parametrize('spec', (
    'annotationListSpec.js',
    # 'annotationSpec.js',
    'geojsAnnotationSpec.js',
    'geojsSpec.js',
))
def testWebClientWithAnnotation(boundServer, fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(boundServer, spec)
