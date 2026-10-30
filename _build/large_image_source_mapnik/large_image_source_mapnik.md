# large_image_source_mapnik package

## Submodules

## large_image_source_mapnik.girder_source module

### *class* large_image_source_mapnik.girder_source.MapnikGirderTileSource(\*args, \*\*kwargs)

Bases: [`MapnikFileTileSource`](#large_image_source_mapnik.MapnikFileTileSource), [`GDALGirderTileSource`](../large_image_source_gdal/large_image_source_gdal.md#large_image_source_gdal.girder_source.GDALGirderTileSource)

Provides tile access to Girder items for mapnik layers.

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
  * **style** – 

    if None, use the default style for the file.  Otherwise,
    this is a string with a json-encoded dictionary.  The style is
    ignored if it does not contain ‘band’ or ‘bands’.  In addition to
    the base class parameters, the style can also contain the following
    keys:
    > scheme: one of the mapnik.COLORIZER_xxx values.  Case
    > : insensitive.  Possible values are at least ‘discrete’,
    >   ‘linear’, and ‘exact’.  This defaults to ‘linear’.

    > composite: this is a string containing one of the mapnik
    > : CompositeOp properties.  It defaults to ‘lighten’.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.  Ignored
    if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326
    converted to the projection divided by the tile size.  Proj4
    projections that are not latlong (is_geographic is False) must
    specify unitsPerPixel.

#### cacheName *= 'tilesource'*

#### name *= 'mapnik'*

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### unitsAcrossLevel0 *: float*

## Module contents

### *class* large_image_source_mapnik.MapnikFileTileSource(\*args, \*\*kwargs)

Bases: [`GDALFileTileSource`](../large_image_source_gdal/large_image_source_gdal.md#large_image_source_gdal.GDALFileTileSource)

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
  * **style** – 

    if None, use the default style for the file.  Otherwise,
    this is a string with a json-encoded dictionary.  The style is
    ignored if it does not contain ‘band’ or ‘bands’.  In addition to
    the base class parameters, the style can also contain the following
    keys:
    > scheme: one of the mapnik.COLORIZER_xxx values.  Case
    > : insensitive.  Possible values are at least ‘discrete’,
    >   ‘linear’, and ‘exact’.  This defaults to ‘linear’.

    > composite: this is a string containing one of the mapnik
    > : CompositeOp properties.  It defaults to ‘lighten’.
  * **unitsPerPixel** – The size of a pixel at the 0 tile size.  Ignored
    if the projection is None.  For projections, None uses the default,
    which is the distance between (-180,0) and (180,0) in EPSG:4326
    converted to the projection divided by the tile size.  Proj4
    projections that are not latlong (is_geographic is False) must
    specify unitsPerPixel.

#### addStyle(m, layerSrs, extent=None)

Attaches raster style option to mapnik raster layer and adds the layer
to the mapnik map.

* **Parameters:**
  * **m** – mapnik map.
  * **layerSrs** – the layer projection
  * **extent** – the extent to use for the mapnik layer.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'nc': SourcePriority.PREFERRED, 'nitf': SourcePriority.HIGHER, 'ntf': SourcePriority.HIGHER, 'tif': SourcePriority.LOWER, 'tiff': SourcePriority.LOWER, 'vrt': SourcePriority.HIGHER, None: SourcePriority.LOW}*

#### getOneBandInformation(band)

Get band information for a single band.

* **Parameters:**
  **band** – a 1-based band.
* **Returns:**
  a dictionary of band information.  See getBandInformation.

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

#### *static* interpolateMinMax(start, stop, count)

Returns interpolated values for a given
start, stop and count

* **Returns:**
  List of interpolated values

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/geotiff': SourcePriority.HIGHER, 'image/tiff': SourcePriority.LOWER, 'image/x-tiff': SourcePriority.LOWER, None: SourcePriority.FALLBACK}*

#### name *= 'mapnik'*

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### unitsAcrossLevel0 *: float*

### large_image_source_mapnik.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_mapnik.open(\*args, \*\*kwargs)

Create an instance of the module class.
