# large_image.tilesource.eager_utils package

## Submodules

## large_image.tilesource.eager_utils.eager_fn module

Share eager iterator callables with worker processes.

### large_image.tilesource.eager_utils.eager_fn.get_transform() → Callable | None

Return the process-local eager transform callable.

* **Returns:**
  The callable set by set_transform, or None if unset.

### large_image.tilesource.eager_utils.eager_fn.get_transform_scale() → Callable | None

Return the process-local eager transform-scale callable.

* **Returns:**
  The callable set by set_transform_scale, or None if unset.

### large_image.tilesource.eager_utils.eager_fn.set_transform(fn: Callable) → None

Store the process-local eager transform callable.

* **Parameters:**
  **fn** – A callable function with either one or three arguments that takes
  in a numpy array containing image data and returns a numpy array containing
  the transformed image data. If the function has three arguments, the first
  argument is the image data, the second argument is the x coordinate of the
  tile, and the third argument is the y coordinate of the tile as tile number
  (transform save mode: tile_x_y) or base pixel coordinates
  (transform save mode: region_x_y).
* **Returns:**
  None.

### large_image.tilesource.eager_utils.eager_fn.set_transform_scale(fn: Callable) → None

Store the process-local eager transform-scale callable.

* **Parameters:**
  **fn** – a callable function that takes in a numpy array of read_kwargs,
  a slide_dimensions dictionary, and returns a tuple containing the read coordinates,
  tile size, and target scale metadata in the following order: xlt, ytt,
  xrt, ybt, mm_x, mm_y, tile_size, target_scale, conv_mm_x, conv_mm_y.
  See default_region_coords_and_target_scale_from_read_args in
  eager_read_args.py for more details.
* **Returns:**
  None.

## large_image.tilesource.eager_utils.eager_image_modifications module

Image padding and color conversion helpers for eager reads.

### large_image.tilesource.eager_utils.eager_image_modifications.pad_chunk_if_necessary(slide_dimensions: dict, chunk: ndarray, xlt: ndarray, xrt: ndarray, ytt: ndarray, ybt: ndarray, w: int, h: int, pad_mode: str = 'wsi_edge', pad_fill_mode: str = 'default')

Pad a chunk when it is smaller than the requested read window.

* **Parameters:**
  * **slide_dimensions** – Slide dimension metadata for the selected region.
  * **chunk** – Chunk image array returned by the tile source.
  * **xlt** – Left coordinates for requested tiles or regions.
  * **xrt** – Right coordinates for requested tiles or regions.
  * **ytt** – Top coordinates for requested tiles or regions.
  * **ybt** – Bottom coordinates for requested tiles or regions.
  * **w** – Desired output width.
  * **h** – Desired output height.
  * **pad_mode** – Padding placement mode.
  * **pad_fill_mode** – Fill mode passed to return_constant_color.
* **Returns:**
  The padded chunk, or the original chunk if padding is unnecessary.

### large_image.tilesource.eager_utils.eager_image_modifications.pad_color(image: ndarray, top: int, bottom: int, left: int, right: int, color: tuple)

Pad an image with a constant RGB color.

* **Parameters:**
  * **image** – Image array in HWC layout.
  * **top** – Number of rows to add above the image.
  * **bottom** – Number of rows to add below the image.
  * **left** – Number of columns to add before the image.
  * **right** – Number of columns to add after the image.
  * **color** – RGB color tuple used for the padded pixels.
* **Returns:**
  The padded image array.

### large_image.tilesource.eager_utils.eager_image_modifications.pad_region_chunk(chunk: ndarray, xlo: list, yto: list, wo: list, ho: list)

Pad a region chunk to cover the requested region coordinates.

* **Parameters:**
  * **chunk** – Chunk image array returned by the tile source.
  * **xlo** – Left offsets within the chunk.
  * **yto** – Top offsets within the chunk.
  * **wo** – Right offsets within the chunk.
  * **ho** – Bottom offsets within the chunk.
