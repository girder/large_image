import os

import pytest
import requests

from large_image.exceptions import TileSourceError

from . import utilities

pytestmark = [
    pytest.mark.skipif(os.getenv('DICOMWEB_TEST_URL') is None,
                       reason='DICOMWEB_TEST_URL is not set'),
]


@pytest.mark.plugin('large_image_source_dicom')
def testTilesFromDICOMweb():
    import large_image_source_dicom

    dicomweb_file = {
        'url': os.environ['DICOMWEB_TEST_URL'],
        'study_uid': '2.25.25644321580420796312527343668921514374',
        'series_uid': '1.3.6.1.4.1.5962.99.1.3205815762.381594633.1639588388306.2.0',
    }

    # Use a token if we were provided with one.
    token = os.getenv('DICOMWEB_TEST_TOKEN')
    if token:
        # First, verify that we receive an authorization error without the token
        with pytest.raises(TileSourceError, match='401'):
            large_image_source_dicom.open(dicomweb_file)

        # Create a session, add the token, and try again
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {token}'})
        dicomweb_file['session'] = session

    source = large_image_source_dicom.open(dicomweb_file)

    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 7081
    assert tileMetadata['sizeY'] == 10000
    assert tileMetadata['levels'] == 7

    utilities.checkTilesZXY(source, tileMetadata)

    # Verify that the internal metadata is working too
    internalMetadata = source.getInternalMetadata()
    assert internalMetadata['dicom_meta']['Specimens'][0]['Anatomical Structure'] == 'Colon'
