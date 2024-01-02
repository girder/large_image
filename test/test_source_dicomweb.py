import sys

import pytest

from . import utilities

# We support Python 3.9 and greater for DICOMweb
pytestmark = [
    pytest.mark.skipif(sys.version_info < (3, 9), reason='requires python3.9 or higher'),
]


@pytest.mark.plugin('large_image_source_dicom')
def testTilesFromDICOMweb():
    import large_image_source_dicom

    dicomweb_file = {
        'url': 'http://localhost:8008/dcm4chee-arc/aets/DCM4CHEE/rs',
        'study_uid': '2.25.18199272949575141157802058345697568861',
        'series_uid': '1.3.6.1.4.1.5962.99.1.3510881361.982628633.1635598486609.2.0',
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
