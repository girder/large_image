# large_image_source_multi package

## Submodules

## large_image_source_multi.girder_source module

### *class* large_image_source_multi.girder_source.MultiGirderTileSource(\*args, \*\*kwargs)

Bases: [`MultiFileTileSource`](#large_image_source_multi.MultiFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with files that the multi source can
read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'multi'*

## Module contents

### *class* large_image_source_multi.MultiFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to a composite of other tile sources.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'json': SourcePriority.PREFERRED, 'yaml': SourcePriority.PREFERRED, 'yml': SourcePriority.PREFERRED, None: SourcePriority.MEDIUM}*

#### getAssociatedImage(imageKey, \*args, \*\*kwargs)

Return an associated image.

* **Parameters:**
  * **imageKey** – the key of the associated image to retrieve.
  * **kwargs** – optional arguments.  Some options are width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  imageData, imageMime: the image data and the mime type, or
  None if the associated image doesn’t exist.

#### getAssociatedImagesList()

Return a list of associated images.

* **Returns:**
  the list of image keys.

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.  Also, only the first 100 sources are used.

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'application/json': SourcePriority.PREFERRED, 'application/yaml': SourcePriority.PREFERRED, 'text/yaml': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### name *= 'multi'*

### large_image_source_multi.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_multi.open(\*args, \*\*kwargs)

Create an instance of the module class.
