# large_image_source_zarr package

## Submodules

## large_image_source_zarr.girder_source module

### *class* large_image_source_zarr.girder_source.ZarrGirderTileSource(\*args, \*\*kwargs)

Bases: [`ZarrFileTileSource`](#large_image_source_zarr.ZarrFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with files that OME Zarr can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'zarr'*

## Module contents

### *class* large_image_source_zarr.ZarrFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to files that the zarr library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### addAssociatedImage(image, imageKey=None)

Add an associated image to this source.

* **Parameters:**
  **image** – a numpy array, PIL Image, or a binary string
  with an image.  The numpy array can have 2 or 3 dimensions.

#### addTile(tile, x=0, y=0, mask=None, axes=None, \*\*kwargs)

Add a numpy or image tile to the image, expanding the image as needed
to accommodate it.  Note that x and y can be negative.  If so, the
output image (and internal memory access of the image) will act as if
the 0, 0 point is the most negative position.  Cropping is applied
after this offset.

* **Parameters:**
  * **tile** – a numpy array, PIL Image, or a binary string
    with an image.  The numpy array can have 2 or 3 dimensions.
  * **x** – location in destination for upper-left corner.
  * **y** – location in destination for upper-left corner.
  * **mask** – a 2-d numpy array (or 3-d if the last dimension is 1).
    If specified, areas where the mask is false will not be altered.
  * **axes** – a string or list of strings specifying the names of axes
    in the same order as the tile dimensions.
  * **kwargs** – start locations for any additional axes.  Note that
    `level` is a reserved word and not permitted for an axis name.

#### *property* additionalMetadata

#### cacheName *= 'tilesource'*

#### *property* channelColors

#### *property* channelNames

If known, return a list of channel names.

* **Returns:**
  either None or a list of channel names as strings.

#### *property* crop

Crop only applies to the output file, not the internal data access.

It consists of x, y, w, h in pixels.

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'db': SourcePriority.MEDIUM, 'zarr': SourcePriority.PREFERRED, 'zarray': SourcePriority.PREFERRED, 'zattrs': SourcePriority.PREFERRED, 'zgroup': SourcePriority.PREFERRED, 'zip': SourcePriority.LOWER, None: SourcePriority.LOW}*

#### *property* frameAxes

#### *property* frameUnits

#### *property* frameValues

#### *property* gcps

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

#### getState()

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

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

#### *property* imageDescription

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'application/vnd+zarr': SourcePriority.PREFERRED, 'application/x-zarr': SourcePriority.PREFERRED, 'application/zip+zarr': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### *property* minHeight

#### *property* minWidth

#### *property* mm_x

#### *property* mm_y

#### name *= 'zarr'*

#### newPriority *: [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority) | None* *= 3*

#### *property* projection

#### write(path, lossy=True, alpha=True, overwriteAllowed=True, resample=None, \*\*converterParams)

Output the current image to a file.

* **Parameters:**
  * **path** – output path.
  * **lossy** – if false, emit a lossless file.
  * **alpha** – True if an alpha channel is allowed.
  * **overwriteAllowed** – if False, raise an exception if the output
    path exists.
  * **resample** – one of the `ResampleMethod` enum values.  Defaults
    to `NP_NEAREST` for lossless and non-uint8 data and to
    `PIL_LANCZOS` for lossy uint8 data.
  * **converterParams** – options to pass to the large_image_converter if
    the output is not a zarr variant.

### large_image_source_zarr.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_zarr.new(\*args, \*\*kwargs)

Create a new image, collecting the results from patches of numpy arrays or
smaller images.

### large_image_source_zarr.open(\*args, \*\*kwargs)

Create an instance of the module class.
