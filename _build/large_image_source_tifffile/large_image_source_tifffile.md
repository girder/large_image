# large_image_source_tifffile package

## Submodules

## large_image_source_tifffile.girder_source module

### *class* large_image_source_tifffile.girder_source.TifffileGirderTileSource(\*args, \*\*kwargs)

Bases: [`TifffileFileTileSource`](#large_image_source_tifffile.TifffileFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with files that tifffile can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'tifffile'*

## Module contents

### *class* large_image_source_tifffile.TifffileFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to files that the tifffile library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### *classmethod* addKnownExtensions()

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'ome': SourcePriority.HIGHER, 'scn': SourcePriority.PREFERRED, 'tif': SourcePriority.LOW, 'tiff': SourcePriority.LOW, None: SourcePriority.LOW}*

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

#### getPreferredLevel(level)

Given a desired level (0 is minimum resolution, self.levels - 1 is max
resolution), return the level that contains actual data that is no
lower resolution.

* **Parameters:**
  **level** – desired level
* **Returns level:**
  a level with actual data that is no lower resolution.

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/scn': SourcePriority.PREFERRED, 'image/tiff': SourcePriority.LOW, 'image/x-tiff': SourcePriority.LOW, None: SourcePriority.FALLBACK}*

#### name *= 'tifffile'*

### large_image_source_tifffile.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### *class* large_image_source_tifffile.checkForMissingDataHandler(level=0)

Bases: `Handler`

Initializes the instance - basically setting the formatter to None
and the filter list to empty.

#### emit(record)

Do whatever it takes to actually log the specified logging record.

This version is intended to be implemented by subclasses and so
raises a NotImplementedError.

### large_image_source_tifffile.et_findall(tag, text)

Find all the child tags in an element tree that end with a specific string.

* **Parameters:**
  * **tag** – the tag to search.
  * **text** – the text to end with.
* **Returns:**
  a list of tags.

### large_image_source_tifffile.open(\*args, \*\*kwargs)

Create an instance of the module class.
