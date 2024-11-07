import os
import sys
import tempfile

import pytest

# We support Python 3.9 and greater for DICOMweb
pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 9), reason='requires python3.9 or higher'),
    pytest.mark.skipif(os.getenv('DICOMWEB_TEST_URL') is None,
                       reason='DICOMWEB_TEST_URL is not set'),
]


@pytest.mark.girder
@pytest.mark.girder_client
@pytest.mark.plugin('large_image')
@pytest.mark.plugin('dicomweb')
def testDICOMWebClient(boundServer, fsAssetstore, db):
    from pytest_girder.web_client import runWebClientTest

    spec = os.path.join(os.path.dirname(__file__), 'web_client_specs', 'dicomWebSpec.js')

    # Replace the template variables
    with open(spec) as rf:
        data = rf.read()

    dicomweb_test_url = os.environ['DICOMWEB_TEST_URL']
    data = data.replace('DICOMWEB_TEST_URL', f"'{dicomweb_test_url}'")

    dicomweb_test_token = os.getenv('DICOMWEB_TEST_TOKEN')
    if dicomweb_test_token:
        dicomweb_test_token = f"'{dicomweb_test_token}'"
    else:
        dicomweb_test_token = 'null'
    data = data.replace('DICOMWEB_TEST_TOKEN', dicomweb_test_token)

    # Need to avoid context manager for this to work on Windows
    tf = tempfile.NamedTemporaryFile(delete=False)
    try:
        tf.write(data.encode())
        tf.close()
        runWebClientTest(boundServer, tf.name, 15000)
    finally:
        os.remove(tf.name)
