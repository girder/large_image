# large_image_source_rasterio package

## Submodules

## large_image_source_rasterio.girder_source module

### *class* large_image_source_rasterio.girder_source.RasterioGirderTileSource(\*args, \*\*kwargs)

Bases: [`RasterioFileTileSource`](#large_image_source_rasterio.RasterioFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items for rasterio layers.

Initialize the tile class.

See the base class for other available parameters.

* **Parameters:**
  * **path** – a filesystem path for the tile source.
  * **projection** – None to use pixel space, otherwise a crs compatible with rasterio’s CRS.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.
    Ignored if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326 converted to the
    projection divided by the tile size. crs projections that are not latlong
    (is_geographic is False) must specify unitsPerPixel.

#### cacheName *= 'tilesource'*

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### name *= 'rasterio'*

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### unitsAcrossLevel0 *: float*

## Module contents

### *class* large_image_source_rasterio.RasterioFileTileSource(\*args, \*\*kwargs)

Bases: [`GDALBaseFileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource)

Provides tile access to geospatial files.

Initialize the tile class.

See the base class for other available parameters.

* **Parameters:**
  * **path** – a filesystem path for the tile source.
  * **projection** – None to use pixel space, otherwise a crs compatible with rasterio’s CRS.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.
    Ignored if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326 converted to the
    projection divided by the tile size. crs projections that are not latlong
    (is_geographic is False) must specify unitsPerPixel.

#### *classmethod* addKnownExtensions()

#### cacheName *= 'tilesource'*

#### getBandInformation(statistics=True, dataset=None, \*\*kwargs)

Get information about each band in the image.

* **Parameters:**
  * **statistics** – if True, compute statistics if they don’t already exist.
    Ignored: always treated as True.
  * **dataset** – the dataset.  If None, use the main dataset.
* **Returns:**
  a list of one dictionary per band.  Each dictionary contains
  known values such as interpretation, min, max, mean, stdev, nodata,
  scale, offset, units, categories, colortable, maskband.

#### getBounds(crs=None, \*\*kwargs)

Returns bounds of the image.

* **Parameters:**
  **crs** – the projection for the bounds.  None for the default.
* **Returns:**
  an object with the four corners and the projection that was used.
  None if we don’t know the original projection.

#### getCrs()

Returns crs object for the given dataset

* **Returns:**
  The crs or None.

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.

Data returned from this method is not guaranteed to be in
any particular format or have specific values.

* **Returns:**
  a dictionary of data or None.

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getMetadata()

Return metadata about this tile source.  This contains

> * **levels:**
>   number of tile levels in this image.
> * **sizeX:**
>   width of the image in pixels.
> * **sizeY:**
>   height of the image in pixels.
> * **tileWidth:**
>   width of a tile in pixels.
> * **tileHeight:**
>   height of a tile in pixels.
> * **magnification:**
>   if known, the magnificaiton of the image.
> * **mm_x:**
>   if known, the width of a pixel in millimeters.
> * **mm_y:**
>   if known, the height of a pixel in millimeters.
> * **dtype:**
>   if known, the type of values in this image.

> In addition to the keys that listed above, tile sources that expose
> multiple frames will also contain

> * **frames:**
>   a list of frames.  Each frame entry is a dictionary with
>   * **Frame:**
>     a 0-values frame index (the location in the list)
>   * **Channel:**
>     optional.  The name of the channel, if known
>   * **IndexC:**
>     optional if unique.  A 0-based index into the channel
>     list
>   * **IndexT:**
>     optional if unique.  A 0-based index for time values
>   * **IndexZ:**
>     optional if unique.  A 0-based index for z values
>   * **IndexXY:**
>     optional if unique.  A 0-based index for view (xy)
>     values
>   * **Index<axis>:**
>     optional if unique.  A 0-based index for an
>     arbitrary axis.
>   * **Index:**
>     a 0-based index of non-channel unique sets.  If the
>     frames vary only by channel and are adjacent, they will
>     have the same index.
> * **IndexRange:**
>   a dictionary of the number of unique index values from
>   frames if greater than 1 (e.g., if an entry like IndexXY is not
>   present, then all frames either do not have that value or have
>   a value of 0).
> * **IndexStride:**
>   a dictionary of the spacing between frames where
>   unique axes values change.
> * **channels:**
>   optional.  If known, a list of channel names
> * **channelmap:**
>   optional.  If known, a dictionary of channel names
>   with their offset into the channel list.

Note that this does not include band information, though some tile
sources may do so.

#### getPixel(\*\*kwargs)

Get a single pixel from the current tile source.

* **Parameters:**
  **kwargs** – optional arguments.  Some options are region, output, encoding,
  jpegQuality, jpegSubsampling, tiffCompression, fill.  See tileIterator.
* **Returns:**
  a dictionary with the value of the pixel for each channel on a
  scale of [0-255], including alpha, if available.  This may contain
  additional information.

#### getRegion(format=('image',), \*\*kwargs)

Get region.

Get a rectangular region from the current tile source.  Aspect ratio is preserved.
If neither width nor height is given, the original size of the highest
resolution level is used.  If both are given, the returned image will be
no larger than either size.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats. Formats
    are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY, TILE_FORMAT_IMAGE).
    If TILE_FORMAT_IMAGE, encoding may be specified.
  * **kwargs** – optional arguments.  Some options are region, output, encoding,
    jpegQuality, jpegSubsampling, tiffCompression, fill.  See tileIterator.
* **Returns:**
  regionData, formatOrRegionMime: the image data and either the
  mime type, if the format is TILE_FORMAT_IMAGE, or the format.

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

#### *static* isGeospatial(ds)

Check if a RasterIO Dataset or file path is likely to be geospatial.

* **Parameters:**
  **ds** – A RasterIO Dataset or the path to the file
* **Returns:**
  True if geospatial.

#### name *= 'rasterio'*

#### pixelToProjection(x, y, level=None)

Convert from pixels back to projection coordinates.

* **Parameters:**
  * **y** (*x* *,*) – base pixel coordinates.
  * **level** – the level of the pixel.  None for maximum level.
* **Returns:**
  px, py in projection coordinates.

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### toNativePixelCoordinates(x, y, crs=None, roundResults=True)

Convert a coordinate in the native projection to pixel coordinates.

* **Parameters:**
  * **x** – the x coordinate it the native projection.
  * **y** – the y coordinate it the native projection.
  * **crs** – input projection.  None to use the sources’s projection.
  * **roundResults** – if True, round the results to the nearest pixel.
* **Returns:**
  (x, y) the pixel coordinate.

#### unitsAcrossLevel0 *: float*

#### validateCOG(strict=True, warn=True)

Check if this image is a valid Cloud Optimized GeoTiff.

This will raise a [`large_image.exceptions.TileSourceInefficientError`](../large_image/large_image.md#large_image.exceptions.TileSourceInefficientError)
if not a valid Cloud Optimized GeoTiff. Otherwise, returns True. Requires
the `rio-cogeo` lib.

* **Parameters:**
  * **strict** – Enforce warnings as exceptions. Set to False to only warn
    and not raise exceptions.
  * **warn** – Log any warnings
* **Returns:**
  the validity of the cogtiff

### large_image_source_rasterio.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_rasterio.make_crs(projection)

### large_image_source_rasterio.open(\*args, \*\*kwargs)

Create an instance of the module class.