* **Returns:**
  The padded chunk.

### large_image.tilesource.eager_utils.eager_image_modifications.pad_tile(tile: ndarray, w: int, h: int, pad_mode: str, pad_fill_mode: str)

Pad a tile to a target width and height.

* **Parameters:**
  * **tile** – Tile image in HWC layout.
  * **w** – Desired output width.
  * **h** – Desired output height.
  * **pad_mode** – Padding placement mode, either ‘equal’ or ‘right_bottom’.
  * **pad_fill_mode** – Fill mode passed to return_constant_color.
* **Returns:**
  A tile padded to the requested size.

### large_image.tilesource.eager_utils.eager_image_modifications.padding(array: ndarray, xx: int, yy: int)

Pad a two-dimensional or image array to a requested size.

* **Parameters:**
  * **array** – Input array to pad.
  * **xx** – Desired output height.
  * **yy** – Desired output width.
* **Returns:**
  The padded array.

### large_image.tilesource.eager_utils.eager_image_modifications.remove_unnecessary_image_information(slide_dimensions: dict, chunk: ndarray, xlt: ndarray, xrt: ndarray, ytt: ndarray, ybt: ndarray, pad_fill_mode: str)

Fill chunk pixels that extend beyond the selected slide region.

* **Parameters:**
  * **slide_dimensions** – Slide dimension metadata for the selected region.
  * **chunk** – Chunk image array to update in place.
  * **xlt** – Left coordinates for requested tiles or regions.
  * **xrt** – Right coordinates for requested tiles or regions.
  * **ytt** – Top coordinates for requested tiles or regions.
  * **ybt** – Bottom coordinates for requested tiles or regions.
  * **pad_fill_mode** – Fill mode passed to return_constant_color.
* **Returns:**
  None; chunk is modified in place.

### large_image.tilesource.eager_utils.eager_image_modifications.return_constant_color(image: ndarray, pad_fill_mode: Any)

Resolve the RGB color used for padding.

* **Parameters:**
  * **image** – Source image used by data-dependent fill modes.
  * **pad_fill_mode** – Fill mode, RGB tuple, or scalar channel value.
* **Returns:**
  An RGB color tuple.

### large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_equal(image: ndarray, w: int, h: int)

Calculate symmetric padding for a target tile size.

* **Parameters:**
  * **image** – Image array to pad.
  * **w** – Desired output width.
  * **h** – Desired output height.
* **Returns:**
  Padding as top, bottom, left, and right pixel counts.

### large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_right_bottom(image: ndarray, w: int, h: int)

Calculate padding that extends only the right and bottom edges.

* **Parameters:**
  * **image** – Image array to pad.
  * **w** – Desired output width.
  * **h** – Desired output height.
* **Returns:**
  Padding as top, bottom, left, and right pixel counts.

### large_image.tilesource.eager_utils.eager_image_modifications.return_needed_padding_wsi_edge(image: ndarray, w: int, h: int, t_dist: int, b_dist: int, l_dist: int, r_dist: int)

Calculate padding amounts that preserve whole-slide-image edge alignment.

* **Parameters:**
  * **image** – Image array to pad.
  * **w** – Desired output width.
  * **h** – Desired output height.
  * **t_dist** – Distance from the image top edge.
  * **b_dist** – Distance from the image bottom edge.
  * **l_dist** – Distance from the image left edge.
  * **r_dist** – Distance from the image right edge.
* **Returns:**
  Padding as top, bottom, left, and right pixel counts.

### large_image.tilesource.eager_utils.eager_image_modifications.rgba2rgb(img_rgba: ndarray, background: tuple = (255, 255, 255))

Convert an RGBA image to RGB by compositing over a background color.

* **Parameters:**
  * **img_rgba** – Input RGB or RGBA image as a numpy array.
  * **background** – RGB background color used for transparent pixels.
* **Returns:**
  An RGB numpy array.

