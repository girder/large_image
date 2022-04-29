Example Usage
=============

The large_image library can be used to read and access different file formats.  There are several common usage patterns.  These examples use ``sample.tiff`` as an example -- any readable image cane be used in this case.

Image Metadata
--------------

All images have metadata that include the base image size, the base tile size, the number of conceptual levels, and information about the size of a pixel in the image if it is known.

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    print(source.getMetadata())

This might print a result like::

    {
        'levels': 9,
        'sizeX': 58368,
        'sizeY': 12288,
        'tileWidth': 256,
        'tileHeight': 256,
        'magnification': 40.0,
        'mm_x': 0.00025,
        'mm_y': 0.00025
    }

``levels`` doesn't actually tell which resolutions are present in the file.  It is the number of levels that can be requested from the ``getTile`` method.  The levels can also be computed via ``ceil(log(max(sizeX / tileWidth, sizeY / tileHeight)) / log(2)) + 1``.

The ``mm_x`` and ``mm_y`` values are the size of a pixel in millimeters.  These can be ``None`` if the value is unknown.  The ``magnification`` is that reported by the file itself, and may be ``None``.  The magnification can be approximated by ``0.01 / mm_x``.

Getting a Region of an Image
----------------------------

You can get a portion of an image at different resolutions and in different formats.  Internally, the large_image library reads the minimum amount of the file necessary to return the requested data, caching partial results in many instances so that a subsequent query may be faster.

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    image, mime_type = source.getRegion(
        region=dict(left=1000, top=500, right=11000, bottom=1500),
        output=dict(maxWidth=1000),
        encoding='PNG')
    # image is a PNG that is 1000 x 100.  Specifically, it will be a bytes
    # object that represent a PNG encoded image.

