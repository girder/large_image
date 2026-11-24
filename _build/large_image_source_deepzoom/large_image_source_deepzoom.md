# large_image_source_deepzoom package

## Submodules

## large_image_source_deepzoom.girder_source module

### *class* large_image_source_deepzoom.girder_source.DeepzoomGirderTileSource(\*args, \*\*kwargs)

Bases: [`DeepzoomFileTileSource`](#large_image_source_deepzoom.DeepzoomFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Deepzoom large_image tile source for Girder.

Provides tile access to Girder items with a Deepzoom xml (dzi) file and
associated pngs/jpegs in relative folders and items or on the local file
system.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'deepzoom'*

## Module contents

### *class* large_image_source_deepzoom.DeepzoomFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to a Deepzoom xml (dzi) file and associated pngs/jpegs
in relative folders on the local file system.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'dzc': SourcePriority.HIGH, 'dzi': SourcePriority.HIGH, None: SourcePriority.LOW}*

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### name *= 'deepzoom'*

### large_image_source_deepzoom.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_deepzoom.open(\*args, \*\*kwargs)

Create an instance of the module class.
