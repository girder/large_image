# large_image_converter package

## Submodules

## large_image_converter.format_aperio module

### large_image_converter.format_aperio.adjust_params(geospatial, params, \*\*kwargs)

Adjust options for aperio format.

* **Parameters:**
  * **geospatial** – True if the source is geospatial.
  * **params** – the conversion options.  Possibly modified.
* **Returns:**
  suffix: the recommended suffix for the new file.

### large_image_converter.format_aperio.create_thumbnail_and_label(tempPath, info, ifdCount, needsLabel, labelPosition, \*\*kwargs)

Create a thumbnail and, optionally, label image for the aperio file.

* **Parameters:**
  * **tempPath** – a temporary file in a temporary directory.
  * **info** – the tifftools info that will be written to the tiff tile;
    modified.
  * **ifdCount** – the number of ifds in the first tiled image.  This is 1 if
    there are subifds.
  * **needsLabel** – true if a label image needs to be added.
  * **labelPosition** – the position in the ifd list where a label image
    should be inserted.

### large_image_converter.format_aperio.modify_tiff_before_write(info, ifdIndices, tempPath, lidata, \*\*kwargs)

Adjust the metadata and ifds for a tiff file to make it compatible with
Aperio (svs).

Aperio files are tiff files which are stored without subifds in the order
full res, optional thumbnail, half res, quarter res, …, full res, half
res, quarter res, …, label, macro.  All ifds have an ImageDescription
that start with an aperio header followed by some dimension information and
then an option key-.value list

* **Parameters:**
  * **info** – the tifftools info that will be written to the tiff tile;
    modified.
  * **ifdIndices** – the 0-based index of the full resolution ifd of each
    frame followed by the ifd of the first associated image.
  * **tempPath** – a temporary file in a temporary directory.
  * **lidata** – large_image data including metadata and associated images.

### large_image_converter.format_aperio.modify_tiled_ifd(info, ifd, idx, ifdIndices, lidata, liDesc, \*\*kwargs)

Modify a tiled image to add aperio metadata and ensure tags are set
appropriately.

* **Parameters:**
  * **info** – the tifftools info that will be written to the tiff tile;
    modified.
  * **ifd** – the full resolution ifd as read by tifftools.
  * **idx** – index of this ifd.
  * **ifdIndices** – the 0-based index of the full resolution ifd of each
    frame followed by the ifd of the first associated image.
  * **lidata** – large_image data including metadata and associated images.
  * **liDesc** – the parsed json from the original large_image_converter
    description.

### large_image_converter.format_aperio.modify_vips_image_before_output(image, convertParams, \*\*kwargs)

Make sure the vips image is either 1 or 3 bands.

* **Parameters:**
  * **image** – a vips image.
  * **convertParams** – the parameters that will be used for compression.
* **Returns:**
  a vips image.

## Module contents

### large_image_converter.convert(inputPath, outputPath=None, \*\*kwargs)

Take a source input file and output a pyramidal tiff file.

* **Parameters:**
  * **inputPath** – the path to the input file or base file of a set.
  * **outputPath** – the path of the output file.

Optional parameters that can be specified in kwargs:

* **Parameters:**
  * **tileSize** – the horizontal and vertical tile size.
  * **format** – one of ‘tiff’ or ‘aperio’.  Default is ‘tiff’.
  * **onlyFrame** – None for all frames or the 0-based frame number to just
    convert a single frame of the source.
  * **compression** – one of ‘jpeg’, ‘deflate’ (zip), ‘lzw’, ‘packbits’,
    ‘zstd’, or ‘none’.
  * **quality** – a jpeg or webp quality passed to vips.  0 is small, 100 is
    high quality.  90 or above is recommended.  For webp, 0 is lossless.
  * **level** – compression level for zstd, 1-22 (default is 10) and deflate,
    1-9.
  * **predictor** – one of ‘none’, ‘horizontal’, ‘float’, or ‘yes’ used for
    lzw and deflate.  Default is horizontal for non-geospatial data and yes
    for geospatial.
  * **psnr** – psnr value for jp2k, higher results in large files.  0 is
    lossless.
  * **cr** – jp2k compression ratio.  1 is lossless, 100 will try to make
    a file 1% the size of the original, etc.
  * **subifds** – if True (the default), when creating a multi-frame file,
    store lower resolution tiles in sub-ifds.  If False, store all data in
    primary ifds.
  * **overwrite** – if not True, throw an exception if the output path
    already exists.
  * **keepFloat** – if True, keep float or double data types as they are, if
    possible.

Additional optional parameters:

* **Parameters:**
  * **geospatial** – if not None, a boolean indicating if this file is
    geospatial.  If not specified or None, this will be checked.
  * **\_concurrency** – the number of cpus to use during conversion.  None to
    use the logical cpu count.
* **Returns:**
  outputPath if successful

### large_image_converter.format_hook(funcname, \*args, \*\*kwargs)

Call a function specific to a file format.

* **Parameters:**
  * **funcname** – name of the function.
  * **args** – parameters to pass to the function.
  * **kwargs** – parameters to pass to the function.
* **Returns:**
  dependent on the function.  False to indicate no further
  processing should be done.

### large_image_converter.is_geospatial(path)

Check if a path is likely to be a geospatial file.

* **Parameters:**
  **path** – The path to the file
* **Returns:**
  True if geospatial.

### large_image_converter.is_vips(path, matchSize=None)

Check if a path is readable by vips.

* **Parameters:**
  * **path** – The path to the file
  * **matchSize** – if not None, the image read by vips must be the specified
    (width, height) tuple in pixels.
* **Returns:**
  True if readable by vips.

### large_image_converter.json_serial(obj)

Fallback serializier for json.  This serializes datetime objects to iso
format.

* **Parameters:**
  **obj** – an object to serialize.
* **Returns:**
  a serialized string.