You could also get this as a ``numpy`` array:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    nparray, mime_type = source.getRegion(
        region=dict(left=1000, top=500, right=11000, bottom=1500),
        output=dict(maxWidth=1000),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    # Our source image happens to be RGB, so nparray is a numpy array of shape
    # (100, 1000, 3)

You can specify the size in physical coordinates:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    nparray, mime_type = source.getRegion(
        region=dict(left=0.25, top=0.125, right=2.75, bottom=0.375, units='mm'),
        scale=dict(mm_x=0.0025),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    # Since our source image had mm_x = 0.00025 for its scale, this has the
    # same result as the previous example.

Tile Serving
------------

One of the uses of large_image is to get tiles that can be used in image or map viewers.  Most of these viewers expect tiles that are a fixed size and known resolution.  The ``getTile`` method returns tiles as stored in the original image and the original tile size.  If there are missing levels, these are synthesized -- this is only done for missing powers-of-two levels or missing tiles. For instance,

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    # getTile takes x, y, z, where x and y are the tile location within the
    # level and z is level where 0 is the lowest resolution.
    tile0 = source.getTile(0, 0, 0)
    # tile0 is the lowest resolution tile that shows the whole image.  It will
    # be a JPEG or PNG or some other image format depending on the source
    tile002 = source.getTile(0, 0, 2)
    # tile002 will be a tile representing no more than 1/4 the width of the
    # image in the upper-left corner.  Since the z (third parameter) is 2, the
    # level will have up to 2**2 x 2**2 (4 x 4) tiles.  An image doesn't
    # necessarily have all tiles in that range, as the image may not be square.

Some methods such as ``getRegion`` and ``getThumbnail`` allow you to specify format on the fly.  But note that since tiles need to be cached in a consistent format, ``getTile`` always returns the same format depending on what encoding was specified when it was opened:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff', encoding='PNG')
    tile0 = source.getTile(0, 0, 0)
    # tile is now guaranteed to be a PNG

Tiles are always ``tileWidth`` by ``tileHeight`` in pixels.  At the maximum level (``z = levels - 1``), the number of tiles in that level will range in ``x`` from ``0`` to strictly less than ``sizeX / tileWidth``, and ``y`` from ``0`` to strictly less than ``sizeY / tileHeight``.  For each lower level, the is a power of two less tiles.  For instance, when ``z = levels - 2``, ``x`` ranges from ``0`` to less than ``sizeX / tileWidth / 2``; at ``z = levels - 3``, ``x`` is less than ``sizeX / tileWidth / 4``.

Iterating Across an Image
-------------------------

Since most images are too large to conveniently fit in memory, it is useful to iterate through the image.  This can take the same parameters as ``getRegion`` to pick an output size and scale, but can also specify a tile size and overlap.  You can also get a specific tile with those parameters.  This tiling doesn't have to have any correspondence to the tiling of the original file.

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    for tile in source.tileIterator(
        tile_size=dict(width=512, height=512),
        format=large_image.constants.TILE_FORMAT_NUMPY
    ):
        # tile is a dictionary of information about the specific tile
        # tile['tile'] contains the actual numpy or image data
        print(tile['x'], tile['y'], tile['tile'].shape)
        # This will print something like:
        #   0 0 (512, 512, 3)
        #   512 0 (512, 512, 3)
        #   1024 0 (512, 512, 3)
        #   ...
        #   56832 11776 (512, 512, 3)
        #   57344 11776 (512, 512, 3)
        #   57856 11776 (512, 512, 3)

You can overlap tiles.  For instance, if you are running an algorithm where there are edge effects, you probably want an overlap that is big enough that you can trim off or ignore those effects:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    for tile in source.tileIterator(
        tile_size=dict(width=2048, height=2048),
        tile_overlap=dict(x=128, y=128, edges=False),
        format=large_image.constants.TILE_FORMAT_NUMPY
    ):
        print(tile['x'], tile['y'], tile['tile'].shape)
        # This will print something like:
        #   0 0 (2048, 2048, 3)
        #   1920 0 (2048, 2048, 3)
        #   3840 0 (2048, 2048, 3)
        #   ...
        #   53760 11520 (768, 2048, 3)
        #   55680 11520 (768, 2048, 3)
        #   57600 11520 (768, 768, 3)

Getting a Thumbnail
-------------------

You can get a thumbnail of an image in different formats or resolutions.  The default is typically JPEG and no larger than 256 x 256.  Getting a thumbnail is essentially the same as doing ``getRegion``, except that it always uses the entire image and has a maximum width and/or height.

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    image, mime_type = source.getThumbnail()
    open('thumb.jpg', 'wb').write(image)

You can get the thumbnail in other image formats and sizes:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    image, mime_type = source.getThumbnail(width=640, height=480, encoding='PNG')
    open('thumb.png', 'wb').write(image)

Associated Images
-----------------

Many digital pathology images (also called whole slide images or WSI) contain secondary images that have additional information.  This commonly includes label and macro images.  A label image is a separate image of just the label of a slide.  A macro image is a small image of these entire slide or the entire slide excluding the label.  There can be other associated images, too.

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff')
    print(source.getAssociatedImagesList())
    # This prints something like:
    #   ['label', 'macro']
    image, mime_type = source.getAssociatedImage('macro')
    # image is a binary image, such as a JPEG
    image, mime_type = source.getAssociatedImage('macro', encoding='PNG')
    # image is now a PNG
    image, mime_type = source.getAssociatedImage('macro', format=large_image.constants.TILE_FORMAT_NUMPY)
    # image is now a numpy array

You can get associated images in different encodings and formats.  The entire image is always returned.

Projections
-----------

large_image handles geospatial images.  These can be handled as any other image in pixel-space by just opening them normally.  Alternately, these can be opened with a projection and then referenced using that projection.

.. code-block:: python

    import large_image
    # Open in Web Mercator projection
    source = large_image.open('sample.geo.tiff', projection='EPSG:3857')
    print(source.getMetadata()['bounds'])
    # This will have the corners in Web Mercator meters, the projection, and
    # the minimum and maximum ranges.
    #   We could also have done
    print(source.getBounds())
    # The 0, 0, 0 tile is now the whole world excepting the poles
    tile0 = source.getTile(0, 0, 0)

Images with Multiple Frames
---------------------------

Some images have multiple "frames".  Conceptually, these are images that could have multiple channels as separate images, such as those from fluorescence microscopy, multiple "z" values from serial sectioning of thick tissue or adjustment of focal plane in a microscope, multiple time ("t") values, or multiple regions of interest (frequently referred as "xy", "p", or "v" values).

Any of the frames of such an image are accessed by adding a ``frame=<integer>`` parameter to the ``getTile``, ``getRegion``, ``tileIterator``, or other methods.

.. code-block:: python

    import large_image
    source = large_image.open('sample.ome.tiff')
    print(source.getMetadata())
    # This will print something like
    #   {
    #     'magnification': 8.130081300813009,
    #     'mm_x': 0.00123,
    #     'mm_y': 0.00123,
    #     'sizeX': 2106,
    #     'sizeY': 2016,
    #     'tileHeight': 1024,
    #     'tileWidth': 1024,
    #     'IndexRange': {'IndexC': 3},
    #     'IndexStride': {'IndexC': 1},
    #     'frames': [
    #       {'Frame': 0, 'Index': 0, 'IndexC': 0, 'IndexT': 0, 'IndexZ': 0},
    #       {'Frame': 1, 'Index': 0, 'IndexC': 1, 'IndexT': 0, 'IndexZ': 0},
    #       {'Frame': 2, 'Index': 0, 'IndexC': 2, 'IndexT': 0, 'IndexZ': 0}
    #     ]
    #   }
    nparray, mime_type = source.getRegion(
        frame=1,
        format=large_image.constants.TILE_FORMAT_NUMPY)
    # nparray will contain data from the middle channel image

Styles - Changing colors, scales, and other properties
------------------------------------------------------

By default, reading from an image gets the values stored in the image file.  If you get a JPEG or PNG as the output, the values will be 8-bit per channel.  If you get values as a numpy array, they will have their original resolution.  Depending on the source image, this could be 16-bit per channel, floats, or other data types.

Especially when working with high bit-depth images, it can be useful to modify the output.  For example, you can adjust the color range:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff', style={'min': 'min', 'max': 'max'})
    # now, any calls to getRegion, getTile, tileIterator, etc. will adjust the
    # intensity so that the lowest value is mapped to black and the brightest
    # value is mapped to white.
    image, mime_type = source.getRegion(
        region=dict(left=1000, top=500, right=11000, bottom=1500),
        output=dict(maxWidth=1000))
    # image will use the full dynamic range

You can also composite a multi-frame image into a false-color output:

.. code-block:: python

    import large_image
    source = large_image.open('sample.tiff', style={'bands': [
        {'frame': 0, 'min': 'min', 'max': 'max', 'palette': '#f00'},
        {'frame': 3, 'min': 'min', 'max': 'max', 'palette': '#0f0'},
        {'frame': 4, 'min': 'min', 'max': 'max', 'palette': '#00f'},
    ]})
    # Composite frames 0, 3, and 4 to red, green, and blue channels.
    image, mime_type = source.getRegion(
        region=dict(left=1000, top=500, right=11000, bottom=1500),
        output=dict(maxWidth=1000))
    # image is false-color and full dynamic range of specific frames

Writing an Image
----------------

If you wish to visualize numpy data, large_image can write a tiled tiff.  This requires a tile source that supports writing to be installed.  As of this writing, only the ``large-image-source-vips`` source supports this.

.. code-block:: python

    import large_image
    source = large_image.new()
    for nparray, x, y in fancy_algorithm():
        # We could optionally add a mask to limit the output
        source.addTile(nparray, x, y)
    source.write('/tmp/sample.tiff', lossy=False)
