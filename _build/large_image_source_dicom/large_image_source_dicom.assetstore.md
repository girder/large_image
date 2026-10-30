# large_image_source_dicom.assetstore package

## Submodules

## large_image_source_dicom.assetstore.dicomweb_assetstore_adapter module

### *class* large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter(assetstore)

Bases: `AbstractAssetstoreAdapter`

This defines the interface to be used by all assetstore adapters.

#### *property* assetstore_meta

#### *property* auth_session

#### deleteFile(file)

This is called when a File is deleted to allow the adapter to remove
the data from within the assetstore. This method should not modify
or delete the file object, as the caller will delete it afterward.

* **Parameters:**
  **file** (*dict*) – The File document about to be deleted.

#### downloadFile(file, offset=0, headers=True, endByte=None, contentDisposition=None, extraParameters=None, \*\*kwargs)

This method is in charge of returning a value to the RESTful endpoint
that can be used to download the file. This should either return a
generator function that yields the bytes of the file (which will stream
the file directly), or modify the response headers and raise a
cherrypy.HTTPRedirect.

* **Parameters:**
  * **file** (*dict*) – The file document being downloaded.
  * **offset** (*int*) – Offset in bytes to start the download at.
  * **headers** (*bool*) – Flag for whether headers should be sent on the response.
  * **endByte** (*int* *or* *None*) – Final byte to download. If `None`, downloads to the
    end of the file.
  * **contentDisposition** (*str* *or* *None*) – Value for Content-Disposition response
    header disposition-type value.

#### finalizeUpload(upload, file)

Call this once the last chunk has been processed. This method does not
need to delete the upload document as that will be deleted by the
caller afterward. This method may augment the File document, and must
return the File document.

* **Parameters:**
  * **upload** (*dict*) – The upload document.
  * **file** (*dict*) – The file document that was created.
* **Returns:**
  The file document with optional modifications.

#### getFileSize(file)

Get the file size (computing it, if necessary). Default behavior simply
returns file.get(‘size’, 0). This method exists because some
assetstores do not compute the file size immediately, but only when
it is actually needed. The assetstore may also need to update the file
size after some changes.

#### importData(parent, parentType, params, progress, user, \*\*kwargs)

Import DICOMweb WSI instances from a DICOMweb server.

* **Parameters:**
  * **parent** – The parent object to import into.
  * **parentType** (*str*) – The model type of the parent object.
  * **params** (*dict*) – 

    Additional parameters required for the import process.
    This dictionary may include the following keys:
    * **limit:**
      (optional) limit the number of studies imported.
    * **filters:**
      (optional) a dictionary/JSON string of additional search
      filters to use with dicomweb_client’s search_for_series()
      function.
  * **progress** (`girder.utility.progress.ProgressContext`) – Object on which to record progress if possible.
  * **user** (*dict* *or* *None*) – The Girder user performing the import.
* **Returns:**
  a list of items that were created

#### initUpload(upload)

This must be called before any chunks are uploaded to do any
additional behavior and optionally augment the upload document. The
method must return the upload document. Default behavior is to
simply return the upload document unmodified.

* **Parameters:**
  **upload** (*dict*) – The upload document to optionally augment.

#### setContentHeaders(file, offset, endByte, contentDisposition=None)

Sets the Content-Length, Content-Disposition, Content-Type, and also
the Content-Range header if this is a partial download.

* **Parameters:**
  * **file** – The file being downloaded.
  * **offset** (*int*) – The start byte of the download.
  * **endByte** (*int* *or* *None*) – The end byte of the download (non-inclusive).
  * **contentDisposition** (*str* *or* *None*) – Content-Disposition response header
    disposition-type value, if None, Content-Disposition will
    be set to ‘attachment; filename=$filename’.

#### *static* validateInfo(doc)

Adapters may implement this if they need to perform any validation
steps whenever the assetstore info is saved to the database. It should
return the document with any necessary alterations in the success case,
or throw an exception if validation fails.

## large_image_source_dicom.assetstore.rest module

