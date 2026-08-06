# large_image_source_tiff package

## Submodules

## large_image_source_tiff.exceptions module

### *exception* large_image_source_tiff.exceptions.IOOpenTiffError

Bases: [`IOTiffError`](#large_image_source_tiff.exceptions.IOTiffError)

An exception caused by an internal failure where the file cannot be opened
by the main library.

### *exception* large_image_source_tiff.exceptions.IOTiffError

Bases: [`TiffError`](#large_image_source_tiff.exceptions.TiffError)

An exception caused by an internal failure, due to an invalid file or other
error.

### *exception* large_image_source_tiff.exceptions.InvalidOperationTiffError

Bases: [`TiffError`](#large_image_source_tiff.exceptions.TiffError)

An exception caused by the user making an invalid request of a TIFF file.

### *exception* large_image_source_tiff.exceptions.TiffError

Bases: `Exception`

### *exception* large_image_source_tiff.exceptions.ValidationTiffError

Bases: [`TiffError`](#large_image_source_tiff.exceptions.TiffError)

An exception caused by the TIFF reader not being able to support a given
file.

## large_image_source_tiff.girder_source module

### *class* large_image_source_tiff.girder_source.TiffGirderTileSource(\*args, \*\*kwargs)

Bases: [`TiffFileTileSource`](#large_image_source_tiff.TiffFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with a TIFF file.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'tiff'*

## large_image_source_tiff.tiff_reader module

### *class* large_image_source_tiff.tiff_reader.TiledTiffDirectory(filePath, directoryNum, mustBeTiled=True, subDirectoryNum=0, validate=True)

Bases: `object`

Create a new reader for a tiled image file directory in a TIFF file.

* **Parameters:**
  * **filePath** (*str*) – A path to a TIFF file on disk.
  * **directoryNum** (*int*) – The number of the TIFF image file directory to
    open.
  * **mustBeTiled** (*bool*) – if True, only tiled images validate.  If False,
    only non-tiled images validate.  None validates both.
  * **subDirectoryNum** (*int*) – if set, the number of the TIFF subdirectory.
  * **validate** – if False, don’t validate that images can be read.
* **Raises:**
  InvalidOperationTiffError or IOTiffError or
  ValidationTiffError

#### CoreFunctions *= ['SetDirectory', 'SetSubDirectory', 'GetField', 'LastDirectory', 'GetMode', 'IsTiled', 'IsByteSwapped', 'IsUpSampled', 'IsMSB2LSB', 'NumberOfStrips']*

#### getTile(x, y, asarray=False)

Get the complete JPEG image from a tile.

* **Parameters:**
  * **x** (*int*) – The column index of the desired tile.
  * **y** (*int*) – The row index of the desired tile.
  * **asarray** (*boolean*) – If True, read jpeg compressed images as arrays.
* **Returns:**
  either a buffer with a JPEG or a PIL image.
* **Return type:**
  bytes
* **Raises:**
  InvalidOperationTiffError or IOTiffError

#### *property* imageHeight

#### *property* imageWidth

#### parse_image_description(meta=None)

#### *property* pixelInfo

#### read_image()

Use the underlying \_tiffFile to read an image.  But, if it is in a jp2k
encoding, read the raw data and convert it.

#### *property* tileHeight

Get the pixel height of tiles.

* **Returns:**
  The tile height in pixels.
* **Return type:**
  int

#### *property* tileWidth

Get the pixel width of tiles.

* **Returns:**
  The tile width in pixels.
* **Return type:**
  int

### large_image_source_tiff.tiff_reader.patchLibtiff()

## Module contents

### *class* large_image_source_tiff.TiffFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to TIFF files.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'ptif': SourcePriority.PREFERRED, 'ptiff': SourcePriority.PREFERRED, 'qptiff': SourcePriority.PREFERRED, 'svs': SourcePriority.MEDIUM, 'tif': SourcePriority.PREFERRED, 'tiff': SourcePriority.PREFERRED, None: SourcePriority.HIGH}*

#### getAssociatedImagesList()

Get a list of all associated images.

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

#### getTiffDir(directoryNum, mustBeTiled=True, subDirectoryNum=0, validate=True)

Get a tile tiff directory reader class.

* **Parameters:**
  * **directoryNum** – The number of the TIFF image file directory to
    open.
  * **mustBeTiled** – if True, only tiled images validate.  If False,
    only non-tiled images validate.  None validates both.
  * **subDirectoryNum** – if set, the number of the TIFF subdirectory.
  * **validate** – if False, don’t validate that images can be read.
* **Returns:**
  a class that can read from a specific tiff directory.

#### getTile(x, y, z, pilImageAllowed=False, numpyAllowed=False, sparseFallback=False, \*\*kwargs)

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

#### getTileIOTiffError(x, y, z, pilImageAllowed=False, numpyAllowed=False, sparseFallback=False, exception=None, \*\*kwargs)

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/tiff': SourcePriority.HIGH, 'image/x-ptif': SourcePriority.PREFERRED, 'image/x-tiff': SourcePriority.HIGH, None: SourcePriority.FALLBACK}*

#### name *= 'tiff'*

### large_image_source_tiff.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_tiff.open(\*args, \*\*kwargs)

Create an instance of the module class.
