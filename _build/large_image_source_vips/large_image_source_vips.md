# large_image_source_vips package

## Submodules

## large_image_source_vips.girder_source module

### *class* large_image_source_vips.girder_source.VipsGirderTileSource(\*args, \*\*kwargs)

Bases: [`VipsFileTileSource`](#large_image_source_vips.VipsFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Vips large_image tile source for Girder.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### name *= 'vips'*

## Module contents

### *class* large_image_source_vips.VipsFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to any libvips compatible file.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### *classmethod* addKnownExtensions()

#### addTile(tile, x=0, y=0, mask=None, interpretation=None)

Add a numpy or image tile to the image, expanding the image as needed
to accommodate it.  Note that x and y can be negative.  If so, the
output image (and internal memory access of the image) will act as if
the 0, 0 point is the most negative position.  Cropping is applied
after this offset.

* **Parameters:**
  * **tile** – a numpy array, PIL Image, vips image, or a binary string
    with an image.  The numpy array can have 2 or 3 dimensions.
  * **x** – location in destination for upper-left corner.
  * **y** – location in destination for upper-left corner.
  * **mask** – a 2-d numpy array (or 3-d if the last dimension is 1).
    If specified, areas where the mask is false will not be altered.
  * **interpretation** – one of the pyvips.enums.Interpretation or ‘L’,
    ‘LA’, ‘RGB’, “RGBA’.  This defaults to RGB/RGBA for 3/4 channel
    images and L/LA for 1/2 channels.  The special value ‘pixelmap’
    will convert a 1 channel integer to a 3 channel RGB map.  For
    images which are not 1 or 3 bands with an optional alpha, specify
    MULTIBAND.  In this case, the mask option cannot be used.

#### *property* bandFormat

#### *property* bandRanges

#### cacheName *= 'tilesource'*

#### *property* crop

Crop only applies to the output file, not the internal data access.

It consists of x, y, w, h in pixels.

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.LOW}*

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### *property* minHeight

#### *property* minWidth

#### *property* mm_x

#### *property* mm_y

#### name *= 'vips'*

#### newPriority *: [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority) | None* *= 4*

#### *property* origin

#### write(path, lossy=True, alpha=True, overwriteAllowed=True, vips_kwargs=None)

Output the current image to a file.

* **Parameters:**
  * **path** – output path.
  * **lossy** – if false, emit a lossless file.
  * **alpha** – True if an alpha channel is allowed.
  * **overwriteAllowed** – if False, raise an exception if the output
    path exists.
  * **vips_kwargs** – if not None, save the image using these kwargs to
    the write_to_file function instead of the automatically chosen
    ones.  In this case, lossy is ignored and all vips options must be
    manually specified.

### large_image_source_vips.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_vips.new(\*args, \*\*kwargs)

Create a new image, collecting the results from patches of numpy arrays or
smaller images.

### large_image_source_vips.open(\*args, \*\*kwargs)

Create an instance of the module class.
