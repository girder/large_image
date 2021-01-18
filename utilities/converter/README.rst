*********************
Large Image Converter
*********************

Convert a variety of images into the most efficient format for Large Image.

Geospatial files are converted into cloud-optimized geotiff_ via gdal_translate.
Single-image non-geospatial files are converted into pyramidal tiff files via pyvips.
Multi-image tiff files are converted into tiff files with multiple pyramidal tiff images and have a custom image description to store frame details.

Some files can be read via the various tile sources in large_image without conversion but are inefficient (for example, uncompressed data in nd2 files).  Converting these files will result in more efficient data access.

Installation
============

To install via pip with custom-built wheels:

``pip install large-image-converter[sources] --find-links https://girder.github.io/large_image_wheels``

The ``[sources]`` extra requirement is optional.  When specified, all of the default large-image tile sources are installed for additional metadata extraction and format support.

Requirements
------------

If the custom-built wheels do not cover your platform, or you want to use different versions of tools, you can install the prerequisites manually.  For full functionality, the following packages and libraries are needed:

- GDAL 3.1.0 or greater, including the command-line tools and the python library
- libtiff, including the command-line tools
- libvips

Additionally, the various tile sources for large_image can be used to read input files to extract and preserve metadata and to read files that can't be read via libvips or GDAL.  The requirements of those sources need to be installed.

Usage
=====

Command Line
------------

In the simplest use, an image can be converted via:

``large_image_converter <source path>``

An output image will be generated in the same directory as the source image.

The full list of options can be obtained via:

``large_image_converter --help``

From Python
-----------

The convert function contains all of the main functionality::

    from large_image_converter import convert

    convert(<source path>)

    # See the options
    print(convert.__doc__)

From Girder
-----------

The converter is installed by default when ``girder-large-image`` is installed.  It relies on Girder Worker to actually run the conversion.

The conversion task can be reached via the user interface on the item details pages, via the ``createImageItem`` method on the ``ImageItem`` model, or via the ``POST`` ``item/{itemId}/tiles`` endpoint.

Limitations and Future Development
==================================

There are some limitations that may be improved with additional development.

- For some multi-image files, such as OME Tiff files that cannot be read by an existing large_image tile source, the specific channel, z-value, or time step is not converted to readily useable metadata.

- Whether the original file is stored in a lossy or lossless format is not always determined.  If unknown, the output defaults to lossless, which may be needlessly large.

.. _geotiff: https://gdal.org/drivers/raster/cog.html
