import os
import pytest
import warnings
from pytest_girder.web_client import runWebClientTest

from .girder_utilities import girderWorker  # noqa


with warnings.catch_warnings():
    warnings.filterwarnings('ignore', 'setup_database.*')
    from pytest_girder.setup_database import setupDatabase


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
    'annotationSpec.js',
    'geojsAnnotationSpec.js',
    'geojsSpec.js',
))
def testWebClientWithAnnotation(boundServer, fsAssetstore, db, spec, girderWorker):
    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', spec)
    setupFile = os.path.splitext(spec)[0] + '.yml'
    if os.path.exists(setupFile):
        setupDatabase(setupFile)
    runWebClientTest(boundServer, spec)