### *class* large_image_source_dicom.assetstore.rest.DICOMwebAssetstoreResource

Bases: `Resource`

#### importData(assetstore, destinationId, destinationType, limit, filters, progress)

## Module contents

### *class* large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter(assetstore)

Bases: `AbstractAssetstoreAdapter`

This defines the interface to be used by all assetstore adapters.

#### *property* assetstore_meta

#### *property* auth_session

#### deleteFile(file)

This is called when a File is deleted to allow the adapter to remove
the data from within the assetstore. This method should not modify
or delete the file object, as the caller will delete it afterward.

* **Parameters:**
  **file** (*dict*) – The File document about to be deleted.

#### downloadFile(file, offset=0, headers=True, endByte=None, contentDisposition=None, extraParameters=None, \*\*kwargs)

This method is in charge of returning a value to the RESTful endpoint
that can be used to download the file. This should either return a
generator function that yields the bytes of the file (which will stream
the file directly), or modify the response headers and raise a
cherrypy.HTTPRedirect.

* **Parameters:**
  * **file** (*dict*) – The file document being downloaded.
  * **offset** (*int*) – Offset in bytes to start the download at.
  * **headers** (*bool*) – Flag for whether headers should be sent on the response.
  * **endByte** (*int* *or* *None*) – Final byte to download. If `None`, downloads to the
    end of the file.
  * **contentDisposition** (*str* *or* *None*) – Value for Content-Disposition response
    header disposition-type value.

#### finalizeUpload(upload, file)

Call this once the last chunk has been processed. This method does not
need to delete the upload document as that will be deleted by the
caller afterward. This method may augment the File document, and must
return the File document.

* **Parameters:**
  * **upload** (*dict*) – The upload document.
  * **file** (*dict*) – The file document that was created.
* **Returns:**
  The file document with optional modifications.

#### getFileSize(file)

Get the file size (computing it, if necessary). Default behavior simply
returns file.get(‘size’, 0). This method exists because some
assetstores do not compute the file size immediately, but only when
it is actually needed. The assetstore may also need to update the file
size after some changes.

#### importData(parent, parentType, params, progress, user, \*\*kwargs)

Import DICOMweb WSI instances from a DICOMweb server.

* **Parameters:**
  * **parent** – The parent object to import into.
  * **parentType** (*str*) – The model type of the parent object.
  * **params** (*dict*) – 

    Additional parameters required for the import process.
    This dictionary may include the following keys:
    * **limit:**
      (optional) limit the number of studies imported.
    * **filters:**
      (optional) a dictionary/JSON string of additional search
      filters to use with dicomweb_client’s search_for_series()
      function.
  * **progress** (`girder.utility.progress.ProgressContext`) – Object on which to record progress if possible.
  * **user** (*dict* *or* *None*) – The Girder user performing the import.
* **Returns:**
  a list of items that were created

#### initUpload(upload)

This must be called before any chunks are uploaded to do any
additional behavior and optionally augment the upload document. The
method must return the upload document. Default behavior is to
simply return the upload document unmodified.

* **Parameters:**
  **upload** (*dict*) – The upload document to optionally augment.

#### setContentHeaders(file, offset, endByte, contentDisposition=None)

Sets the Content-Length, Content-Disposition, Content-Type, and also
the Content-Range header if this is a partial download.

* **Parameters:**
  * **file** – The file being downloaded.
  * **offset** (*int*) – The start byte of the download.
  * **endByte** (*int* *or* *None*) – The end byte of the download (non-inclusive).
  * **contentDisposition** (*str* *or* *None*) – Content-Disposition response header
    disposition-type value, if None, Content-Disposition will
    be set to ‘attachment; filename=$filename’.

#### *static* validateInfo(doc)

Adapters may implement this if they need to perform any validation
steps whenever the assetstore info is saved to the database. It should
return the document with any necessary alterations in the success case,
or throw an exception if validation fails.

### large_image_source_dicom.assetstore.load(info)

Load the plugin into Girder.

* **Parameters:**
  **info** – a dictionary of plugin information.  The name key contains the
  name of the plugin according to Girder.
