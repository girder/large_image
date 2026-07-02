# large_image_source_ometiff package

## Submodules

## large_image_source_ometiff.girder_source module

### *class* large_image_source_ometiff.girder_source.OMETiffGirderTileSource(\*args, \*\*kwargs)

Bases: [`OMETiffFileTileSource`](#large_image_source_ometiff.OMETiffFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with an OMETiff file.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'ometiff'*

## Module contents

### *class* large_image_source_ometiff.OMETiffFileTileSource(\*args, \*\*kwargs)

Bases: [`TiffFileTileSource`](../large_image_source_tiff/large_image_source_tiff.md#large_image_source_tiff.TiffFileTileSource)

Provides tile access to TIFF files.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'ome': SourcePriority.PREFERRED, 'tif': SourcePriority.MEDIUM, 'tiff': SourcePriority.MEDIUM, None: SourcePriority.LOW}*

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

Get the magnification for the highest-resolution level.

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/tiff': SourcePriority.MEDIUM, 'image/x-tiff': SourcePriority.MEDIUM}*

#### name *= 'ometiff'*

### large_image_source_ometiff.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_ometiff.open(\*args, \*\*kwargs)

Create an instance of the module class.
