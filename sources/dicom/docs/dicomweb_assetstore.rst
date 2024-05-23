DICOMweb Assetstore
===================

The DICOM source also provides a Girder Assetstore plugin for accessing data on DICOMweb servers.  This is available if the package is installed in the same python environment as Girder and the Girder client is built after installation.

A DICOMweb assetstore can be added through the Girder Admin Console by selecting the "Create new DICOMweb assetstore" button.  It requires an appropriate URL; for those using DCM4CHEE, this might be something like "https://some.server.com/dcm4chee-arc/aets/DCM4CHEE/rs".  Check with the DICOMweb provider for appropriate QIDO and WADO prefixes.

Existing images have to be imported from the assetstore via the standard Girder import process.  A json specification to filter the import can be added.  A common filter is to only import Slide Modality images via ``{ "ModalitiesInStudy": "SM" }``.
