# large_image_source_nd2 package

## Submodules

## large_image_source_nd2.girder_source module

### *class* large_image_source_nd2.girder_source.ND2GirderTileSource(\*args, \*\*kwargs)

Bases: [`ND2FileTileSource`](#large_image_source_nd2.ND2FileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with an ND2 file or other files that
the nd2 library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'nd2'*

## Module contents

### *class* large_image_source_nd2.ND2FileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to nd2 files the nd2 library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'nd2': SourcePriority.PREFERRED, None: SourcePriority.LOW}*

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/nd2': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### name *= 'nd2'*

### large_image_source_nd2.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_nd2.diffObj(obj1, obj2)

Given two objects, report the differences that exist in the first object
that are not in the second object.

* **Parameters:**
  * **obj1** – the first object to compare.  Only values present in this
    object are returned.
  * **obj2** – the second object to compare.
* **Returns:**
  a subset of obj1.

### large_image_source_nd2.namedtupleToDict(obj)

Convert a namedtuple to a plain dictionary.

* **Parameters:**
  **obj** – the object to convert
* **Returns:**
  a dictionary or the original object.

### large_image_source_nd2.open(\*args, \*\*kwargs)

Create an instance of the module class.
