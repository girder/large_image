# large_image_source_gdal package

## Submodules

## large_image_source_gdal.girder_source module

### *class* large_image_source_gdal.girder_source.GDALGirderTileSource(\*args, \*\*kwargs)

Bases: [`GDALFileTileSource`](#large_image_source_gdal.GDALFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items for gdal layers.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  * **path** – a filesystem path for the tile source.
  * **projection** – None to use pixel space, otherwise a proj4
    projection string or a case-insensitive string of the form
    ‘EPSG:<epsg number>’.  If a string and case-insensitively prefixed
    with ‘proj4:’, that prefix is removed.  For instance,
    ‘proj4:EPSG:3857’, ‘PROJ4:+init=epsg:3857’, and ‘+init=epsg:3857’,
    and ‘EPSG:3857’ are all equivalent.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.  Ignored
    if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326
    converted to the projection divided by the tile size.  Proj4
    projections that are not latlong (is_geographic is False) must
    specify unitsPerPixel.

#### cacheName *= 'tilesource'*

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### name *= 'gdal'*

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### unitsAcrossLevel0 *: float*

## Module contents

### *class* large_image_source_gdal.GDALFileTileSource(\*args, \*\*kwargs)

Bases: [`GDALBaseFileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource)

Provides tile access to geospatial files.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  * **path** – a filesystem path for the tile source.
  * **projection** – None to use pixel space, otherwise a proj4
    projection string or a case-insensitive string of the form
    ‘EPSG:<epsg number>’.  If a string and case-insensitively prefixed
    with ‘proj4:’, that prefix is removed.  For instance,
    ‘proj4:EPSG:3857’, ‘PROJ4:+init=epsg:3857’, and ‘+init=epsg:3857’,
    and ‘EPSG:3857’ are all equivalent.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.  Ignored
    if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326
    converted to the projection divided by the tile size.  Proj4
    projections that are not latlong (is_geographic is False) must
    specify unitsPerPixel.

#### PROJECTED_VECTOR_IMAGE_SIZE *= 32768*

#### VECTOR_IMAGE_SIZE *= 262144*

#### *classmethod* addKnownExtensions()

#### cacheName *= 'tilesource'*

#### *property* geospatial

This is true if the source has geospatial information.

#### getBandInformation(statistics=True, dataset=None, \*\*kwargs)

Get information about each band in the image.

* **Parameters:**
  * **statistics** – if True, compute statistics if they don’t already
    exist.  Ignored: always treated as True.
  * **dataset** – the dataset.  If None, use the main dataset.
* **Returns:**
  a list of one dictionary per band.  Each dictionary contains
  known values such as interpretation, min, max, mean, stdev, nodata,
  scale, offset, units, categories, colortable, maskband.

#### getBounds(srs=None)

Returns bounds of the image.

* **Parameters:**
  **srs** – the projection for the bounds.  None for the default 4326.
* **Returns:**
  an object with the four corners and the projection that was
  used.  None if we don’t know the original projection.

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
  **kwargs** – optional arguments.  Some options are region, output,
  encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
  tileIterator.
* **Returns:**
  a dictionary with the value of the pixel for each channel on
  a scale of [0-255], including alpha, if available.  This may
  contain additional information.

#### getProj4String()

Returns proj4 string for the given dataset

* **Returns:**
  The proj4 string or None.

#### getRegion(format=('image',), \*\*kwargs)

Get a rectangular region from the current tile source.  Aspect ratio is
preserved.  If neither width nor height is given, the original size of
the highest resolution level is used.  If both are given, the returned
image will be no larger than either size.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats.
    Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
    TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding may be
    specified.
  * **kwargs** – optional arguments.  Some options are region, output,
    encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
    tileIterator.
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

Check if a GDAL Dataset or file path is likely to be geospatial.

* **Parameters:**
  **ds** – A GDAL Dataset or the path to the file
* **Returns:**
  True if geospatial.

#### name *= 'gdal'*

#### pixelToProjection(x, y, level=None)

Convert from pixels back to projection coordinates.

* **Parameters:**
  * **y** (*x* *,*) – base pixel coordinates.
  * **level** – the level of the pixel.  None for maximum level.
* **Returns:**
  x, y in projection coordinates.

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### toNativePixelCoordinates(x, y, proj=None, roundResults=True)

Convert a coordinate in the native projection (self.getProj4String) to
pixel coordinates.

* **Parameters:**
  * **x** – the x coordinate it the native projection.
  * **y** – the y coordinate it the native projection.
  * **proj** – input projection.  None to use the source’s projection.
  * **roundResults** – if True, round the results to the nearest pixel.
* **Returns:**
  (x, y) the pixel coordinate.

#### unitsAcrossLevel0 *: float*

#### validateCOG(check_tiled=True, full_check=False, strict=True, warn=True) → bool

Check if this image is a valid Cloud Optimized GeoTiff.

This will raise a [`large_image.exceptions.TileSourceInefficientError`](../large_image/large_image.md#large_image.exceptions.TileSourceInefficientError)
if not a valid Cloud Optimized GeoTiff. Otherwise, returns True.

Requires the `osgeo_utils` package.

* **Parameters:**
  * **check_tiled** (*bool*) – Set to False to ignore missing tiling.
  * **full_check** (*bool*) – Set to True to check tile/strip leader/trailer bytes.
    Might be slow on remote files
  * **strict** (*bool*) – Enforce warnings as exceptions. Set to False to only warn and not
    raise exceptions.
  * **warn** (*bool*) – Log any warnings

### large_image_source_gdal.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_gdal.open(\*args, \*\*kwargs)

Create an instance of the module class.
