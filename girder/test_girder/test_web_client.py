import os
import pytest
from pytest_girder.web_client import runWebClientTest

from .girder_utilities import girderWorker  # noqa


@pytest.mark.usefixtures('girderWorker')  # noqa
@pytest.mark.parametrize('spec', (
    'annotationListSpec.js',
    # 'annotationSpec.js',
    'geojsAnnotationSpec.js',
    'geojsSpec.js',
    'imageViewerSpec.js',
    'largeImageSpec.js'
))
def testWebClient(fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    runWebClientTest(spec, plugins=['large_image', 'large_image_annotation'])