## large_image.tilesource.eager_utils.eager_pytorch_threading_context module

Context manager for temporarily limiting PyTorch thread counts.

## large_image.tilesource.eager_utils.eager_read_args module

Read argument planning helpers for eager tile and region batches.

### large_image.tilesource.eager_utils.eager_read_args.check_edge_condition(base_size_x: int, base_size_y: int, sorted_in: ndarray, edge: bool = False)

Optionally discard read arguments that cross image boundaries.

* **Parameters:**
  * **base_size_x** – Base image width in pixels.
  * **base_size_y** – Base image height in pixels.
  * **sorted_in** – Sorted tile or region read argument array.
  * **edge** – If True, discard entries that extend beyond the base image.
* **Returns:**
  A tuple of filtered read arguments and the number discarded.

### large_image.tilesource.eager_utils.eager_read_args.chunks_from_kd_tree(sorted_in: ndarray, used: ndarray, points: ndarray, tree: KDTree, chunks: list, chunk_size: int, k_mod: int = 1)

Append unused nearest-neighbor read arguments to sparse chunks.

* **Parameters:**
  * **sorted_in** – Sorted tile or region read argument array.
  * **used** – Boolean mask tracking rows already assigned to a chunk.
  * **points** – Coordinate points used for nearest-neighbor grouping.
  * **tree** – KD-tree built from points.
  * **chunks** – Existing list of chunks to append to.
  * **chunk_size** – Target number of read arguments per chunk.
  * **k_mod** – Multiplier used when widening nearest-neighbor searches.
* **Returns:**
  The updated list of read argument chunks.

### large_image.tilesource.eager_utils.eager_read_args.default_region_coords_and_target_scale_from_read_args(read_kwargs: ndarray, slide_dimensions: dict, include_mm: bool = True)

Extract read coordinates and target scale from read arguments.

* **Parameters:**
  * **read_kwargs** – Read argument array produced by eager read argument generators.
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **include_mm** – If True, include per-read mm scale columns in the output.
* **Returns:**
  Coordinates, mm metadata, tile size, target scale, and conversion factors.

### large_image.tilesource.eager_utils.eager_read_args.gen_read_args_complete_grid(sorted_tiles: ndarray, chunk_mult: int)

Group tile read arguments for a complete rectangular grid.

* **Parameters:**
  * **sorted_tiles** – Tile read argument array sorted by tile row and column.
  * **chunk_mult** – Width and height, in tiles, of each grouped read chunk.
* **Returns:**
  A list of numpy arrays, one per read chunk.

### large_image.tilesource.eager_utils.eager_read_args.gen_read_args_for_regions(slide_dimensions: dict, regions: list | ndarray, edge: bool = False, chunk_mult: int = 2)

Generate grouped read arguments for explicit output regions.

* **Parameters:**
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **regions** – Regions in top, left, height, width order.
  * **edge** – If True, discard regions that extend beyond the base image.
  * **chunk_mult** – Chunk side length multiplier; chunk size is chunk_mult squared.
* **Returns:**
  A list of numpy arrays containing grouped region read arguments.

### large_image.tilesource.eager_utils.eager_read_args.gen_read_args_for_tiles(n_possible_tiles: int, slide_dimensions: dict, tiles: list | ndarray, edge: bool = False, chunk_mult: int = 2, region: dict[str, Any] | None = None)

Generate grouped read arguments for output tiles.

* **Parameters:**
  * **n_possible_tiles** – Number of tiles in the full target grid.
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **tiles** – Tile indexes in row, column order.
  * **edge** – If True, discard tiles that extend beyond the base image.
  * **chunk_mult** – Chunk side length multiplier; chunk size is chunk_mult squared.
  * **region** – Optional region used to clip tile coordinates to region bounds.
* **Returns:**
  A list of numpy arrays containing grouped tile read arguments.

### large_image.tilesource.eager_utils.eager_read_args.gen_read_args_incomplete_grid(sorted_in: ndarray, chunk_size: int)

