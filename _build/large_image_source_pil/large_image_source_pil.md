# large_image_source_pil package

## Submodules

## large_image_source_pil.girder_source module

### *class* large_image_source_pil.girder_source.PILGirderTileSource(\*args, \*\*kwargs)

Bases: [`PILFileTileSource`](#large_image_source_pil.PILFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with a PIL file.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  * **path** – the associated file path.
  * **maxSize** – either a number or an object with {‘width’: (width),
    ‘height’: height} in pixels.  If None, the default max size is
    used.

#### cacheName *= 'tilesource'*

#### defaultMaxSize()

Get the default max size from the config settings.

* **Returns:**
  the default max size.

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getState()

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

#### getTile(x, y, z, pilImageAllowed=False, numpyAllowed=False, mayRedirect=False, \*\*kwargs)

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

#### name *= 'pil'*

## Module contents

### *class* large_image_source_pil.PILFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to single image PIL files.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  * **path** – the associated file path.
  * **maxSize** – either a number or an object with {‘width’: (width),
    ‘height’: height} in pixels.  If None, the default max size is
    used.

#### *classmethod* addKnownExtensions()

#### cacheName *= 'tilesource'*

#### defaultMaxSize()

Get the default max size from the config settings.

* **Returns:**
  the default max size.

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'jpe': SourcePriority.LOW, 'jpeg': SourcePriority.LOW, 'jpg': SourcePriority.LOW, 'nef': SourcePriority.LOW, None: SourcePriority.FALLBACK_HIGH}*

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getMetadata()

Return a dictionary of metadata containing levels, sizeX, sizeY,
tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

* **Returns:**
  metadata dictionary.

#### getState()

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

#### getTile(x, y, z, pilImageAllowed=False, numpyAllowed=False, mayRedirect=False, \*\*kwargs)

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/jpeg': SourcePriority.LOW, None: SourcePriority.FALLBACK_HIGH}*

#### name *= 'pil'*

### large_image_source_pil.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_pil.getMaxSize(size=None, maxDefault=4096)

Get the maximum width and height that we allow for an image.

* **Parameters:**
  * **size** – the requested maximum size.  This is either a number to use
    for both width and height, or an object with {‘width’: (width),
    ‘height’: height} in pixels.  If None, the default max size is used.
  * **maxDefault** – a default value to use for width and height.
* **Returns:**
  maxWidth, maxHeight in pixels.  0 means no images are allowed.

### large_image_source_pil.open(\*args, \*\*kwargs)

Create an instance of the module class.
