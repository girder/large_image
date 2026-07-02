# large_image_source_test package

## Module contents

### *class* large_image_source_test.TestTileSource(\*args, \*\*kwargs)

Bases: [`TileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.TileSource)

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  * **ignored_path** – for compatibility with FileTileSource.
  * **minLevel** – minimum tile level
  * **maxLevel** – maximum tile level.  If both sizeX and sizeY are
    specified, this value is ignored.
  * **tileWidth** – tile width in pixels
  * **tileHeight** – tile height in pixels
  * **sizeX** – image width in pixels at maximum level.  Computed from
    maxLevel and tileWidth if None.
  * **sizeY** – image height in pixels at maximum level.  Computed from
    maxLevel and tileHeight if None.
  * **fractal** – if True, and the tile size is square and a power of
    two, draw a simple fractal on the tiles.
  * **frames** – if present, this is either a single number for generic
    frames, a comma-separated list of c,z,t,xy, or a string of the
    form ‘<axis>=<count>,<axis>=<count>,…’.
  * **monochrome** – if True, return single channel tiles.
  * **bands** – if present, a comma-separated list of band names.
    Defaults to red,green,blue.  Each band may optionally specify a
    value range in the form “<band name>=<min val>-<max val>”.  If any
    ranges are specified, bands with no ranges will use the union of
    the specified ranges.  The internal dtype with be uint8, uint16, or
    float depending on the union of the specified ranges.  If no ranges
    are specified at all, it is the same as 0-255.

#### cacheName *= 'tilesource'*

#### *classmethod* canRead(\*args, \*\*kwargs)

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it cannot.

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.MANUAL}*

#### fractalTile(image, x, y, widthCount, color=(0, 0, 0))

Draw a simple fractal in a tile image.

* **Parameters:**
  * **image** – a Pil image to draw on.  Modified.
  * **x** – the tile x position
  * **y** – the tile y position
  * **widthCount** – 2 \*\* z; the number of tiles across for a “full size”
    image at this z level.
  * **color** – an rgb tuple on a scale of [0-255].

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

#### getTile(x, y, z, \*args, \*\*kwargs)

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

#### levels *: int*

#### name *= 'test'*

#### sizeX *: int*

#### sizeY *: int*

#### tileHeight *: int*

#### tileWidth *: int*

### large_image_source_test.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_test.open(\*args, \*\*kwargs)

Create an instance of the module class.
