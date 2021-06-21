Tile Source Options
===================

Each tile source can have custom options that affect how tiles are generated from that tile source.  All tile sources have a basic set of options:

Format
------

Python tile functions can return tile data as images, numpy arrays, or PIL Image objects.  The ``format`` parameter is one of the ``TILE_FORMAT_*`` constants.

Encoding
--------

The ``encoding`` parameter can be one of ``JPEG``, ``PNG``, ``TIFF``, or ``JFIF``.  When the tile is output as an image, this is the preferred format.  Note that ``JFIF`` is a specific variant of ``JPEG`` that will always use either the Y or YCbCr color space as well as constraining other options.

The ``encoding`` only affects output when ``format`` is ``TILE_FORMAT_IMAGE``.

Associated with ``encoding``, some image formats have additional parameters.

- ``JPEG`` and ``JFIF`` can specify ``jpegQuality``, a number from 0 to 100 where 0 is small and 100 is higher-quality, and ``jpegSubsampling``, where 0 is full chrominance data, 1 is half-resolution chrominance, and 2 is quarter-resolution chrominance.

- ``TIFF`` can specify ``tiffCompression``, which is one of the ``libtiff_ctypes.COMPRESSION*`` options.

Edges
-----

When a tile is requested at the right or bottom edge of the image, the tile could extend past the boundary of the image.  If the image is not an even multiple of the tile size, the ``edge`` parameter determines how the tile is generated.  A value of ``None`` or ``False`` will generate a standard sized tile where the area outside of the image space could have pixels of any color.  An ``edge`` value of ``'crop'`` or ``True`` will return a tile that is smaller than the standard size.  A value if the form of a hexadecimal encoded 8-bit-per-channel color (e.g., ``#rrggbb``) will ensure that the area outside of the image space is all that color.

Style
-----

Often tiles are desired as 8-bit-per-sample images.  However, if the tile source is more than 8 bits per sample or has more than 3 channels, some data will be lost.  Similarly, if the data is returned as a numpy array, the range of values returned can vary by tile source.  The ``style`` parameter can remap samples values and determine how channels are composited.

If ``style`` is not specified or None, the default stype for the file is used.  Otherwise, this is a json-encoded string that contains an object with a key of ``bands`` consisting of an array of band definitions.  If only one band is needed, a json-encoded string of just the band definition can be used.

A band definition is an object which can contain the following keys:

- ``band``: if -1 or None, the greyscale value is used.  Otherwise, a 1-based numerical index into the channels of the image or a string that matches the interpretation of the band ('red', 'green', 'blue', 'gray', 'alpha').  Note that 'gray' on an RGB or RGBA image will use the green band.

- ``frame``: if specified, override the frame parameter used in the tile query for this band.  Note that it is more efficient to have at least one band not specify a frame parameter or use the same value as the basic query.  Defaults to the frame value of the core query.

- ``framedelta``: if specified, and ``frame`` is not specified, override the frame parameter used in the tile query for this band by adding the value to the current frame number.  If many different frames are being requested, all with the same ``framedelta``, this is more efficient than varying the ``frame`` within the style.

- ``min``: the value to map to the first palette value.  Defaults to 0.  'auto' to use 0 if the reported minimum and maximum of the band are between [0, 255] or use the reported minimum otherwise.  'min' or 'max' to always uses the reported minimum or maximum.

- ``max``: the value to map to the last palette value.  Defaults to 255.  'auto' to use 0 if the reported minimum and maximum of the band are between [0, 255] or use the reported maximum otherwise.  'min' or 'max' to always uses the reported minimum or maximum.

- ``palette``: a list of two or more color strings, where color strings are of the form #RRGGBB, #RRGGBBAA, #RGB, #RGBA.  The values between min and max are interpolated using a piecewise linear algorithm to map to the specified palette values.

- ``nodata``: the value to use for missing data.  null or unset to not use a nodata value.

- ``composite``: either 'lighten' or 'multiply'.  Defaults to 'lighten' for all except the alpha band.

- ``clamp``: either True to clamp (also called clip or crop) values outside of the [min, max] to the ends of the palette or False to make outside values transparent.

Note that some tile sources add additional options to the ``style`` parameter.

Examples
++++++++

Swap the red and green channels of a three color image
______________________________________________________

.. code-block::

  style = {"bands": [
    {"band": 1, "palette": ["#000", "#0f0"]},
    {"band": 2, "palette": ["#000", "#f00"]},
    {"band": 3, "palette": ["#000", "#00f"]}
  ]}

Apply a gamma correction to the image
_____________________________________

This used a precomputed sixteen entry greyscale palette, computed as ``(value / 255) ** gamma * 255``, where ``value`` is one of [0, 17, 34, 51, 68, 85, 102, 119, 136, 153, 170, 187, 204, 221, 238, 255] and gamma is ``0.5``.

.. code-block::

  style = {"palette": [
    "#000000", "#414141", "#5D5D5D", "#727272",
    "#838383", "#939393", "#A1A1A1", "#AEAEAE",
    "#BABABA", "#C5C5C5", "#D0D0D0", "#DADADA",
    "#E4E4E4", "#EDEDED", "#F6F6F6", "#FFFFFF"
  ]}