Generate read argument chunks for a sparse or incomplete grid.

* **Parameters:**
  * **sorted_in** – Sorted tile or region read argument array.
  * **chunk_size** – Target number of read arguments per chunk.
* **Returns:**
  A list of numpy arrays, one per read chunk.

### large_image.tilesource.eager_utils.eager_read_args.sparse_chunks(sorted_in: ndarray, used: ndarray, points: ndarray, tree: KDTree, chunks: list, chunk_size: int, k_mod: int = 1)

Build read chunks for sparse or incomplete tile and region grids.

* **Parameters:**
  * **sorted_in** – Sorted tile or region read argument array.
  * **used** – Boolean mask tracking rows already assigned to a chunk.
  * **points** – Coordinate points used for nearest-neighbor grouping.
  * **tree** – KD-tree built from points.
  * **chunks** – Existing list of chunks to append to.
  * **chunk_size** – Target number of read arguments per chunk.
  * **k_mod** – Multiplier used when widening nearest-neighbor searches.
* **Returns:**
  The updated list of read argument chunks.

## large_image.tilesource.eager_utils.eager_shared_array module

Shared-memory array wrapper used by eager worker processes.

### *class* large_image.tilesource.eager_utils.eager_shared_array.SharedArray(shape: tuple | list, dtype: Any, is_torch: bool = False, enable_mm: bool = False)

Bases: `object`

Shared-memory array wrapper used by eager worker processes.

Create a shared-memory array.

* **Parameters:**
  * **shape** – Shape of the image batch buffer.
  * **dtype** – Numpy or torch dtype stored by the buffer.
  * **is_torch** – If True, expose the buffer as a torch tensor.
  * **enable_mm** – If True, create a second shared buffer for mm scale metadata.
* **Returns:**
  None.

#### close() → None

Release the shared-memory resources owned by this array.

* **Returns:**
  None.

#### copy(arr: ndarray | torch.Tensor)

Copy an array into the shared-memory buffer.

* **Parameters:**
  **arr** – Numpy array or torch tensor to copy.
* **Returns:**
  None.

#### insert(arr: ndarray | torch.Tensor, i: int)

Insert an array into a batch slot.

* **Parameters:**
  * **arr** – Numpy array or torch tensor to insert.
  * **i** – Batch index to update.
* **Returns:**
  None.

#### insert_mm(mm_x: float, mm_y: float, i: int)

Insert per-item mm scale metadata into a batch slot.

* **Parameters:**
  * **mm_x** – Horizontal pixel size in millimeters.
  * **mm_y** – Vertical pixel size in millimeters.
  * **i** – Batch index to update.
* **Returns:**
  None.

#### mm_view()

Return a view of the shared mm scale metadata buffer.

* **Returns:**
  A numpy array with [mm_y, mm_x] columns.

#### resize_shm(shape: tuple | list)

Update the logical shape and byte size for the shared buffer.

* **Parameters:**
  **shape** – New shape for the shared image batch buffer.
* **Returns:**
  None.

#### tobytes()

Return the shared-memory contents as bytes.

* **Returns:**
  The byte representation of the current image buffer.

#### view()

Return an array or tensor view of the shared image buffer.

* **Returns:**
  A numpy array or torch tensor backed by shared memory.

## large_image.tilesource.eager_utils.eager_wsi_operations module

Whole-slide geometry and scaling helpers for eager reads.

### large_image.tilesource.eager_utils.eager_wsi_operations.calculate_slide_dimensions(source: [large_image.tilesource.base.TileSource](large_image.tilesource.md#large_image.tilesource.base.TileSource), region: dict[str, int] | None = None, scale: dict[str, Any] | None = None, tile_size: dict[str, int] | None = None, source_scale: dict[str, Any] | None = None, \*\*kwargs)

Calculate slide geometry for eager reads.

