# large_image_source_dummy package

## Module contents

### *class* large_image_source_dummy.DummyTileSource(\*args, \*\*kwargs)

Bases: [`TileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.TileSource)

Initialize the tile class.

* **Parameters:**
  * **jpegQuality** – when serving jpegs, use this quality.
  * **jpegSubsampling** – when serving jpegs, use this subsampling (0 is
    full chroma, 1 is half, 2 is quarter).
  * **encoding** – ‘JPEG’, ‘PNG’, ‘TIFF’, or ‘TILED’.
  * **edge** – False to leave edge tiles whole, True or ‘crop’ to crop
    edge tiles, otherwise, an #rrggbb color to fill edges.
  * **tiffCompression** – the compression format to use when encoding a
    TIFF.
  * **style** – 

    if None, use the default style for the file.  Otherwise,
    this is a string with a json-encoded dictionary.  The style can
    contain the following keys:
    > * **band:**
    >   if -1 or None, and if style is specified at all, the
    >   greyscale value is used.  Otherwise, a 1-based numerical
    >   index into the channels of the image or a string that
    >   matches the interpretation of the band (‘red’, ‘green’,
    >   ‘blue’, ‘gray’, ‘alpha’).  Note that ‘gray’ on an RGB or
    >   RGBA image will use the green band.
    > * **frame:**
    >   if specified, override the frame value for this band.
    >   When used as part of a bands list, this can be used to
    >   composite multiple frames together.  It is most efficient
    >   if at least one band either doesn’t specify a frame
    >   parameter or specifies the same frame value as the primary
    >   query.
    > * **framedelta:**
    >   if specified and frame is not specified, override
    >   the frame value for this band by using the current frame
    >   plus this value.
    > * **min:**
    >   the value to map to the first palette value.  Defaults to
    >   0.  ‘auto’ to use 0 if the reported minimum and maximum of
    >   the band are between [0, 255] or use the reported minimum
    >   otherwise.  ‘min’ or ‘max’ to always uses the reported
    >   minimum or maximum.  ‘full’ to always use 0.
    > * **max:**
    >   the value to map to the last palette value.  Defaults to
    >   255.  ‘auto’ to use 0 if the reported minimum and maximum
    >   of the band are between [0, 255] or use the reported
    >   maximum otherwise.  ‘min’ or ‘max’ to always uses the
    >   reported minimum or maximum.  ‘full’ to use the maximum
    >   value of the base data type (either 1, 255, or 65535).
    > * **palette:**
    >   a single color string, a palette name, or a list of
    >   two or more color strings.  Color strings are of the form
    >   #RRGGBB, #RRGGBBAA, #RGB, #RGBA, or any string parseable by
    >   the PIL modules, or, if it is installed, by matplotlib.   A
    >   single color string is the same as the list [‘#000’,
    >   <color>].  Palette names are the name of a palettable
    >   palette or, if available, a matplotlib palette.
    > * **nodata:**
    >   the value to use for missing data.  null or unset to
    >   not use a nodata value.
    > * **composite:**
    >   either ‘lighten’ or ‘multiply’.  Defaults to
    >   ‘lighten’ for all except the alpha band.
    > * **clamp:**
    >   either True to clamp (also called clip or crop) values
    >   outside of the [min, max] to the ends of the palette or
    >   False to make outside values transparent.
    > * **dtype:**
    >   convert the results to the specified numpy dtype.
    >   Normally, if a style is applied, the results are
    >   intermediately a float numpy array with a value range of
    >   [0,255].  If this is ‘uint16’, it will be cast to that and
    >   multiplied by 65535/255.  If ‘float’, it will be divided by
    >   255.  If ‘source’, this uses the dtype of the source image.
    > * **axis:**
    >   keep only the specified axis from the numpy intermediate
    >   results.  This can be used to extract a single channel
    >   after compositing.

    Alternately, the style object can contain a single key of ‘bands’,
    which has a value which is a list of style dictionaries as above,
    excepting that each must have a band that is not -1.  Bands are
    composited in the order listed.  This base object may also contain
    the ‘dtype’ and ‘axis’ values.
  * **noCache** – if True, the style can be adjusted dynamically and the
    source is not elibible for caching.  If there is no intention to
    reuse the source at a later time, this can have performance
    benefits, such as when first cataloging images that can be read.

#### *classmethod* canRead(\*args, \*\*kwargs)

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it cannot.

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.MANUAL}*

#### getTile(x, y, z, \*\*kwargs)

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

#### name *= 'dummy'*

### large_image_source_dummy.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_dummy.open(\*args, \*\*kwargs)

Create an instance of the module class.
