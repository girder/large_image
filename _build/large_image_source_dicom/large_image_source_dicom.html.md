# large_image_source_dicom package

## Subpackages

* [large_image_source_dicom.assetstore package](large_image_source_dicom.assetstore.md)
  * [Submodules](large_image_source_dicom.assetstore.md#submodules)
  * [large_image_source_dicom.assetstore.dicomweb_assetstore_adapter module](large_image_source_dicom.assetstore.md#module-large_image_source_dicom.assetstore.dicomweb_assetstore_adapter)
    * [`DICOMwebAssetstoreAdapter`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter)
      * [`DICOMwebAssetstoreAdapter.assetstore_meta`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.assetstore_meta)
      * [`DICOMwebAssetstoreAdapter.auth_session`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.auth_session)
      * [`DICOMwebAssetstoreAdapter.deleteFile()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.deleteFile)
      * [`DICOMwebAssetstoreAdapter.downloadFile()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.downloadFile)
      * [`DICOMwebAssetstoreAdapter.finalizeUpload()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.finalizeUpload)
      * [`DICOMwebAssetstoreAdapter.getFileSize()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.getFileSize)
      * [`DICOMwebAssetstoreAdapter.importData()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.importData)
      * [`DICOMwebAssetstoreAdapter.initUpload()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.initUpload)
      * [`DICOMwebAssetstoreAdapter.setContentHeaders()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.setContentHeaders)
      * [`DICOMwebAssetstoreAdapter.validateInfo()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.dicomweb_assetstore_adapter.DICOMwebAssetstoreAdapter.validateInfo)
  * [large_image_source_dicom.assetstore.rest module](large_image_source_dicom.assetstore.md#module-large_image_source_dicom.assetstore.rest)
    * [`DICOMwebAssetstoreResource`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.rest.DICOMwebAssetstoreResource)
      * [`DICOMwebAssetstoreResource.importData()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.rest.DICOMwebAssetstoreResource.importData)
  * [Module contents](large_image_source_dicom.assetstore.md#module-large_image_source_dicom.assetstore)
    * [`DICOMwebAssetstoreAdapter`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter)
      * [`DICOMwebAssetstoreAdapter.assetstore_meta`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.assetstore_meta)
      * [`DICOMwebAssetstoreAdapter.auth_session`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.auth_session)
      * [`DICOMwebAssetstoreAdapter.deleteFile()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.deleteFile)
      * [`DICOMwebAssetstoreAdapter.downloadFile()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.downloadFile)
      * [`DICOMwebAssetstoreAdapter.finalizeUpload()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.finalizeUpload)
      * [`DICOMwebAssetstoreAdapter.getFileSize()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.getFileSize)
      * [`DICOMwebAssetstoreAdapter.importData()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.importData)
      * [`DICOMwebAssetstoreAdapter.initUpload()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.initUpload)
      * [`DICOMwebAssetstoreAdapter.setContentHeaders()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.setContentHeaders)
      * [`DICOMwebAssetstoreAdapter.validateInfo()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.DICOMwebAssetstoreAdapter.validateInfo)
    * [`load()`](large_image_source_dicom.assetstore.md#large_image_source_dicom.assetstore.load)

## Submodules

## large_image_source_dicom.dicom_metadata module

### large_image_source_dicom.dicom_metadata.extract_dicom_metadata(dataset)

### large_image_source_dicom.dicom_metadata.extract_specimen_metadata(dataset)

## large_image_source_dicom.dicom_tags module

### large_image_source_dicom.dicom_tags.dicom_key_to_tag(key)

## large_image_source_dicom.dicomweb_utils module

### large_image_source_dicom.dicomweb_utils.get_dicomweb_metadata(client, study_uid, series_uid)

### large_image_source_dicom.dicomweb_utils.get_first_wsi_volume_metadata(client, study_uid, series_uid)

## large_image_source_dicom.girder_plugin module

### *class* large_image_source_dicom.girder_plugin.DICOMwebPlugin(entrypoint)

Bases: `GirderPlugin`

#### CLIENT_SOURCE_PATH *= 'web_client'*

The path of the plugin’s web client source code.  This path is given relative to the python
package.  This property is used to link the web client source into the staging area while
building in development mode.  When this value is None it indicates there is no web client
component.

#### DISPLAY_NAME *= 'DICOMweb Plugin'*

This is the named displayed to users on the plugin page.  Unlike the entrypoint name
used internally, this name can be an arbitrary string.

#### load(info)

## large_image_source_dicom.girder_source module

### *class* large_image_source_dicom.girder_source.DICOMGirderTileSource(\*args, \*\*kwargs)

Bases: [`DICOMFileTileSource`](#large_image_source_dicom.DICOMFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with an DICOM file or other files that
the dicomreader library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'dicom'*

## Module contents

### *class* large_image_source_dicom.DICOMFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to dicom files the dicom or dicomreader library can
read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'dcm': SourcePriority.PREFERRED, 'dic': SourcePriority.PREFERRED, 'dicom': SourcePriority.PREFERRED, None: SourcePriority.LOW}*

#### getAssociatedImagesList()

Return a list of associated images.

* **Returns:**
  the list of image keys.

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### getMetadata()

Return a dictionary of metadata containing levels, sizeX, sizeY,
tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

* **Returns:**
  metadata dictionary.

#### getNativeMagnification()

Get the magnification at a particular level.

* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getTile(x, y, z, pilImageAllowed=False, numpyAllowed=False, \*\*kwargs)

Get a tile from a tile source, returning it as an binary image, a PIL
image, or a numpy array.

* **Parameters:**
  * **x** – the 0-based x position of the tile on the specified z level.
    0 is left.
  * **y** – the 0-based y position of the tile on the specified z level.
    0 is top.
  * **z** – the z level of the tile.  May range from [0, self.levels],
    where 0 is the lowest resolution, single tile for the whole source.
  * **pilImageAllowed** – True if a PIL image may be returned.
  * **numpyAllowed** – True if a numpy image may be returned.  ‘always’
    to return a numpy array.
  * **sparseFallback** – if False and a tile doesn’t exist, raise an
    error.  If True, check if a lower resolution tile exists, and, if
    so, interpolate the needed data for this tile.
  * **frame** – the frame number within the tile source.  None is the
    same as 0 for multi-frame sources.
* **Returns:**
  either a numpy array, a PIL image, or a memory object with an
  image file.

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'application/dicom': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### name *= 'dicom'*

#### nameMatches *: dict[str, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'DCM_\\\\d+$': SourcePriority.MEDIUM, '\\\\d+(\\\\.\\\\d+){3,20}$': SourcePriority.MEDIUM}*

### large_image_source_dicom.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_dicom.dicom_to_dict(ds, base=None)

Convert a pydicom dataset to a fairly flat python dictionary for purposes
of reporting.  This is not invertable without extra work.

* **Parameters:**
  * **ds** – a pydicom dataset.
  * **base** – a base dataset entry within the dataset.
* **Returns:**
  a dictionary of values.

### large_image_source_dicom.open(\*args, \*\*kwargs)

Create an instance of the module class.
