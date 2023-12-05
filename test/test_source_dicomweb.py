import pytest

from . import utilities


@pytest.mark.plugin('large_image_source_dicom')
def testTilesFromDICOMweb():
    import large_image_source_dicom

    # Hopefully this URL and file will work for a long time. But we might need
    # to update it at some point.
    dicomweb_file = {
        'url': 'https://idc-external-006.uc.r.appspot.com/dcm4chee-arc/aets/DCM4CHEE/rs',
        'study_uid': '2.25.18199272949575141157802058345697568861',
        'series_uid': '1.3.6.1.4.1.5962.99.1.3510881361.982628633.1635598486609.2.0',
    }

    source = large_image_source_dicom.open(dicomweb_file)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 46336
    assert tileMetadata['sizeY'] == 44288
    assert tileMetadata['levels'] == 9

    utilities.checkTilesZXY(source, tileMetadata)

    # Verify that the internal metadata is working too
    internalMetadata = source.getInternalMetadata()
    assert internalMetadata['dicom_meta']['Specimens'][0]['Anatomical Structure'] == 'Lung'