* **Parameters:**
  * **source** – Large Image tile source used for metadata and scale conversion.
  * **region** – Optional region with left, top, width, height, and units.
  * **scale** – Optional target scale using magnification or mm_x and mm_y.
  * **tile_size** – Optional output tile size with width and height in pixels.
  * **source_scale** – Source scale used when region units are mag_pixels.
  * **kwargs** – Additional options reserved for compatibility.
* **Returns:**
  A slide dimension dictionary used by eager read planning and workers.

### large_image.tilesource.eager_utils.eager_wsi_operations.generate_assumptions_for_x_y_given_mag(x, y, z)

Estimate pixel sizes from magnification when metadata is incomplete.

* **Parameters:**
  * **x** – Existing horizontal pixel size, or None.
  * **y** – Existing vertical pixel size, or None.
  * **z** – Magnification used to estimate missing pixel sizes.
* **Returns:**
  Estimated x, y, and z values.

### large_image.tilesource.eager_utils.eager_wsi_operations.get_base_mm_from_meta(source_meta)

Return base pixel sizes from source metadata.

* **Parameters:**
  **source_meta** – Metadata dictionary from a tile source.
* **Returns:**
  The base mm_x and mm_y values.

### large_image.tilesource.eager_utils.eager_wsi_operations.get_patch_from_mask_for_tile(mask: ndarray, slide_dimensions: dict, tile: list)

Return the mask patch corresponding to a tile index.

* **Parameters:**
  * **mask** – Whole-slide mask image.
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **tile** – Tile index in row, column order.
* **Returns:**
  A mask patch for the requested tile.

### large_image.tilesource.eager_utils.eager_wsi_operations.get_scaling_values_from_meta(source_meta: dict, scale: dict[str, Any] | None = None)

Calculate base and target scaling values from source metadata.

* **Parameters:**
  * **source_meta** – Metadata dictionary from a tile source.
  * **scale** – Scale request with either magnification or mm_x and mm_y values.
* **Returns:**
  A dictionary with base and target mm and magnification values.

### large_image.tilesource.eager_utils.eager_wsi_operations.get_smallest_bounding_box(roi)

Return the smallest bounding box that contains an ROI polygon.

* **Parameters:**
  **roi** – ROI dictionary with a points sequence containing x and y coordinates.
* **Returns:**
  The top-left and bottom-right coordinate pairs.

### large_image.tilesource.eager_utils.eager_wsi_operations.return_relevant_tile_indexes_for_slide_dim(slide_dimensions: dict, tile_overlap: dict[str, int] | dict[str, float] | None = None)

Return tile indexes covering the target slide dimensions.

* **Parameters:**
  * **slide_dimensions** – Slide dimension metadata from calculate_slide_dimensions.
  * **tile_overlap** – Optional x and y tile overlap as pixels or fractions.
* **Returns:**
  A numpy array of tile indexes in row, column order.

### large_image.tilesource.eager_utils.eager_wsi_operations.return_target_scaling_feature(feature)

Normalize a target scaling value to a float.

* **Parameters:**
  **feature** – Scaling value as a string, integer, float, or None.
* **Returns:**
  The scaling value as a float, or None if it cannot be converted.

### large_image.tilesource.eager_utils.eager_wsi_operations.return_tile_slides_meeting_area_threshold(mask: ndarray, slide_dim: dict, tiles: list | ndarray, area_threshold: float = 0.25, threshold_mask: float = 100)

Filter tile indexes by the amount of mask signal they contain.

* **Parameters:**
  * **mask** – Whole-slide mask image used to score candidate tiles.
  * **slide_dim** – Slide dimension metadata from calculate_slide_dimensions.
  * **tiles** – Candidate tile indexes in row, column order.
  * **area_threshold** – Minimum mask-signal fraction required for a tile.
  * **threshold_mask** – Minimum mask pixel value considered signal.
* **Returns:**
  A list of tile indexes that meet the threshold.

## Module contents

Utilities used by the eager tile iterator.
