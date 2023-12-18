import os
import sys

import pytest

# We support Python 3.9 and greater for DICOMweb
pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 9), reason='requires python3.9 or higher'),
]


@pytest.mark.skip(reason='the remote server we test with is down as of 2023-12-17')
@pytest.mark.girder()
@pytest.mark.girder_client()
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testDICOMWebClient(boundServer, fsAssetstore, db):
    from pytest_girder.web_client import runWebClientTest

    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', 'dicomWebSpec.js')
    runWebClientTest(boundServer, spec, 15000)
