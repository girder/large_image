# large_image.tilesource package

## Subpackages

* [large_image.tilesource.eager_utils package](large_image.tilesource.eager_utils.md)
  * [Submodules](large_image.tilesource.eager_utils.md#submodules)
  * [large_image.tilesource.eager_utils.eager_fn module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_fn)
    * [`get_transform()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_fn.get_transform)
    * [`get_transform_scale()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_fn.get_transform_scale)
    * [`set_transform()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_fn.set_transform)
    * [`set_transform_scale()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_fn.set_transform_scale)
  * [large_image.tilesource.eager_utils.eager_image_modifications module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_image_modifications)
    * [`pad_chunk_if_necessary()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.pad_chunk_if_necessary)
    * [`pad_color()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.pad_color)
    * [`pad_region_chunk()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.pad_region_chunk)
    * [`pad_tile()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.pad_tile)
    * [`padding()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.padding)
    * [`remove_unnecessary_image_information()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.remove_unnecessary_image_information)
    * [`return_constant_color()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.return_constant_color)
    * [`return_needed_padding_equal()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_equal)
    * [`return_needed_padding_right_bottom()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_right_bottom)
    * [`return_needed_padding_wsi_edge()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_wsi_edge)
    * [`rgba2rgb()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_image_modifications.rgba2rgb)
  * [large_image.tilesource.eager_utils.eager_pytorch_threading_context module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_pytorch_threading_context)
  * [large_image.tilesource.eager_utils.eager_read_args module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_read_args)
    * [`check_edge_condition()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.check_edge_condition)
    * [`chunks_from_kd_tree()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.chunks_from_kd_tree)
    * [`default_region_coords_and_target_scale_from_read_args()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.default_region_coords_and_target_scale_from_read_args)
    * [`gen_read_args_complete_grid()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.gen_read_args_complete_grid)
    * [`gen_read_args_for_regions()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.gen_read_args_for_regions)
    * [`gen_read_args_for_tiles()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.gen_read_args_for_tiles)
    * [`gen_read_args_incomplete_grid()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.gen_read_args_incomplete_grid)
    * [`sparse_chunks()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_read_args.sparse_chunks)
  * [large_image.tilesource.eager_utils.eager_shared_array module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_shared_array)
    * [`SharedArray`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray)
      * [`SharedArray.close()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.close)
      * [`SharedArray.copy()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.copy)
      * [`SharedArray.insert()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.insert)
      * [`SharedArray.insert_mm()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.insert_mm)
      * [`SharedArray.mm_view()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.mm_view)
      * [`SharedArray.resize_shm()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.resize_shm)
      * [`SharedArray.tobytes()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.tobytes)
      * [`SharedArray.view()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_shared_array.SharedArray.view)
  * [large_image.tilesource.eager_utils.eager_wsi_operations module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_wsi_operations)
    * [`calculate_slide_dimensions()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.calculate_slide_dimensions)
    * [`generate_assumptions_for_x_y_given_mag()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.generate_assumptions_for_x_y_given_mag)
    * [`get_base_mm_from_meta()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.get_base_mm_from_meta)
    * [`get_patch_from_mask_for_tile()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.get_patch_from_mask_for_tile)
    * [`get_scaling_values_from_meta()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.get_scaling_values_from_meta)
    * [`get_smallest_bounding_box()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.get_smallest_bounding_box)
    * [`return_relevant_tile_indexes_for_slide_dim()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.return_relevant_tile_indexes_for_slide_dim)
    * [`return_target_scaling_feature()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.return_target_scaling_feature)
    * [`return_tile_slides_meeting_area_threshold()`](large_image.tilesource.eager_utils.md#large_image.tilesource.eager_utils.eager_wsi_operations.return_tile_slides_meeting_area_threshold)
  * [Module contents](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils)

## Submodules

## large_image.tilesource.base module

### *class* large_image.tilesource.base.FileTileSource(path: str | Path | dict[Any, Any], \*args, \*\*kwargs)

Bases: [`TileSource`](#large_image.tilesource.base.TileSource)

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### *classmethod* addKnownMimetypes() → None

Based on already listed extensions and a set of common extension-
mimetype list, add mimetypes if they do not already exist.

#### *classmethod* canRead(path: str | Path | dict[Any, Any], \*args, \*\*kwargs) → bool

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it
  cannot.

#### *static* getLRUHash(\*args, \*\*kwargs) → str

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getState() → str

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

### *class* large_image.tilesource.base.TileSource(encoding: str | None = None, jpegQuality: int = 95, jpegSubsampling: int = 0, tiffCompression: str = 'raw', edge: bool | str = False, style: str | dict[str, int] | None = None, noCache: bool | None = None, \*args, \*\*kwargs)

Bases: [`IPyLeafletMixin`](#large_image.tilesource.jupyter.IPyLeafletMixin)

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

#### axesToFrame(\*\*kwargs: int) → int

Given values on some or all of the axes, return the corresponding frame
number.  Any unspecified axis is 0.  If one of the specified axes is
‘frame’, this is just returned and the other values are ignored.

* **Parameters:**
  **kwargs** – axes with position values.
* **Returns:**
  a frame number.

#### *property* bandCount *: int | None*

#### *classmethod* canRead(\*args, \*\*kwargs) → bool

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it cannot.

#### *property* channelNames *: list[str] | None*

If known, return a list of channel names.

* **Returns:**
  either None or a list of channel names as strings.

#### convertRegionScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, cropToImage: bool = True) → dict[str, Any]

Convert a region from one scale to another.

* **Parameters:**
  * **sourceRegion** – 

    a dictionary of optional values which specify the
    part of an image to process.
    * **left:**
      the left edge (inclusive) of the region to process.
    * **top:**
      the top edge (inclusive) of the region to process.
    * **right:**
      the right edge (exclusive) of the region to process.
    * **bottom:**
      the bottom edge (exclusive) of the region to process.
    * **width:**
      the width of the region to process.
    * **height:**
      the height of the region to process.
    * **units:**
      either ‘base_pixels’ (default), ‘pixels’, ‘mm’, or
      ‘fraction’.  base_pixels are in maximum resolution pixels.
      pixels is in the specified magnification pixels.  mm is in the
      specified magnification scale.  fraction is a scale of 0 to 1.
      pixels and mm are only available if the magnification and mm
      per pixel are defined for the image.
  * **sourceScale** – 

    a dictionary of optional values which specify the
    scale of the source region.  Required if the sourceRegion is
    in “mag_pixels” units.
    * **magnification:**
      the magnification ratio.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
  * **targetScale** – 

    a dictionary of optional values which specify the
    scale of the target region.  Required in targetUnits is in
    “mag_pixels” units.
    * **magnification:**
      the magnification ratio.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
  * **targetUnits** – if not None, convert the region to these units.
    Otherwise, the units are will either be the sourceRegion units if
    those are not “mag_pixels” or base_pixels.  If “mag_pixels”, the
    targetScale must be specified.
  * **cropToImage** – if True, don’t return region coordinates outside of
    the image.

#### *property* dtype *: dtype*

#### eagerIterator(\*\*kwargs) → [EagerIterator](#large_image.tilesource.eageriterator.EagerIterator)

Create an eager iterator for batched tile or region reads.

The eager iterator is intended for AI and machine-learning workflows that need
prefetched numpy or torch batches from a Large Image tile source. It supports tile
mode and explicit region mode, optional masking, scaling, padding, transforms,
and dynamic transform-scale callbacks.

* **Parameters:**
  **kwargs** – EagerIterator options such as output_mode, tile_overlap, mask,
  region, scale, tile_size, region_size, source_scale, dtype, chunk_mult,
  edge, pad_mode, pad_fill_mode, nchw, batch, prefetch, workers, tiles,
  regions, transform, randomize_chunks, seed, area_threshold, threshold_mask,
  transform_save_mode, and transform_scale.
* **Returns:**
  An EagerIterator. Each iteration returns a dictionary with ‘tile’ as a
  SharedArray plus tile metadata including format, gx, gy, level_x, level_y,
  tile_position, width, height, level, magnification, mm_x, mm_y, gwidth, and
  gheight.

#### extensions *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### frameToAxes(frame: int) → dict[str, int]

Given a frame number, return a dictionary of axes values.  If unknown,
this is just ‘frame’: frame.

* **Parameters:**
  **frame** – a frame number.
* **Returns:**
  a dictionary of axes that specify the frame.

#### *property* frames *: int*

A property with the number of frames.

#### *property* geospatial *: bool*

#### getAssociatedImage(imageKey: str, \*args, \*\*kwargs) → tuple[[ImageBytes](#large_image.tilesource.utilities.ImageBytes), str] | None

Return an associated image.

* **Parameters:**
  * **imageKey** – the key of the associated image to retrieve.
  * **kwargs** – optional arguments.  Some options are width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  imageData, imageMime: the image data and the mime type, or
  None if the associated image doesn’t exist.

#### getAssociatedImagesList() → list[str]

Return a list of associated images.

* **Returns:**
  the list of image keys.

#### getBandInformation(statistics: bool = False, \*\*kwargs) → dict[int, Any]

Get information about each band in the image.

* **Parameters:**
  **statistics** – if True, compute statistics if they don’t already
  exist.
* **Returns:**
  a dictionary of one dictionary per band.  Each dictionary
  contains known values such as interpretation, min, max, mean,
  stdev.

#### getBounds(\*args, \*\*kwargs) → dict[str, Any]

#### getCenter(\*args, \*\*kwargs) → tuple[float, float]

Returns (Y, X) center location.

#### getGeospatialRegion(src_projection: str, src_gcps: list[tuple[float] | list[float]], dest_projection: str, dest_region: dict[str, float], \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

This function requires pyproj and either rasterio or gdal; it allows
specifying georeferencing (even for non-geospatial images) and
retrieving a region from geospatial coordinates.  In addition to the
required georeferencing parameters described below, this takes the same
parameters as getRegion.

* **Parameters:**
  * **src_projection** – A string describing the coordinate reference
    system used for src_gcps. This string can be an EPSG code or other
    format accepted by pyproj.CRS.from_string.
  * **src_gcps** – A list of ground control points describing projected
    coordinates for certain pixel coordinates in the image. Each GCP
    can be a list or tuple with the following format: (cx, cy, px, py)
    where (cx, cy) is a projected coordinate in the coordinate
    reference system described by src_projection and (px, py) is a
    pixel coordinate within the extents of the image.
  * **dest_projection** – A string describing the coordinate reference
    system used for dest_region. This string can be an EPSG code or
    other format accepted by pyproj.CRS.from_string.
  * **dest_region** – A dictionary describing the desired region to
    retrieve from the image.  Must specify values for “top”, “bottom”,
    “left”, and “right” in the projected coordinate system specified by
    dest_projection.
  * **kwargs** – Optional arguments passed to getRegion.
* **Returns:**
  regionData, formatOrRegionMime: the image data and either the
  mime type, if the format is TILE_FORMAT_IMAGE, or the format.

#### getICCProfiles(idx: int | None = None, onlyInfo: bool = False) → None | ImageCmsProfile | list[ImageCmsProfile | None]

Get a list of all ICC profiles that are available for the source, or
get a specific profile.

* **Parameters:**
  * **idx** – a 0-based index into the profiles to get one profile, or
    None to get a list of all profiles.
  * **onlyInfo** – if idx is None and this is true, just return the
    profile information.
* **Returns:**
  either one or a list of PIL.ImageCms.CmsProfile objects, or
  None if no profiles are available.  If a list, entries in the list
  may be None.

#### getInternalMetadata(\*\*kwargs) → dict[Any, Any] | None

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### *static* getLRUHash(\*args, \*\*kwargs) → str

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getLevelForMagnification(magnification: float | None = None, exact: bool = False, mm_x: float | None = None, mm_y: float | None = None, rounding: str | bool | None = 'round', \*\*kwargs) → int | float | None

Get the level for a specific magnification or pixel size.  If the
magnification is unknown or no level is sufficient resolution, and an
exact match is not requested, the highest level will be returned.

If none of magnification, mm_x, and mm_y are specified, the maximum
level is returned.  If more than one of these values is given, an
average of those given will be used (exact will require all of them to
match).

* **Parameters:**
  * **magnification** – the magnification ratio.
  * **exact** – if True, only a level that matches exactly will be
    returned.
  * **mm_x** – the horizontal size of a pixel in millimeters.
  * **mm_y** – the vertical size of a pixel in millimeters.
  * **rounding** – if False, a fractional level may be returned.  If
    ‘ceil’ or ‘round’, that function is used to convert the level to an
    integer (the exact flag still applies).  If None, the level is not
    cropped to the actual image’s level range.
* **Returns:**
  the selected level or None for no match.

#### getMagnificationForLevel(level: float | None = None) → dict[str, float | None]

Get the magnification at a particular level.

* **Parameters:**
  **level** – None to use the maximum level, otherwise the level to get
  the magnification factor of.
* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getMetadata() → [JSONDict](#large_image.tilesource.utilities.JSONDict)

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

#### getNativeMagnification() → dict[str, float | None]

Get the magnification for the highest-resolution level.

* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getOneBandInformation(band: int) → dict[str, Any]

Get band information for a single band.

* **Parameters:**
  **band** – a 1-based band.
* **Returns:**
  a dictionary of band information.  See getBandInformation.

#### getPixel(includeTileRecord: bool = False, \*\*kwargs) → [JSONDict](#large_image.tilesource.utilities.JSONDict)

Get a single pixel from the current tile source.

* **Parameters:**
  * **includeTileRecord** – if True, include the tile used for computing
    the pixel in the response.
  * **kwargs** – optional arguments.  Some options are region, output,
    encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
    tileIterator.
* **Returns:**
  a dictionary with the value of the pixel for each channel on
  a scale of [0-255], including alpha, if available.  This may
  contain additional information.

#### getPointAtAnotherScale(point: tuple[float, float], sourceScale: dict[str, float] | None = None, sourceUnits: str | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → tuple[float, float]

Given a point as a (x, y) tuple, convert it from one scale to another.
The sourceScale, sourceUnits, targetScale, and targetUnits parameters
are the same as convertRegionScale, where sourceUnits are the units
used with sourceScale.

#### getPreferredLevel(level: int) → int

Given a desired level (0 is minimum resolution, self.levels - 1 is max
resolution), return the level that contains actual data that is no
lower resolution.

* **Parameters:**
  **level** – desired level
* **Returns level:**
  a level with actual data that is no lower resolution.

#### getRegion(format: str | tuple[str] = ('image',), \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

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

#### getRegionAtAnotherScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

This takes the same parameters and returns the same results as
getRegion, except instead of region and scale, it takes sourceRegion,
sourceScale, targetScale, and targetUnits.  These parameters are the
same as convertRegionScale.  See those two functions for parameter
definitions.

#### getSingleTile(\*args, \*\*kwargs) → [LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict) | None

Return any single tile from an iterator.  This takes exactly the same
parameters as tileIterator.  Use tile_position to get a specific tile,
otherwise the first tile is returned.

* **Returns:**
  a tile dictionary or None.

#### getSingleTileAtAnotherScale(\*args, \*\*kwargs) → [LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict) | None

Return any single tile from a rescaled iterator.  This takes exactly
the same parameters as tileIteratorAtAnotherScale.  Use tile_position
to get a specific tile, otherwise the first tile is returned.

* **Returns:**
  a tile dictionary or None.

#### getState() → str

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

#### getThumbnail(width: str | int | None = None, height: str | int | None = None, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

Get a basic thumbnail from the current tile source.  Aspect ratio is
preserved.  If neither width nor height is given, a default value is
used.  If both are given, the thumbnail will be no larger than either
size.  A thumbnail has the same options as a region except that it
always includes the entire image and has a default size of 256 x 256.

* **Parameters:**
  * **width** – maximum width in pixels.
  * **height** – maximum height in pixels.
  * **kwargs** – optional arguments.  Some options are encoding,
    jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  thumbData, thumbMime: the image data and the mime type.

#### getTile(x: int, y: int, z: int, pilImageAllowed: bool = False, numpyAllowed: bool | str = False, sparseFallback: bool = False, frame: int | None = None) → [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | Image | bytes | ndarray

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

#### getTileCount(\*args, \*\*kwargs) → int

Return the number of tiles that the tileIterator will return.  See
tileIterator for parameters.

* **Returns:**
  the number of tiles that the tileIterator will yield.

#### getTileMimeType() → str

Return the default mimetype for image tiles.

* **Returns:**
  the mime type of the tile.

#### histogram(dtype: type[Any] | dtype[Any] | \_HasDType[dtype[Any]] | \_HasNumPyDType[dtype[Any]] | tuple[Any, Any] | list[Any] | \_DTypeDict | str | None = None, onlyMinMax: bool = False, bins: int = 256, density: bool = False, format: Any = None, \*args, \*\*kwargs) → dict[str, ndarray | list[dict[str, Any]]]

Get a histogram for a region.

* **Parameters:**
  * **dtype** – if specified, the tiles must be this numpy.dtype.
  * **onlyMinMax** – if True, only return the minimum and maximum value
    of the region.
  * **bins** – the number of bins in the histogram.  This is passed to
    numpy.histogram, but needs to produce the same set of edges for
    each tile.
  * **density** – if True, scale the results based on the number of
    samples.
  * **format** – ignored.  Used to override the format for the
    tileIterator.
  * **range** – if None, use the computed min and (max + 1).  Otherwise,
    this is the range passed to numpy.histogram.  Note this is only
    accessible via kwargs as it otherwise overloads the range function.
    If ‘round’, use the computed values, but the number of bins may be
    reduced or the bin_edges rounded to integer values for
    integer-based source data.
  * **args** – parameters to pass to the tileIterator.
  * **kwargs** – parameters to pass to the tileIterator.
* **Returns:**
  if onlyMinMax is true, this is a dictionary with keys min and
  max, each of which is a numpy array with the minimum and maximum of
  all of the bands.  If onlyMinMax is False, this is a dictionary
  with a single key ‘histogram’ that contains a list of histograms
  per band.  Each entry is a dictionary with min, max, range, hist,
  bins, and bin_edges.  range is [min, (max + 1)].  hist is the
  counts (normalized if density is True) for each bin.  bins is the
  number of bins used.  bin_edges is an array one longer than the
  hist array that contains the boundaries between bins.

#### levels *: int*

#### *property* metadata *: [JSONDict](#large_image.tilesource.utilities.JSONDict)*

#### mimeTypes *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### name *= None*

#### nameMatches *: dict[str, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {}*

#### newPriority *: [SourcePriority](large_image.md#large_image.constants.SourcePriority) | None* *= None*

#### sizeX *: int*

#### sizeY *: int*

#### *property* style *: [JSONDict](#large_image.tilesource.utilities.JSONDict) | None*

#### tileFrames(format: str | tuple[str] = ('image',), frameList: list[int] | None = None, framesAcross: int | None = None, max_workers: int | None = -4, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

Given the parameters for getRegion, plus a list of frames and the
number of frames across, make a larger image composed of a region from
each listed frame composited together.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats.
    Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
    TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding may be
    specified.
  * **frameList** – None for all frames, or a list of 0-based integers.
  * **framesAcross** – the number of frames across the final image.  If
    unspecified, this is the ceiling of sqrt(number of frames in frame
    list).
  * **kwargs** – optional arguments.  Some options are region, output,
    encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
    tileIterator.
  * **max_workers** – maximum workers for parallelism.  If negative, use
    the minimum of the absolute value of this number or
    multiprocessing.cpu_count().
* **Returns:**
  regionData, formatOrRegionMime: the image data and either the
  mime type, if the format is TILE_FORMAT_IMAGE, or the format.

#### tileHeight *: int*

#### tileIterator(format: str | tuple[str] = ('numpy',), resample: bool = True, \*\*kwargs) → Iterator[[LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict)]

Iterate on all tiles in the specified region at the specified scale.
Each tile is returned as part of a dictionary that includes

> * **x, y:**
>   (left, top) coordinates in current magnification pixels
> * **width, height:**
>   size of current tile in current magnification pixels
> * **tile:**
>   cropped tile image
> * **format:**
>   format of the tile
> * **level:**
>   level of the current tile
> * **level_x, level_y:**
>   the tile reference number within the level.
>   Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
>   yielded may not be (0, 0) if a region is specified.
> * **tile_position:**
>   a dictionary of the tile position within the
>   iterator, containing:
>   * **level_x, level_y:**
>     the tile reference number within the level.
>   * **region_x, region_y:**
>     0, 0 is the first tile in the full
>     iteration (when not restricting the iteration to a single
>     tile).
>   * **position:**
>     a 0-based value for the tile within the full
>     iteration.
> * **iterator_range:**
>   a dictionary of the output range of the iterator:
>   * **level_x_min, level_x_max:**
>     the tiles that are be included
>     during the full iteration: [layer_x_min, layer_x_max).
>   * **level_y_min, level_y_max:**
>     the tiles that are be included
>     during the full iteration: [layer_y_min, layer_y_max).
>   * **region_x_max, region_y_max:**
>     the number of tiles included during
>     the full iteration.   This is layer_x_max - layer_x_min,
>     layer_y_max - layer_y_min.
>   * **position:**
>     the total number of tiles included in the full
>     iteration.  This is region_x_max \* region_y_max.
> * **magnification:**
>   magnification of the current tile
> * **mm_x, mm_y:**
>   size of the current tile pixel in millimeters.
> * **gx, gy:**
>   (left, top) coordinates in maximum-resolution pixels
> * **gwidth, gheight:**
>   size of of the current tile in maximum-resolution
>   pixels.
> * **tile_overlap:**
>   the amount of overlap with neighboring tiles (left,
>   top, right, and bottom).  Overlap never extends outside of the
>   requested region.

If a region that includes partial tiles is requested, those tiles are
cropped appropriately.  Most images will have tiles that get cropped
along the right and bottom edges in any case.  If an exact
magnification or scale is requested, no tiles will be returned.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats.
    Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
    TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding must be
    specified.
  * **resample** – 

    If True or one of PIL.Image.Resampling.NEAREST,
    LANCZOS, BILINEAR, or BICUBIC to resample tiles that are not the
    target output size.  Tiles that are resampled will have additional
    dictionary entries of:
    * **scaled:**
      the scaling factor that was applied (less than 1 is
      downsampled).
    * **tile_x, tile_y:**
      (left, top) coordinates before scaling
    * **tile_width, tile_height:**
      size of the current tile before
      scaling.
    * **tile_magnification:**
      magnification of the current tile before
      scaling.
    * **tile_mm_x, tile_mm_y:**
      size of a pixel in a tile in millimeters
      before scaling.

    Note that scipy.misc.imresize uses PIL internally.
  * **region** – 

    a dictionary of optional values which specify the part
    of the image to process:
    * **left:**
      the left edge (inclusive) of the region to process.
    * **top:**
      the top edge (inclusive) of the region to process.
    * **right:**
      the right edge (exclusive) of the region to process.
    * **bottom:**
      the bottom edge (exclusive) of the region to process.
    * **width:**
      the width of the region to process.
    * **height:**
      the height of the region to process.
    * **units:**
      either ‘base_pixels’ (default), ‘pixels’, ‘mm’, or
      ‘fraction’.  base_pixels are in maximum resolution pixels.
      pixels is in the specified magnification pixels.  mm is in the
      specified magnification scale.  fraction is a scale of 0 to 1.
      pixels and mm are only available if the magnification and mm
      per pixel are defined for the image.  For geospatial sources,
      this can also be ‘projection’, or a case-insensitive string
      starting with ‘proj4:’, ‘epsg:’ or a enumerated value like
      ‘wgs84’.
    * **unitsWH:**
      if not specified, this is the same as units.
      Otherwise, these units will be used for the width and height if
      specified.  If can take the same values as units.
  * **output** – 

    a dictionary of optional values which specify the size
    of the output.
    * **maxWidth:**
      maximum width in pixels.  If either maxWidth or maxHeight
      is specified, magnification, mm_x, and mm_y are ignored.
    * **maxHeight:**
      maximum height in pixels.
  * **scale** – 

    a dictionary of optional values which specify the scale
    of the region and / or output.  This applies to region if
    pixels or mm are used for inits.  It applies to output if
    neither output maxWidth nor maxHeight is specified.
    * **magnification:**
      the magnification ratio.  Only used if maxWidth and
      maxHeight are not specified or None.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
    * **exact:**
      if True, only a level that matches exactly will be returned.
      This is only applied if magnification, mm_x, or mm_y is used.
  * **tile_position** – if present, either a number to only yield the
    (tile_position)th tile [0 to (xmax - min) \* (ymax - ymin)) that the
    iterator would yield, or a dictionary of {region_x, region_y} to
    yield that tile, where 0, 0 is the first tile yielded, and
    xmax - xmin - 1, ymax - ymin - 1 is the last tile yielded, or a
    dictionary of {level_x, level_y} to yield that specific tile if it
    is in the region.
  * **tile_size** – 

    if present, retile the output to the specified tile
    size.  If only width or only height is specified, the resultant
    tiles will be square.  This is a dictionary containing at least
    one of:
    * **width:**
      the desired tile width.
    * **height:**
      the desired tile height.
  * **tile_overlap** – 

    if present, retile the output adding a symmetric
    overlap to the tiles.  If either x or y is not specified, it
    defaults to zero.  The overlap does not change the tile size,
    only the stride of the tiles.  This is a dictionary containing:
    * **x:**
      the horizontal overlap in pixels.
    * **y:**
      the vertical overlap in pixels.
    * **edges:**
      if True, then the edge tiles will exclude the overlap
      distance.  If unset or False, the edge tiles are full size.

      The overlap is conceptually split between the two sides of
      the tile.  This is only relevant to where overlap is reported
      or if edges is True

      As an example, suppose an image that is 8 pixels across
      (01234567) and a tile size of 5 is requested with an overlap of
      4.  If the edges option is False (the default), the following
      tiles are returned: 01234, 12345, 23456, 34567.  Each tile
      reports its overlap, and the non-overlapped area of each tile
      is 012, 3, 4, 567.  If the edges option is True, the tiles
      returned are: 012, 0123, 01234, 12345, 23456, 34567, 4567, 567,
      with the non-overlapped area of each as 0, 1, 2, 3, 4, 5, 6, 7.
  * **tile_offset** – 

    if present, adjust tile positions so that the
    corner of one tile is at the specified location.
    * **left:**
      the left offset in pixels.
    * **top:**
      the top offset in pixels.
    * **auto:**
      a boolean, if True, automatically set the offset to align
      with the region’s left and top.
  * **encoding** – if format includes TILE_FORMAT_IMAGE, a valid PIL
    encoding (typically ‘PNG’, ‘JPEG’, or ‘TIFF’) or ‘TILED’ (identical
    to TIFF).  Must also be in the TileOutputMimeTypes map.
  * **jpegQuality** – the quality to use when encoding a JPEG.
  * **jpegSubsampling** – the subsampling level to use when encoding a
    JPEG.
  * **tiffCompression** – the compression format when encoding a TIFF.
    This is usually ‘raw’, ‘tiff_lzw’, ‘jpeg’, or ‘tiff_adobe_deflate’.
    Some of these are aliased: ‘none’, ‘lzw’, ‘deflate’.
  * **frame** – the frame number within the tile source.  None is the
    same as 0 for multi-frame sources.
  * **kwargs** – optional arguments.
* **Yields:**
  an iterator that returns a dictionary as listed above.

#### tileIteratorAtAnotherScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → Iterator[[LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict)]

This takes the same parameters and returns the same results as
tileIterator, except instead of region and scale, it takes
sourceRegion, sourceScale, targetScale, and targetUnits.  These
parameters are the same as convertRegionScale.  See those two functions
for parameter definitions.

#### tileWidth *: int*

#### wrapKey(\*args, \*\*kwargs) → str

Return a key for a tile source and function parameters that can be used
as a unique cache key.

* **Parameters:**
  * **args** – arguments to add to the hash.
  * **kwaths** – arguments to add to the hash.
* **Returns:**
  a cache key.

## large_image.tilesource.eageriterator module

Eager iterator implementation for batched tile and region reads.

### *class* large_image.tilesource.eageriterator.EagerIterator(source: [TileSource](#large_image.tilesource.base.TileSource), output_mode: str = 'tiles', tile_overlap: dict[str, int] | dict[str, float] | None=None, mask: ndarray | str | PathLike | None = None, region: dict[str, ~typing.Any] | None=None, scale: dict[str, ~typing.Any] | None=None, tile_size: dict[str, int] | None=None, region_size: dict[str, int] | None=None, source_scale: dict[str, ~typing.Any] | None=None, dtype: type[~typing.Any] | ~numpy.dtype[~typing.Any] | ~numpy._typing._dtype_like._HasDType[~numpy.dtype[~typing.Any]] | ~numpy._typing._dtype_like._HasNumPyDType[~numpy.dtype[~typing.Any]] | tuple[~typing.Any, ~typing.Any] | list[~typing.Any] | ~numpy._typing._dtype_like._DTypeDict | str=<class 'numpy.uint8'>, chunk_mult: int = 2, edge: bool = False, pad_mode: str = 'wsi_edge', pad_fill_mode: str = 'default', nchw: bool = False, batch: int = 64, prefetch: int = 16, workers: int = 16, tiles: list | ndarray | None = None, regions: list | ndarray | None = None, transform: Callable | None = None, randomize_chunks: bool = False, seed: int = 42, area_threshold: float = 0.25, threshold_mask: float = 100, transform_save_mode: str | None = 'tile_x_y', transform_scale: Callable | None = None)

Bases: `object`

Iterator that prefetches batched Large Image tile or region reads.

Initialize an eager iterator for batched tile or region reads.

* **Parameters:**
  * **source** – Tile source used to read image data.
  * **output_mode** – Output mode, either ‘tiles’ or ‘regions’.
  * **tile_overlap** – Optional x and y tile overlap as pixels or fractions.
  * **mask** – Optional whole-slide mask array or mask image path used to filter tiles.
  * **region** – Optional source region with left, top, width, height, and units.
  * **scale** – Optional target scale using magnification or mm_x and mm_y.
  * **tile_size** – Optional output tile size with width and height in pixels.
  * **region_size** – Optional output region size with width and height in pixels.
  * **source_scale** – Source scale used when region units are mag_pixels.
  * **dtype** – Numpy or torch dtype for the output image batch.
  * **chunk_mult** – Chunk side length multiplier; chunk size is chunk_mult squared.
  * **edge** – If True, discard reads that cross image boundaries.
  * **pad_mode** – Padding mode used when reads are smaller than the requested output.
  * **pad_fill_mode** – Fill mode used for padded pixels.
  * **nchw** – If True, output batches use NCHW layout; otherwise NHWC layout.
  * **batch** – Number of tiles or regions returned in each batch.
  * **prefetch** – Number of batches to keep queued ahead of iteration.
  * **workers** – Number of worker processes used for image reads.
  * **tiles** – Optional tile indexes in row, column order for tile output mode.
  * **regions** – Optional regions in top, left, height, width order for region mode.
  * **transform** – Optional transform applied to each tile or region.
  * **randomize_chunks** – If True, randomize chunk order before reading.
  * **seed** – Random seed used when randomize_chunks is True.
  * **area_threshold** – Minimum mask-signal fraction required for a tile.
  * **threshold_mask** – Minimum mask pixel value considered signal.
  * **transform_save_mode** – Coordinate mode passed to three-argument transforms.
  * **transform_scale** – Optional callable that customizes read coordinates and scale.
* **Returns:**
  None. Iteration yields dictionaries containing image data and metadata.

#### cleanup(wait=True)

Shut down worker processes and release queued shared-memory buffers.

* **Parameters:**
  **wait** – If True, wait for submitted worker tasks to finish before shutdown.
* **Returns:**
  None.

#### get_output_image_count()

Return the number of output images planned by this iterator.

* **Returns:**
  Number of tiles or regions available from the iterator.

#### *static* read(source: [TileSource](#large_image.tilesource.base.TileSource), dtype: dtype, nchw: bool, read_kwargs: list, sharrs: list, offset: int, output_mode: str, batch: int, slide_dimensions: dict, region: dict[str, Any] | None = None, transform: Callable | str | None = None, pad_mode: str = 'wsi_edge', pad_fill_mode: str = 'default', callable_arg_num: int | None = None, transform_save_mode: str | None = 'tile_x_y', worker_transform_scale: Callable | str | None = None)

Read one eager chunk into shared-memory output buffers.

* **Parameters:**
  * **source** – Tile source used to read image data.
  * **dtype** – Numpy or torch dtype for output images.
  * **nchw** – If True, write transformed numpy tiles in NCHW layout.
  * **read_kwargs** – Read argument rows for this worker task.
  * **sharrs** – SharedArray buffers filled by this worker task.
  * **offset** – Batch offset for the first output tile in this task.
  * **output_mode** – Output mode, either ‘tiles’ or ‘regions’.
  * **batch** – Number of tiles or regions in each output batch.
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **region** – Optional source region used for tile clipping.
  * **transform** – Optional transform applied to each tile or region.
  * **pad_mode** – Padding mode used when reads are smaller than requested output.
  * **pad_fill_mode** – Fill mode used for padded pixels.
  * **callable_arg_num** – Number of positional arguments expected by transform.
  * **transform_save_mode** – Coordinate mode passed to three-argument transforms.
  * **worker_transform_scale** – Optional worker-safe transform-scale callable.
* **Returns:**
  None. The shared arrays are filled in place.

## large_image.tilesource.geo module

### *class* large_image.tilesource.geo.GDALBaseFileTileSource(path: str | Path | dict[Any, Any], \*args, \*\*kwargs)

Bases: [`GeoBaseFileTileSource`](#large_image.tilesource.geo.GeoBaseFileTileSource)

Abstract base class for GDAL-based tile sources.

This base class assumes the underlying library is powered by GDAL
(rasterio, mapnik, etc.)

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### extensions *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {'geotiff': SourcePriority.PREFERRED, 'nitf': SourcePriority.PREFERRED, 'ntf': SourcePriority.PREFERRED, 'tif': SourcePriority.LOW, 'tiff': SourcePriority.LOW, 'vrt': SourcePriority.PREFERRED, None: SourcePriority.MEDIUM}*

#### *property* geospatial *: bool*

This is true if the source has geospatial information.

#### getBounds(\*args, \*\*kwargs) → dict[str, Any]

#### *static* getHexColors(palette: str | list[str | float | tuple[float, ...]]) → list[str]

Returns list of hex colors for a given color palette

* **Returns:**
  List of colors

#### getNativeMagnification() → dict[str, float | None]

Get the magnification at the base level.

* **Returns:**
  width of a pixel in mm, height of a pixel in mm.

#### getPixelSizeInMeters() → float | None

Get the approximate base pixel size in meters.  This is calculated as
the average scale of the four edges in the WGS84 ellipsoid.

* **Returns:**
  the pixel size in meters or None.

#### getThumbnail(width: str | int | None = None, height: str | int | None = None, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

Get a basic thumbnail from the current tile source.  Aspect ratio is
preserved.  If neither width nor height is given, a default value is
used.  If both are given, the thumbnail will be no larger than either
size.  A thumbnail has the same options as a region except that it
always includes the entire image if there is no projection and has a
default size of 256 x 256.

* **Parameters:**
  * **width** – maximum width in pixels.
  * **height** – maximum height in pixels.
  * **kwargs** – optional arguments.  Some options are encoding,
    jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  thumbData, thumbMime: the image data and the mime type.

#### getTileCorners(z: int, x: float, y: float) → tuple[float, float, float, float]

Returns bounds of a tile for a given x,y,z index.

* **Parameters:**
  * **z** – tile level
  * **x** – tile offset from left.
  * **y** – tile offset from right
* **Returns:**
  (xmin, ymin, xmax, ymax) in the current projection or base
  pixels.

#### *static* isGeospatial(path: str | Path) → bool

Check if a path is likely to be a geospatial file.

* **Parameters:**
  **path** – The path to the file
* **Returns:**
  True if geospatial.

#### mimeTypes *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {'image/geotiff': SourcePriority.PREFERRED, 'image/tiff': SourcePriority.LOW, 'image/x-tiff': SourcePriority.LOW, None: SourcePriority.FALLBACK}*

#### pixelToProjection(\*args, \*\*kwargs) → tuple[float, float]

#### projection *: str | bytes*

#### projectionOrigin *: tuple[float, float]*

#### sourceLevels *: int*

#### sourceSizeX *: int*

#### sourceSizeY *: int*

#### toNativePixelCoordinates(\*args, \*\*kwargs) → tuple[float, float]

#### unitsAcrossLevel0 *: float*

### *class* large_image.tilesource.geo.GeoBaseFileTileSource(path: str | Path | dict[Any, Any], \*args, \*\*kwargs)

Bases: [`FileTileSource`](#large_image.tilesource.base.FileTileSource)

Abstract base class for geospatial tile sources.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

### large_image.tilesource.geo.make_vsi(url: str | Path | dict[Any, Any], \*\*options) → str

## large_image.tilesource.jupyter module

A vanilla REST interface to a `TileSource`.

This is intended for use in JupyterLab and not intended to be used as a full
fledged REST API. Only two endpoints are exposed with minimal options:

* /metadata
* /tile?z={z}&x={x}&y={y}&encoding=png

We use Tornado because it is Jupyter’s web server and will not require Jupyter
users to install any additional dependencies. Also, Tornado doesn’t require us
to manage a separate thread for the web server.

Please note that this webserver will not work with Classic Notebook and will
likely lead to crashes. This is only for use in JupyterLab.

### *class* large_image.tilesource.jupyter.IPyLeafletMixin(\*args, \*\*kwargs)

Bases: `object`

Mixin class to support interactive visualization in JupyterLab.

This class implements `_ipython_display_` with `ipyleaflet` to display
an interactive image visualizer for the tile source in JupyterLab.

Install [ipyleaflet](https://github.com/jupyter-widgets/ipyleaflet) to
interactively visualize tile sources in JupyterLab.

For remote JupyterHub environments, you may need to configure the class
variables `JUPYTER_HOST` or `JUPYTER_PROXY`.

If `JUPYTER_PROXY` is set, it overrides `JUPYTER_HOST`.

Use `JUPYTER_HOST` to set the host name of the machine such that the tile
URL can be accessed at `'http://{JUPYTER_HOST}:{port}'`.

Use `JUPYTER_PROXY` to leverage `jupyter-server-proxy` to proxy the
tile serving port through Jupyter’s authenticated web interface.  This is
useful in Docker and cloud JupyterHub environments.  You can set the
environment variable `LARGE_IMAGE_JUPYTER_PROXY` to control the default
value of `JUPYTER_PROXY`.  If `JUPYTER_PROXY` is set to `True`, the
default will be `'/proxy/` which will work for most Docker Jupyter
configurations. If in a cloud JupyterHub environment, this will get a bit
more nuanced as the `JUPYTERHUB_SERVICE_PREFIX` may need to prefix the
`'/proxy/'`.  If set to `'auto'`, an automatic value will be chosen
through some effort to detect the environment.

To programmatically set these values:

```default
from large_image.tilesource.jupyter import IPyLeafletMixin

# Only set one of these values

# Use a custom domain (avoids port proxying)
IPyLeafletMixin.JUPYTER_HOST = 'mydomain'

# Proxy in a standard JupyterLab environment
IPyLeafletMixin.JUPYTER_PROXY = True  # defaults to `/proxy/`

# Proxy in a cloud JupyterHub environment
IPyLeafletMixin.JUPYTER_PROXY = '/jupyter/user/username/proxy/'
# See if ``JUPYTERHUB_SERVICE_PREFIX`` is in the environment
# variables to improve this
```

#### JUPYTER_HOST *= '127.0.0.1'*

#### JUPYTER_PROXY *: str | bool* *= 'auto'*

#### as_leaflet_layer(\*\*kwargs) → Any

#### *property* iplmap *: Any*

If using ipyleaflets, get access to the map object.

### *class* large_image.tilesource.jupyter.Map(, ts: [IPyLeafletMixin](#large_image.tilesource.jupyter.IPyLeafletMixin) | None = None, metadata: dict | None = None, url: str | None = None, gc: Any | None = None, id: str | None = None, resource: str | None = None)

Bases: `object`

An IPyLeafletMap representation of a large image.

Specify the large image to be used with the IPyLeaflet Map.  One of (a)
a tile source, (b) metadata dictionary and tile url, (c) girder client
and item or file id, or (d) girder client and resource path must be
specified.

* **Parameters:**
  * **ts** – a TileSource.
  * **metadata** – a metadata dictionary as returned by a tile source or
    a girder item/{id}/tiles endpoint.
  * **url** – a slippy map template url to fetch tiles (e.g.,
    …/item/{id}/tiles/zxy/{z}/{x}/{y}?params=…)
  * **gc** – an authenticated girder client.
  * **id** – an item id that exists on the girder client.
  * **resource** – a girder resource path of an item or file that exists
    on the girder client.

#### add_region_indicator()

#### from_map(coordinate: list[float] | tuple[float, float]) → tuple[float, float]

* **Parameters:**
  **coordinate** – a two-tuple that is in the map space coordinates.
* **Returns:**
  a two-tuple that is x, y in pixel space or x, y in image
  projection space.

#### get_frame_histogram(query)

#### *property* id *: str | None*

#### *property* layer *: Any*

#### make_layer(metadata: dict, url: str, \*\*kwargs) → Any

Create an ipyleaflet tile layer given large_image metadata and a tile
url.

#### make_map(metadata: dict, layer: Any | None = None, center: tuple[float, float] | None = None) → Any

Create an ipyleaflet map given large_image metadata, an optional
ipyleaflet layer, and the center of the tile source.

#### *property* map *: Any*

#### *property* metadata *: [JSONDict](#large_image.tilesource.utilities.JSONDict)*

#### to_map(coordinate: list[float] | tuple[float, float]) → tuple[float, float]

Convert a coordinate from the image or projected image space to the map
space.

* **Parameters:**
  **coordinate** – a two-tuple that is x, y in pixel space or x, y in
  image projection space.
* **Returns:**
  a two-tuple that is in the map space coordinates.

#### update_frame(frame, style, \*\*kwargs)

### *class* large_image.tilesource.jupyter.NumpyEncoder(, skipkeys=False, ensure_ascii=True, check_circular=True, allow_nan=True, sort_keys=False, indent=None, separators=None, default=None)

Bases: `JSONEncoder`

Special json encoder for numpy types from [https://stackoverflow.com/a/49677241](https://stackoverflow.com/a/49677241)

Constructor for JSONEncoder, with sensible defaults.

If skipkeys is false, then it is a TypeError to attempt
encoding of keys that are not str, int, float or None.  If
skipkeys is True, such items are simply skipped.

If ensure_ascii is true, the output is guaranteed to be str
objects with all incoming non-ASCII characters escaped.  If
ensure_ascii is false, the output can contain non-ASCII characters.

If check_circular is true, then lists, dicts, and custom encoded
objects will be checked for circular references during encoding to
prevent an infinite recursion (which would cause an RecursionError).
Otherwise, no such check takes place.

If allow_nan is true, then NaN, Infinity, and -Infinity will be
encoded as such.  This behavior is not JSON specification compliant,
but is consistent with most JavaScript based encoders and decoders.
Otherwise, it will be a ValueError to encode such floats.

If sort_keys is true, then the output of dictionaries will be
sorted by key; this is useful for regression tests to ensure
that JSON serializations can be compared on a day-to-day basis.

If indent is a non-negative integer, then JSON array
elements and object members will be pretty-printed with that
indent level.  An indent level of 0 will only insert newlines.
None is the most compact representation.

If specified, separators should be an (item_separator, key_separator)
tuple.  The default is (’, ‘, ‘: ‘) if *indent* is `None` and
(‘,’, ‘: ‘) otherwise.  To get the most compact JSON representation,
you should specify (‘,’, ‘:’) to eliminate whitespace.

If specified, default is a function that gets called for objects
that can’t otherwise be serialized.  It should return a JSON encodable
version of the object or raise a `TypeError`.

#### default(obj)

Implement this method in a subclass such that it returns
a serializable object for `o`, or calls the base implementation
(to raise a `TypeError`).

For example, to support arbitrary iterators, you could
implement default like this:

```default
def default(self, o):
    try:
        iterable = iter(o)
    except TypeError:
        pass
    else:
        return list(iterable)
    # Let the base class default method raise the TypeError
    return super().default(o)
```

### *class* large_image.tilesource.jupyter.RequestManager(tile_source: [IPyLeafletMixin](#large_image.tilesource.jupyter.IPyLeafletMixin))

Bases: `object`

#### *property* port *: int*

#### *property* ports *: tuple[int, ...]*

#### *property* tile_source *: [IPyLeafletMixin](#large_image.tilesource.jupyter.IPyLeafletMixin)*

### large_image.tilesource.jupyter.launch_tile_server(tile_source: [IPyLeafletMixin](#large_image.tilesource.jupyter.IPyLeafletMixin), port: int = 0) → Any

## large_image.tilesource.resample module

### *class* large_image.tilesource.resample.ResampleMethod(value)

Bases: `Enum`

#### NP_MAX *= 9*

#### NP_MAX_COLOR *= 12*

#### NP_MEAN *= 6*

#### NP_MEDIAN *= 7*

#### NP_MIN *= 10*

#### NP_MIN_COLOR *= 13*

#### NP_MODE *= 8*

#### NP_NEAREST *= 11*

#### PIL_BICUBIC *= Resampling.BICUBIC*

#### PIL_BILINEAR *= Resampling.BILINEAR*

#### PIL_BOX *= Resampling.BOX*

#### PIL_HAMMING *= Resampling.HAMMING*

#### PIL_LANCZOS *= Resampling.LANCZOS*

#### PIL_MAX_ENUM *= Resampling.HAMMING*

#### PIL_NEAREST *= Resampling.NEAREST*

### large_image.tilesource.resample.downsampleTileHalfRes(tile: ndarray, resample_method: [ResampleMethod](#large_image.tilesource.resample.ResampleMethod)) → ndarray

### large_image.tilesource.resample.numpyResize(tile: ndarray, new_shape: dict, resample_method: [ResampleMethod](#large_image.tilesource.resample.ResampleMethod)) → ndarray

### large_image.tilesource.resample.pilResize(tile: ndarray, new_shape: dict, resample_method: [ResampleMethod](#large_image.tilesource.resample.ResampleMethod)) → ndarray

## large_image.tilesource.stylefuncs module

### large_image.tilesource.stylefuncs.maskPixelValues(image: ndarray, context: SimpleNamespace, values: list[int | list[int] | tuple[int, ...]], negative: int | None = None, positive: int | None = None) → ndarray

This is a style utility function that returns a black-and-white 8-bit image
where the image is white if the pixel of the source image is in a list of
values and black otherwise.  The values is a list where each entry can
either be a tuple the same length as the band dimension of the output image
or a single value which is handled as 0xBBGGRR.

* **Parameters:**
  * **image** – a numpy array of Y, X, Bands.
  * **context** – the style context.  context.image is the source image
  * **values** – an array of values, each of which is either an array of the
    same number of bands as the source image or a single value of the form
    0xBBGGRR assuming uint8 data.
  * **negative** – None to use [0, 0, 0, 255], or an RGBA uint8 value for
    pixels not in the value list.
  * **positive** – None to use [255, 255, 255, 0], or an RGBA uint8 value for
    pixels in the value list.
* **Returns:**
  an RGBA numpy image which is exactly black or transparent white.

### large_image.tilesource.stylefuncs.medianFilter(image: ndarray, context: SimpleNamespace | None = None, kernel: int = 5, weight: float = 1.0) → ndarray

This is a style utility function that applies a median rank filter to the
image to sharpen it.

* **Parameters:**
  * **image** – a numpy array of Y, X, Bands.
  * **context** – the style context.  context.image is the source image
  * **kernel** – the filter kernel size.
  * **weight** – the weight of the difference between the image and the
    filtered image that is used to add into the image.  0 is no effect/
* **Returns:**
  an numpy image which is the filtered version of the source.

## large_image.tilesource.tiledict module

### *class* large_image.tilesource.tiledict.LazyTileDict(tileInfo: dict[str, Any], \*args, \*\*kwargs)

Bases: `dict`

Tiles returned from the tile iterator and dictionaries of information with
actual image data in the ‘tile’ key and the format in the ‘format’ key.
Since some applications need information about the tile but don’t need the
image data, these two values are lazily computed.  The LazyTileDict can be
treated like a regular dictionary, except that when either of those two
keys are first accessed, they will cause the image to be loaded and
possibly converted to a PIL image and cropped.

Unless setFormat is called on the tile, tile images may always be returned
as PIL images.

Create a LazyTileDict dictionary where there is enough information to
load the tile image.  ang and kwargs are as for the dict() class.

* **Parameters:**
  **tileInfo** – a dictionary of x, y, level, format, encoding, crop,
  and source, used for fetching the tile image.

#### release() → None

If the tile has been loaded, unload it.  It can be loaded again.  This
is useful if you want to keep tiles available in memory but not their
actual tile data.

#### setFormat(format: tuple[str, ...], resample: bool = False, imageKwargs: dict[str, Any] | None = None) → None

Set a more restrictive output format for a tile, possibly also resizing
it via resampling.  If this is not called, the tile may either be
returned as one of the specified formats or as a PIL image.

* **Parameters:**
  * **format** – a tuple or list of allowed formats.  Formats are members
    of TILE_FORMAT_\*.  This will avoid converting images if they are
    in the desired output encoding (regardless of subparameters).
  * **resample** – if not False or None, allow resampling.  Once turned
    on, this cannot be turned off on the tile.
  * **imageKwargs** – additional parameters that should be passed to
    \_encodeImage.

## large_image.tilesource.tileiterator module

### *class* large_image.tilesource.tileiterator.TileIterator(source: [tilesource.TileSource](#large_image.tilesource.TileSource), format: str | tuple[str] = ('numpy',), resample: bool | None = True, \*\*kwargs)

Bases: `object`

A tile iterator on a TileSource.  Details about the iterator can be read
via the info attribute on the iterator.

## large_image.tilesource.utilities module

### *class* large_image.tilesource.utilities.ImageBytes(source: bytes, mimetype: str | None = None)

Bases: `bytes`

Wrapper class to make repr of image bytes better in ipython.

Display the number of bytes and, if known, the mimetype.

#### *property* mimetype *: str | None*

### *class* large_image.tilesource.utilities.JSONDict(\*args, \*\*kwargs)

Bases: `dict`

Wrapper class to improve Jupyter repr of JSON-able dicts.

### large_image.tilesource.utilities.addPILFormatsToOutputOptions() → None

Check PIL for available formats that be saved and add them to the lists of
of available formats.

### large_image.tilesource.utilities.dictToEtree(d: dict[str, Any], root: Element | None = None) → Element

Convert a dictionary in the style produced by etreeToDict back to an etree.
Make an xml string via xml.etree.ElementTree.tostring(dictToEtree(
dictionary), encoding=’utf8’, method=’xml’).  Note that this function and
etreeToDict are not perfect conversions; numerical values are quoted in
xml.  Plain key-value pairs are ambiguous whether they should be attributes
or text values.  Text fields are collected together.

* **Parameters:**
  **d** – a dictionary.
* **Prarm root:**
  the root node to attach this dictionary to.
* **Returns:**
  an etree.

### large_image.tilesource.utilities.etreeToDict(t: Element) → dict[str, Any]

Convert an xml etree to a nested dictionary without schema names in the
keys.  If you have an xml string, this can be converted to a dictionary via
xml.etree.etreeToDict(ElementTree.fromstring(xml_string)).

* **Parameters:**
  **t** – an etree.
* **Returns:**
  a python dictionary with the results.

### large_image.tilesource.utilities.fullAlphaValue(arr: ndarray | type[Any] | dtype[Any] | \_HasDType[dtype[Any]] | \_HasNumPyDType[dtype[Any]] | tuple[Any, Any] | list[Any] | \_DTypeDict | str) → int

Given a numpy array, return the value that should be used for a fully
opaque alpha channel.  For uint variants, this is the max value.

* **Parameters:**
  **arr** – a numpy array.
* **Returns:**
  the value for the alpha channel.

### large_image.tilesource.utilities.getAvailableNamedPalettes(includeColors: bool = True, reduced: bool = False) → list[str]

Get a list of all named palettes that can be used with getPaletteColors.

* **Parameters:**
  * **includeColors** – if True, include named colors.  If False, only
    include actual palettes.
  * **reduced** – if True, exclude reversed palettes and palettes with
    fewer colors where a palette with the same basic name exists with more
    colors.
* **Returns:**
  a list of names.

### large_image.tilesource.utilities.getPaletteColors(value: str | list[str | float | tuple[float, ...]]) → ndarray

Given a list or a name, return a list of colors in the form of a numpy
array of RGBA.  If a list, each entry is a color name resolvable by either
PIL.ImageColor.getcolor, by matplotlib.colors, or a 3 or 4 element list or
tuple of RGB(A) values on a scale of 0-1.  If this is NOT a list, then, if
it can be parsed as a color, it is treated as [‘#000’, <value>].  If that
cannot be parsed, then it is assumed to be a named palette in palettable
(such as viridis.Viridis_12) or a named palette in matplotlib (including
plugins).

* **Parameters:**
  **value** – Either a list, a single color name, or a palette name.  See
  above.
* **Returns:**
  a numpy array of RGBA value on the scale of [0-255].

### large_image.tilesource.utilities.getTileFramesQuadInfo(metadata: dict[str, Any], options: dict[str, Any] | None = None) → dict[str, Any]

Compute what tile_frames need to be requested for a particular condition.

Options is a dictionary of:
: * **format:**
    The compression and format for the texture.  Defaults to
    {‘encoding’: ‘JPEG’, ‘jpegQuality’: 85, ‘jpegSubsampling’: 1}.
  * **query:**
    Additional query options to add to the tile source, such as
    style.
  * **frameBase:**
    (default 0) Starting frame number used.  c/z/xy/z to step
    through that index length (0 to 1 less than the value), which is
    probably only useful for cache reporting or scheduling.
  * **frameStride:**
    (default 1) Only use every `frameStride` frame of the
    image.  c/z/xy/z to use that axis length.
  * **frameGroup:**
    (default 1) If above 1 and multiple textures are used, each
    texture will have an even multiple of the group size number of
    frames.  This helps control where texture loading transitions
    occur.  c/z/xy/z to use that axis length.
  * **frameGroupFactor:**
    (default 4) If `frameGroup` would reduce the size
    of the tile images beyond this factor, don’t use it.
  * **frameGroupStride:**
    (default 1) If `frameGroup` is above 1 and multiple
    textures are used, then the frames are reordered based on this
    stride value.  “auto” to use frameGroup / frameStride if that
    value is an integer.
  * **maxTextureSize:**
    Limit the maximum texture size to a square of this
    size.
  * **maxTextures:**
    (default 1) If more than one, allow multiple textures to
    increase the size of the individual frames.  The number of textures
    will be capped by `maxTotalTexturePixels` as well as this number.
  * **maxTotalTexturePixels:**
    (default 1073741824) Limit the maximum texture
    size and maximum number of textures so that the combined set does
    not exceed this number of pixels.
  * **alignment:**
    (default 16) Individual frames are buffered to an alignment
    of this maxy pixels.  If JPEG compression is used, this should
    be 8 for monochrome images or jpegs without subsampling, or 16 for
    jpegs with moderate subsampling to avoid compression artifacts from
    leaking between frames.
  * **maxFrameSize:**
    If set, limit the maximum width and height of an
    individual frame to this value.

* **Parameters:**
  * **metadata** – the tile source metadata.  Needs to contain sizeX, sizeY,
    tileWidth, tileHeight, and a list of frames.
  * **options** – dictionary of options, as described above.
* **Returns:**
  a dictionary of values to use for making calls to tile_frames.

### large_image.tilesource.utilities.histogramThreshold(histogram: dict[str, Any], threshold: float, fromMax: bool = False) → float

Given a histogram and a threshold on a scale of [0, 1], return the bin
edge that excludes no more than the specified threshold amount of values.
For instance, a threshold of 0.02 would exclude at most 2% of the values.

* **Parameters:**
  * **histogram** – a histogram record for a specific channel.
  * **threshold** – a value from 0 to 1.
  * **fromMax** – if False, return values excluding the low end of the
    histogram; if True, return values from excluding the high end of the
    histogram.
* **Returns:**
  the value the excludes no more than the threshold from the
  specified end.

### large_image.tilesource.utilities.isValidPalette(value: str | list[str | float | tuple[float, ...]]) → bool

Check if a value can be used as a palette.

* **Parameters:**
  **value** – Either a list, a single color name, or a palette name.  See
  getPaletteColors.
* **Returns:**
  a boolean; true if the value can be used as a palette.

### large_image.tilesource.utilities.nearPowerOfTwo(val1: float, val2: float, tolerance: float = 0.02) → bool

Check if two values are different by nearly a power of two.

* **Parameters:**
  * **val1** – the first value to check.
  * **val2** – the second value to check.
  * **tolerance** – the maximum difference in the log2 ratio’s mantissa.
* **Returns:**
  True if the values are nearly a power of two different from each
  other; false otherwise.

## Module contents

### *class* large_image.tilesource.FileTileSource(path: str | Path | dict[Any, Any], \*args, \*\*kwargs)

Bases: [`TileSource`](#large_image.tilesource.base.TileSource)

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### *classmethod* addKnownMimetypes() → None

Based on already listed extensions and a set of common extension-
mimetype list, add mimetypes if they do not already exist.

#### *classmethod* canRead(path: str | Path | dict[Any, Any], \*args, \*\*kwargs) → bool

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it
  cannot.

#### *static* getLRUHash(\*args, \*\*kwargs) → str

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getState() → str

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

### *exception* large_image.tilesource.TileGeneralError

Bases: `Exception`

### large_image.tilesource.TileGeneralException

alias of [`TileGeneralError`](large_image.md#large_image.exceptions.TileGeneralError)

### *class* large_image.tilesource.TileSource(encoding: str | None = None, jpegQuality: int = 95, jpegSubsampling: int = 0, tiffCompression: str = 'raw', edge: bool | str = False, style: str | dict[str, int] | None = None, noCache: bool | None = None, \*args, \*\*kwargs)

Bases: [`IPyLeafletMixin`](#large_image.tilesource.jupyter.IPyLeafletMixin)

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

#### axesToFrame(\*\*kwargs: int) → int

Given values on some or all of the axes, return the corresponding frame
number.  Any unspecified axis is 0.  If one of the specified axes is
‘frame’, this is just returned and the other values are ignored.

* **Parameters:**
  **kwargs** – axes with position values.
* **Returns:**
  a frame number.

#### *property* bandCount *: int | None*

#### *classmethod* canRead(\*args, \*\*kwargs) → bool

Check if we can read the input.  This takes the same parameters as
\_\_init_\_.

* **Returns:**
  True if this class can read the input.  False if it cannot.

#### *property* channelNames *: list[str] | None*

If known, return a list of channel names.

* **Returns:**
  either None or a list of channel names as strings.

#### convertRegionScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, cropToImage: bool = True) → dict[str, Any]

Convert a region from one scale to another.

* **Parameters:**
  * **sourceRegion** – 

    a dictionary of optional values which specify the
    part of an image to process.
    * **left:**
      the left edge (inclusive) of the region to process.
    * **top:**
      the top edge (inclusive) of the region to process.
    * **right:**
      the right edge (exclusive) of the region to process.
    * **bottom:**
      the bottom edge (exclusive) of the region to process.
    * **width:**
      the width of the region to process.
    * **height:**
      the height of the region to process.
    * **units:**
      either ‘base_pixels’ (default), ‘pixels’, ‘mm’, or
      ‘fraction’.  base_pixels are in maximum resolution pixels.
      pixels is in the specified magnification pixels.  mm is in the
      specified magnification scale.  fraction is a scale of 0 to 1.
      pixels and mm are only available if the magnification and mm
      per pixel are defined for the image.
  * **sourceScale** – 

    a dictionary of optional values which specify the
    scale of the source region.  Required if the sourceRegion is
    in “mag_pixels” units.
    * **magnification:**
      the magnification ratio.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
  * **targetScale** – 

    a dictionary of optional values which specify the
    scale of the target region.  Required in targetUnits is in
    “mag_pixels” units.
    * **magnification:**
      the magnification ratio.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
  * **targetUnits** – if not None, convert the region to these units.
    Otherwise, the units are will either be the sourceRegion units if
    those are not “mag_pixels” or base_pixels.  If “mag_pixels”, the
    targetScale must be specified.
  * **cropToImage** – if True, don’t return region coordinates outside of
    the image.

#### *property* dtype *: dtype*

#### eagerIterator(\*\*kwargs) → [EagerIterator](#large_image.tilesource.eageriterator.EagerIterator)

Create an eager iterator for batched tile or region reads.

The eager iterator is intended for AI and machine-learning workflows that need
prefetched numpy or torch batches from a Large Image tile source. It supports tile
mode and explicit region mode, optional masking, scaling, padding, transforms,
and dynamic transform-scale callbacks.

* **Parameters:**
  **kwargs** – EagerIterator options such as output_mode, tile_overlap, mask,
  region, scale, tile_size, region_size, source_scale, dtype, chunk_mult,
  edge, pad_mode, pad_fill_mode, nchw, batch, prefetch, workers, tiles,
  regions, transform, randomize_chunks, seed, area_threshold, threshold_mask,
  transform_save_mode, and transform_scale.
* **Returns:**
  An EagerIterator. Each iteration returns a dictionary with ‘tile’ as a
  SharedArray plus tile metadata including format, gx, gy, level_x, level_y,
  tile_position, width, height, level, magnification, mm_x, mm_y, gwidth, and
  gheight.

#### extensions *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### frameToAxes(frame: int) → dict[str, int]

Given a frame number, return a dictionary of axes values.  If unknown,
this is just ‘frame’: frame.

* **Parameters:**
  **frame** – a frame number.
* **Returns:**
  a dictionary of axes that specify the frame.

#### *property* frames *: int*

A property with the number of frames.

#### *property* geospatial *: bool*

#### getAssociatedImage(imageKey: str, \*args, \*\*kwargs) → tuple[[ImageBytes](#large_image.tilesource.utilities.ImageBytes), str] | None

Return an associated image.

* **Parameters:**
  * **imageKey** – the key of the associated image to retrieve.
  * **kwargs** – optional arguments.  Some options are width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  imageData, imageMime: the image data and the mime type, or
  None if the associated image doesn’t exist.

#### getAssociatedImagesList() → list[str]

Return a list of associated images.

* **Returns:**
  the list of image keys.

#### getBandInformation(statistics: bool = False, \*\*kwargs) → dict[int, Any]

Get information about each band in the image.

* **Parameters:**
  **statistics** – if True, compute statistics if they don’t already
  exist.
* **Returns:**
  a dictionary of one dictionary per band.  Each dictionary
  contains known values such as interpretation, min, max, mean,
  stdev.

#### getBounds(\*args, \*\*kwargs) → dict[str, Any]

#### getCenter(\*args, \*\*kwargs) → tuple[float, float]

Returns (Y, X) center location.

#### getGeospatialRegion(src_projection: str, src_gcps: list[tuple[float] | list[float]], dest_projection: str, dest_region: dict[str, float], \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

This function requires pyproj and either rasterio or gdal; it allows
specifying georeferencing (even for non-geospatial images) and
retrieving a region from geospatial coordinates.  In addition to the
required georeferencing parameters described below, this takes the same
parameters as getRegion.

* **Parameters:**
  * **src_projection** – A string describing the coordinate reference
    system used for src_gcps. This string can be an EPSG code or other
    format accepted by pyproj.CRS.from_string.
  * **src_gcps** – A list of ground control points describing projected
    coordinates for certain pixel coordinates in the image. Each GCP
    can be a list or tuple with the following format: (cx, cy, px, py)
    where (cx, cy) is a projected coordinate in the coordinate
    reference system described by src_projection and (px, py) is a
    pixel coordinate within the extents of the image.
  * **dest_projection** – A string describing the coordinate reference
    system used for dest_region. This string can be an EPSG code or
    other format accepted by pyproj.CRS.from_string.
  * **dest_region** – A dictionary describing the desired region to
    retrieve from the image.  Must specify values for “top”, “bottom”,
    “left”, and “right” in the projected coordinate system specified by
    dest_projection.
  * **kwargs** – Optional arguments passed to getRegion.
* **Returns:**
  regionData, formatOrRegionMime: the image data and either the
  mime type, if the format is TILE_FORMAT_IMAGE, or the format.

#### getICCProfiles(idx: int | None = None, onlyInfo: bool = False) → None | ImageCmsProfile | list[ImageCmsProfile | None]

Get a list of all ICC profiles that are available for the source, or
get a specific profile.

* **Parameters:**
  * **idx** – a 0-based index into the profiles to get one profile, or
    None to get a list of all profiles.
  * **onlyInfo** – if idx is None and this is true, just return the
    profile information.
* **Returns:**
  either one or a list of PIL.ImageCms.CmsProfile objects, or
  None if no profiles are available.  If a list, entries in the list
  may be None.

#### getInternalMetadata(\*\*kwargs) → dict[Any, Any] | None

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### *static* getLRUHash(\*args, \*\*kwargs) → str

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getLevelForMagnification(magnification: float | None = None, exact: bool = False, mm_x: float | None = None, mm_y: float | None = None, rounding: str | bool | None = 'round', \*\*kwargs) → int | float | None

Get the level for a specific magnification or pixel size.  If the
magnification is unknown or no level is sufficient resolution, and an
exact match is not requested, the highest level will be returned.

If none of magnification, mm_x, and mm_y are specified, the maximum
level is returned.  If more than one of these values is given, an
average of those given will be used (exact will require all of them to
match).

* **Parameters:**
  * **magnification** – the magnification ratio.
  * **exact** – if True, only a level that matches exactly will be
    returned.
  * **mm_x** – the horizontal size of a pixel in millimeters.
  * **mm_y** – the vertical size of a pixel in millimeters.
  * **rounding** – if False, a fractional level may be returned.  If
    ‘ceil’ or ‘round’, that function is used to convert the level to an
    integer (the exact flag still applies).  If None, the level is not
    cropped to the actual image’s level range.
* **Returns:**
  the selected level or None for no match.

#### getMagnificationForLevel(level: float | None = None) → dict[str, float | None]

Get the magnification at a particular level.

* **Parameters:**
  **level** – None to use the maximum level, otherwise the level to get
  the magnification factor of.
* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getMetadata() → [JSONDict](#large_image.tilesource.utilities.JSONDict)

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

#### getNativeMagnification() → dict[str, float | None]

Get the magnification for the highest-resolution level.

* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getOneBandInformation(band: int) → dict[str, Any]

Get band information for a single band.

* **Parameters:**
  **band** – a 1-based band.
* **Returns:**
  a dictionary of band information.  See getBandInformation.

#### getPixel(includeTileRecord: bool = False, \*\*kwargs) → [JSONDict](#large_image.tilesource.utilities.JSONDict)

Get a single pixel from the current tile source.

* **Parameters:**
  * **includeTileRecord** – if True, include the tile used for computing
    the pixel in the response.
  * **kwargs** – optional arguments.  Some options are region, output,
    encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
    tileIterator.
* **Returns:**
  a dictionary with the value of the pixel for each channel on
  a scale of [0-255], including alpha, if available.  This may
  contain additional information.

#### getPointAtAnotherScale(point: tuple[float, float], sourceScale: dict[str, float] | None = None, sourceUnits: str | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → tuple[float, float]

Given a point as a (x, y) tuple, convert it from one scale to another.
The sourceScale, sourceUnits, targetScale, and targetUnits parameters
are the same as convertRegionScale, where sourceUnits are the units
used with sourceScale.

#### getPreferredLevel(level: int) → int

Given a desired level (0 is minimum resolution, self.levels - 1 is max
resolution), return the level that contains actual data that is no
lower resolution.

* **Parameters:**
  **level** – desired level
* **Returns level:**
  a level with actual data that is no lower resolution.

#### getRegion(format: str | tuple[str] = ('image',), \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

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

#### getRegionAtAnotherScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

This takes the same parameters and returns the same results as
getRegion, except instead of region and scale, it takes sourceRegion,
sourceScale, targetScale, and targetUnits.  These parameters are the
same as convertRegionScale.  See those two functions for parameter
definitions.

#### getSingleTile(\*args, \*\*kwargs) → [LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict) | None

Return any single tile from an iterator.  This takes exactly the same
parameters as tileIterator.  Use tile_position to get a specific tile,
otherwise the first tile is returned.

* **Returns:**
  a tile dictionary or None.

#### getSingleTileAtAnotherScale(\*args, \*\*kwargs) → [LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict) | None

Return any single tile from a rescaled iterator.  This takes exactly
the same parameters as tileIteratorAtAnotherScale.  Use tile_position
to get a specific tile, otherwise the first tile is returned.

* **Returns:**
  a tile dictionary or None.

#### getState() → str

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

#### getThumbnail(width: str | int | None = None, height: str | int | None = None, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

Get a basic thumbnail from the current tile source.  Aspect ratio is
preserved.  If neither width nor height is given, a default value is
used.  If both are given, the thumbnail will be no larger than either
size.  A thumbnail has the same options as a region except that it
always includes the entire image and has a default size of 256 x 256.

* **Parameters:**
  * **width** – maximum width in pixels.
  * **height** – maximum height in pixels.
  * **kwargs** – optional arguments.  Some options are encoding,
    jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  thumbData, thumbMime: the image data and the mime type.

#### getTile(x: int, y: int, z: int, pilImageAllowed: bool = False, numpyAllowed: bool | str = False, sparseFallback: bool = False, frame: int | None = None) → [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | Image | bytes | ndarray

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

#### getTileCount(\*args, \*\*kwargs) → int

Return the number of tiles that the tileIterator will return.  See
tileIterator for parameters.

* **Returns:**
  the number of tiles that the tileIterator will yield.

#### getTileMimeType() → str

Return the default mimetype for image tiles.

* **Returns:**
  the mime type of the tile.

#### histogram(dtype: type[Any] | dtype[Any] | \_HasDType[dtype[Any]] | \_HasNumPyDType[dtype[Any]] | tuple[Any, Any] | list[Any] | \_DTypeDict | str | None = None, onlyMinMax: bool = False, bins: int = 256, density: bool = False, format: Any = None, \*args, \*\*kwargs) → dict[str, ndarray | list[dict[str, Any]]]

Get a histogram for a region.

* **Parameters:**
  * **dtype** – if specified, the tiles must be this numpy.dtype.
  * **onlyMinMax** – if True, only return the minimum and maximum value
    of the region.
  * **bins** – the number of bins in the histogram.  This is passed to
    numpy.histogram, but needs to produce the same set of edges for
    each tile.
  * **density** – if True, scale the results based on the number of
    samples.
  * **format** – ignored.  Used to override the format for the
    tileIterator.
  * **range** – if None, use the computed min and (max + 1).  Otherwise,
    this is the range passed to numpy.histogram.  Note this is only
    accessible via kwargs as it otherwise overloads the range function.
    If ‘round’, use the computed values, but the number of bins may be
    reduced or the bin_edges rounded to integer values for
    integer-based source data.
  * **args** – parameters to pass to the tileIterator.
  * **kwargs** – parameters to pass to the tileIterator.
* **Returns:**
  if onlyMinMax is true, this is a dictionary with keys min and
  max, each of which is a numpy array with the minimum and maximum of
  all of the bands.  If onlyMinMax is False, this is a dictionary
  with a single key ‘histogram’ that contains a list of histograms
  per band.  Each entry is a dictionary with min, max, range, hist,
  bins, and bin_edges.  range is [min, (max + 1)].  hist is the
  counts (normalized if density is True) for each bin.  bins is the
  number of bins used.  bin_edges is an array one longer than the
  hist array that contains the boundaries between bins.

#### levels *: int*

#### *property* metadata *: [JSONDict](#large_image.tilesource.utilities.JSONDict)*

#### mimeTypes *: dict[str | None, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {None: SourcePriority.FALLBACK}*

#### name *= None*

#### nameMatches *: dict[str, [SourcePriority](large_image.md#large_image.constants.SourcePriority)]* *= {}*

#### newPriority *: [SourcePriority](large_image.md#large_image.constants.SourcePriority) | None* *= None*

#### sizeX *: int*

#### sizeY *: int*

#### *property* style *: [JSONDict](#large_image.tilesource.utilities.JSONDict) | None*

#### tileFrames(format: str | tuple[str] = ('image',), frameList: list[int] | None = None, framesAcross: int | None = None, max_workers: int | None = -4, \*\*kwargs) → tuple[ndarray | Image | [ImageBytes](#large_image.tilesource.utilities.ImageBytes) | bytes | Path, str]

Given the parameters for getRegion, plus a list of frames and the
number of frames across, make a larger image composed of a region from
each listed frame composited together.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats.
    Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
    TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding may be
    specified.
  * **frameList** – None for all frames, or a list of 0-based integers.
  * **framesAcross** – the number of frames across the final image.  If
    unspecified, this is the ceiling of sqrt(number of frames in frame
    list).
  * **kwargs** – optional arguments.  Some options are region, output,
    encoding, jpegQuality, jpegSubsampling, tiffCompression, fill.  See
    tileIterator.
  * **max_workers** – maximum workers for parallelism.  If negative, use
    the minimum of the absolute value of this number or
    multiprocessing.cpu_count().
* **Returns:**
  regionData, formatOrRegionMime: the image data and either the
  mime type, if the format is TILE_FORMAT_IMAGE, or the format.

#### tileHeight *: int*

#### tileIterator(format: str | tuple[str] = ('numpy',), resample: bool = True, \*\*kwargs) → Iterator[[LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict)]

Iterate on all tiles in the specified region at the specified scale.
Each tile is returned as part of a dictionary that includes

> * **x, y:**
>   (left, top) coordinates in current magnification pixels
> * **width, height:**
>   size of current tile in current magnification pixels
> * **tile:**
>   cropped tile image
> * **format:**
>   format of the tile
> * **level:**
>   level of the current tile
> * **level_x, level_y:**
>   the tile reference number within the level.
>   Tiles are numbered (0, 0), (1, 0), (2, 0), etc.  The 0th tile
>   yielded may not be (0, 0) if a region is specified.
> * **tile_position:**
>   a dictionary of the tile position within the
>   iterator, containing:
>   * **level_x, level_y:**
>     the tile reference number within the level.
>   * **region_x, region_y:**
>     0, 0 is the first tile in the full
>     iteration (when not restricting the iteration to a single
>     tile).
>   * **position:**
>     a 0-based value for the tile within the full
>     iteration.
> * **iterator_range:**
>   a dictionary of the output range of the iterator:
>   * **level_x_min, level_x_max:**
>     the tiles that are be included
>     during the full iteration: [layer_x_min, layer_x_max).
>   * **level_y_min, level_y_max:**
>     the tiles that are be included
>     during the full iteration: [layer_y_min, layer_y_max).
>   * **region_x_max, region_y_max:**
>     the number of tiles included during
>     the full iteration.   This is layer_x_max - layer_x_min,
>     layer_y_max - layer_y_min.
>   * **position:**
>     the total number of tiles included in the full
>     iteration.  This is region_x_max \* region_y_max.
> * **magnification:**
>   magnification of the current tile
> * **mm_x, mm_y:**
>   size of the current tile pixel in millimeters.
> * **gx, gy:**
>   (left, top) coordinates in maximum-resolution pixels
> * **gwidth, gheight:**
>   size of of the current tile in maximum-resolution
>   pixels.
> * **tile_overlap:**
>   the amount of overlap with neighboring tiles (left,
>   top, right, and bottom).  Overlap never extends outside of the
>   requested region.

If a region that includes partial tiles is requested, those tiles are
cropped appropriately.  Most images will have tiles that get cropped
along the right and bottom edges in any case.  If an exact
magnification or scale is requested, no tiles will be returned.

* **Parameters:**
  * **format** – the desired format or a tuple of allowed formats.
    Formats are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY,
    TILE_FORMAT_IMAGE).  If TILE_FORMAT_IMAGE, encoding must be
    specified.
  * **resample** – 

    If True or one of PIL.Image.Resampling.NEAREST,
    LANCZOS, BILINEAR, or BICUBIC to resample tiles that are not the
    target output size.  Tiles that are resampled will have additional
    dictionary entries of:
    * **scaled:**
      the scaling factor that was applied (less than 1 is
      downsampled).
    * **tile_x, tile_y:**
      (left, top) coordinates before scaling
    * **tile_width, tile_height:**
      size of the current tile before
      scaling.
    * **tile_magnification:**
      magnification of the current tile before
      scaling.
    * **tile_mm_x, tile_mm_y:**
      size of a pixel in a tile in millimeters
      before scaling.

    Note that scipy.misc.imresize uses PIL internally.
  * **region** – 

    a dictionary of optional values which specify the part
    of the image to process:
    * **left:**
      the left edge (inclusive) of the region to process.
    * **top:**
      the top edge (inclusive) of the region to process.
    * **right:**
      the right edge (exclusive) of the region to process.
    * **bottom:**
      the bottom edge (exclusive) of the region to process.
    * **width:**
      the width of the region to process.
    * **height:**
      the height of the region to process.
    * **units:**
      either ‘base_pixels’ (default), ‘pixels’, ‘mm’, or
      ‘fraction’.  base_pixels are in maximum resolution pixels.
      pixels is in the specified magnification pixels.  mm is in the
      specified magnification scale.  fraction is a scale of 0 to 1.
      pixels and mm are only available if the magnification and mm
      per pixel are defined for the image.  For geospatial sources,
      this can also be ‘projection’, or a case-insensitive string
      starting with ‘proj4:’, ‘epsg:’ or a enumerated value like
      ‘wgs84’.
    * **unitsWH:**
      if not specified, this is the same as units.
      Otherwise, these units will be used for the width and height if
      specified.  If can take the same values as units.
  * **output** – 

    a dictionary of optional values which specify the size
    of the output.
    * **maxWidth:**
      maximum width in pixels.  If either maxWidth or maxHeight
      is specified, magnification, mm_x, and mm_y are ignored.
    * **maxHeight:**
      maximum height in pixels.
  * **scale** – 

    a dictionary of optional values which specify the scale
    of the region and / or output.  This applies to region if
    pixels or mm are used for inits.  It applies to output if
    neither output maxWidth nor maxHeight is specified.
    * **magnification:**
      the magnification ratio.  Only used if maxWidth and
      maxHeight are not specified or None.
    * **mm_x:**
      the horizontal size of a pixel in millimeters.
    * **mm_y:**
      the vertical size of a pixel in millimeters.
    * **exact:**
      if True, only a level that matches exactly will be returned.
      This is only applied if magnification, mm_x, or mm_y is used.
  * **tile_position** – if present, either a number to only yield the
    (tile_position)th tile [0 to (xmax - min) \* (ymax - ymin)) that the
    iterator would yield, or a dictionary of {region_x, region_y} to
    yield that tile, where 0, 0 is the first tile yielded, and
    xmax - xmin - 1, ymax - ymin - 1 is the last tile yielded, or a
    dictionary of {level_x, level_y} to yield that specific tile if it
    is in the region.
  * **tile_size** – 

    if present, retile the output to the specified tile
    size.  If only width or only height is specified, the resultant
    tiles will be square.  This is a dictionary containing at least
    one of:
    * **width:**
      the desired tile width.
    * **height:**
      the desired tile height.
  * **tile_overlap** – 

    if present, retile the output adding a symmetric
    overlap to the tiles.  If either x or y is not specified, it
    defaults to zero.  The overlap does not change the tile size,
    only the stride of the tiles.  This is a dictionary containing:
    * **x:**
      the horizontal overlap in pixels.
    * **y:**
      the vertical overlap in pixels.
    * **edges:**
      if True, then the edge tiles will exclude the overlap
      distance.  If unset or False, the edge tiles are full size.

      The overlap is conceptually split between the two sides of
      the tile.  This is only relevant to where overlap is reported
      or if edges is True

      As an example, suppose an image that is 8 pixels across
      (01234567) and a tile size of 5 is requested with an overlap of
      4.  If the edges option is False (the default), the following
      tiles are returned: 01234, 12345, 23456, 34567.  Each tile
      reports its overlap, and the non-overlapped area of each tile
      is 012, 3, 4, 567.  If the edges option is True, the tiles
      returned are: 012, 0123, 01234, 12345, 23456, 34567, 4567, 567,
      with the non-overlapped area of each as 0, 1, 2, 3, 4, 5, 6, 7.
  * **tile_offset** – 

    if present, adjust tile positions so that the
    corner of one tile is at the specified location.
    * **left:**
      the left offset in pixels.
    * **top:**
      the top offset in pixels.
    * **auto:**
      a boolean, if True, automatically set the offset to align
      with the region’s left and top.
  * **encoding** – if format includes TILE_FORMAT_IMAGE, a valid PIL
    encoding (typically ‘PNG’, ‘JPEG’, or ‘TIFF’) or ‘TILED’ (identical
    to TIFF).  Must also be in the TileOutputMimeTypes map.
  * **jpegQuality** – the quality to use when encoding a JPEG.
  * **jpegSubsampling** – the subsampling level to use when encoding a
    JPEG.
  * **tiffCompression** – the compression format when encoding a TIFF.
    This is usually ‘raw’, ‘tiff_lzw’, ‘jpeg’, or ‘tiff_adobe_deflate’.
    Some of these are aliased: ‘none’, ‘lzw’, ‘deflate’.
  * **frame** – the frame number within the tile source.  None is the
    same as 0 for multi-frame sources.
  * **kwargs** – optional arguments.
* **Yields:**
  an iterator that returns a dictionary as listed above.

#### tileIteratorAtAnotherScale(sourceRegion: dict[str, Any], sourceScale: dict[str, float] | None = None, targetScale: dict[str, float] | None = None, targetUnits: str | None = None, \*\*kwargs) → Iterator[[LazyTileDict](#large_image.tilesource.tiledict.LazyTileDict)]

This takes the same parameters and returns the same results as
tileIterator, except instead of region and scale, it takes
sourceRegion, sourceScale, targetScale, and targetUnits.  These
parameters are the same as convertRegionScale.  See those two functions
for parameter definitions.

#### tileWidth *: int*

#### wrapKey(\*args, \*\*kwargs) → str

Return a key for a tile source and function parameters that can be used
as a unique cache key.

* **Parameters:**
  * **args** – arguments to add to the hash.
  * **kwaths** – arguments to add to the hash.
* **Returns:**
  a cache key.

### *exception* large_image.tilesource.TileSourceAssetstoreError

Bases: [`TileSourceError`](large_image.md#large_image.exceptions.TileSourceError)

### large_image.tilesource.TileSourceAssetstoreException

alias of [`TileSourceAssetstoreError`](large_image.md#large_image.exceptions.TileSourceAssetstoreError)

### *exception* large_image.tilesource.TileSourceError

Bases: [`TileGeneralError`](large_image.md#large_image.exceptions.TileGeneralError)

### large_image.tilesource.TileSourceException

alias of [`TileSourceError`](large_image.md#large_image.exceptions.TileSourceError)

### *exception* large_image.tilesource.TileSourceFileNotFoundError(\*args)

Bases: [`TileSourceError`](large_image.md#large_image.exceptions.TileSourceError), `FileNotFoundError`

### large_image.tilesource.canRead(\*args, \*\*kwargs) → bool

Check if large_image can read a path or uri.

If there is no intention to open the image immediately, conisder adding
noCache=True to the kwargs to avoid cycling the cache unnecessarily.

* **Returns:**
  True if any appropriate source reports it can read the path or
  uri.

### large_image.tilesource.dictToEtree(d: dict[str, Any], root: Element | None = None) → Element

Convert a dictionary in the style produced by etreeToDict back to an etree.
Make an xml string via xml.etree.ElementTree.tostring(dictToEtree(
dictionary), encoding=’utf8’, method=’xml’).  Note that this function and
etreeToDict are not perfect conversions; numerical values are quoted in
xml.  Plain key-value pairs are ambiguous whether they should be attributes
or text values.  Text fields are collected together.

* **Parameters:**
  **d** – a dictionary.
* **Prarm root:**
  the root node to attach this dictionary to.
* **Returns:**
  an etree.

### large_image.tilesource.etreeToDict(t: Element) → dict[str, Any]

Convert an xml etree to a nested dictionary without schema names in the
keys.  If you have an xml string, this can be converted to a dictionary via
xml.etree.etreeToDict(ElementTree.fromstring(xml_string)).

* **Parameters:**
  **t** – an etree.
* **Returns:**
  a python dictionary with the results.

### large_image.tilesource.getSourceNameFromDict(availableSources: dict[str, type[[FileTileSource](#large_image.tilesource.base.FileTileSource)]], pathOrUri: str | PosixPath, mimeType: str | None = None, \*args, \*\*kwargs) → str | None

Get a tile source based on a ordered dictionary of known sources and a path
name or URI.  Additional parameters are passed to the tile source and can
be used for properties such as encoding.

* **Parameters:**
  * **availableSources** – an ordered dictionary of sources to try.
  * **pathOrUri** – either a file path or a fixed source via
    large_image://<source>.
  * **mimeType** – the mimetype of the file, if known.
* **Returns:**
  the name of a tile source that can read the input, or None if
  there is no such source.

### large_image.tilesource.getTileSource(\*args, \*\*kwargs) → [FileTileSource](#large_image.tilesource.base.FileTileSource)

Get a tilesource using the known sources.  If tile sources have not yet
been loaded, load them.

* **Returns:**
  A tilesource for the passed arguments.

### large_image.tilesource.listExtensions(availableSources: dict[str, type[[FileTileSource](#large_image.tilesource.base.FileTileSource)]] | None = None) → list[str]

Get a list of all known extensions.

* **Parameters:**
  **availableSources** – an ordered dictionary of sources to try.
* **Returns:**
  a list of extensions (without leading dots).

### large_image.tilesource.listMimeTypes(availableSources: dict[str, type[[FileTileSource](#large_image.tilesource.base.FileTileSource)]] | None = None) → list[str]

Get a list of all known mime types.

* **Parameters:**
  **availableSources** – an ordered dictionary of sources to try.
* **Returns:**
  a list of mime types.

### large_image.tilesource.listSources(availableSources: dict[str, type[[FileTileSource](#large_image.tilesource.base.FileTileSource)]] | None = None) → dict[str, dict[str, Any]]

Get a dictionary with all sources, all known extensions, and all known
mimetypes.

* **Parameters:**
  **availableSources** – an ordered dictionary of sources to try.
* **Returns:**
  a dictionary with sources, extensions, and mimeTypes.  The
  extensions and mimeTypes list their matching sources in priority order.
  The sources list their supported extensions and mimeTypes with their
  priority.

### large_image.tilesource.nearPowerOfTwo(val1: float, val2: float, tolerance: float = 0.02) → bool

Check if two values are different by nearly a power of two.

* **Parameters:**
  * **val1** – the first value to check.
  * **val2** – the second value to check.
  * **tolerance** – the maximum difference in the log2 ratio’s mantissa.
* **Returns:**
  True if the values are nearly a power of two different from each
  other; false otherwise.

### large_image.tilesource.new(\*args, \*\*kwargs) → [TileSource](#large_image.tilesource.base.TileSource)

Create a new image.

TODO: add specific arguments to choose a source based on criteria.

### large_image.tilesource.open(\*args, \*\*kwargs) → [FileTileSource](#large_image.tilesource.base.FileTileSource)

Alternate name of getTileSource.

Get a tilesource using the known sources.  If tile sources have not yet
been loaded, load them.

* **Returns:**
  A tilesource for the passed arguments.
