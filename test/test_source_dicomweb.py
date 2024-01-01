import sys

import pytest

from . import utilities

# We support Python 3.9 and greater for DICOMweb
pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 9), reason='requires python3.9 or higher'),
]


def upload_test_files(server_url):
    import urllib.request
    from io import BytesIO

    from dicomweb_client import DICOMwebClient
    from pydicom import dcmread

    urls = [
        # 'https://data.kitware.com/api/v1/file/65933ddb9c30d6f4e17c9ca1/download',
        # 'https://data.kitware.com/api/v1/file/65933dd09c30d6f4e17c9c9e/download',

        # This is the lowest resolution
        'https://data.kitware.com/api/v1/file/65933ddd9c30d6f4e17c9ca4/download',
    ]
    datasets = []
    for url in urls:
        resp = urllib.request.urlopen(url)
        data = resp.read()
        dataset = dcmread(BytesIO(data))
        datasets.append(dataset)

    client = DICOMwebClient(server_url)
    client.store_instances(datasets)


@pytest.mark.plugin('large_image_source_dicom')
def testTilesFromDICOMweb():
    import large_image_source_dicom

    url = 'http://localhost:8008/dcm4chee-arc/aets/DCM4CHEE/rs'
    study_uid = '2.25.18199272949575141157802058345697568861'
    series_uid = '1.3.6.1.4.1.5962.99.1.3510881361.982628633.1635598486609.2.0'

    # Make sure our test files are uploaded
    upload_test_files(url)

    dicomweb_file = {
        'url': url,
        'study_uid': study_uid,
        'series_uid': series_uid,
    }

    source = large_image_source_dicom.open(dicomweb_file)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 2896
    assert tileMetadata['sizeY'] == 2768
    assert tileMetadata['levels'] == 5

    utilities.checkTilesZXY(source, tileMetadata)

    # Verify that the internal metadata is working too
    internalMetadata = source.getInternalMetadata()
    assert internalMetadata['dicom_meta']['Specimens'][0]['Anatomical Structure'] == 'Lung'
