Large Image
===========

.. image:: https://img.shields.io/circleci/build/github/girder/large_image.svg
  :target: https://circleci.com/gh/girder/large_image
  :alt: Build Status

.. image:: https://img.shields.io/badge/license-Apache%202-blue.svg
  :target: https://raw.githubusercontent.com/girder/large_image/master/LICENSE
  :alt: License

.. image:: https://img.shields.io/codecov/c/github/girder/large_image.svg
  :target: https://codecov.io/github/girder/large_image?branch=master
  :alt: codecov.io

.. image:: https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4562625-blue.svg
  :target: https://doi.org/10.5281/zenodo.4562625

.. image:: https://img.shields.io/pypi/v/large-image.svg?logo=python&logoColor=white
  :target: https://pypi.org/project/large-image/

*Python modules to work with large, multiresolution images.*

Large Image is developed and maintained by the Data & Analytics group at `Kitware, Inc. <https://kitware.com>`_ for processing large geospatial and medical images. This provides the backbone for several of our image analysis platforms including `Resonant GeoData <https://github.com/ResonantGeoData/ResonantGeoData>`_, `HistomicsUI <https://github.com/DigitalSlideArchive/HistomicsUI>`_, and `the Digital Slide Archive <https://digitalslidearchive.github.io/digital_slide_archive/>`_.


Highlights
----------

- Tile serving made easy
- Supports a wide variety of geospatial and medical image formats
- Convert to tiled Cloud Optimized (Geo)Tiffs (also known as pyramidal tiffs)
- Python methods for retiling or accessing regions of images efficiently
- Options for restyling tiles, such as dynamically applying color and band transform


Installation
------------

In addition to installing the base ``large-image`` package, you'll need at least one tile source which corresponds to your target file format(s) (a ``large-image-source-xxx`` package).   You can install everything from the main project with one of these commands:

Pip
~~~

Install common tile sources on linux, OSX, or Windows::

    pip install large-image[common]

Install all tile sources on linux::

    pip install large-image[all] --find-links https://girder.github.io/large_image_wheels

When using large-image with an instance of `Girder`_, install all tile sources and all Girder plugins on linux::

    pip install large-image[all] girder-large-image-annotation[tasks] --find-links https://girder.github.io/large_image_wheels


Conda
~~~~~

Conda makes dependency management a bit easier if not on Linux. The base module, converter module, and two of the source modules are available on conda-forge. You can install the following::

    conda install -c conda-forge large-image
    conda install -c conda-forge large-image-source-gdal
    conda install -c conda-forge large-image-source-tiff
    conda install -c conda-forge large-image-converter


Docker Image
~~~~~~~~~~~~

Included in this repository’s packages is a pre-built Docker image that has all
of the dependencies to read any supported image format.

This is particularly useful if you do not want to install some of the heavier
dependencies like GDAL on your system or want a dedicated and isolated
environment for working with large images.

To use, pull the image and run it by mounting a local volume where the
imagery is stored::

    docker pull ghcr.io/girder/large_image:latest
    docker run -v /path/to/images:/opt/images ghcr.io/girder/large_image:latest


Modules
-------

Large Image consists of several Python modules designed to work together.  These include:

- ``large-image``: The core module.

  You can specify extras_require of the name of any tile source included with this repository.  For instance, you can do ``pip install large-image[tiff]``.  There are additional extras_require options:

  - ``sources``: all of the tile sources in the repository, a specific source name (e.g., ``tiff``)

  - ``memcached``: use memcached for tile caching

  - ``converter``: include the converter module

  - ``colormaps``: use matplotlib for named color palettes used in styles

  - ``tiledoutput``: support for emitting large regions as tiled tiffs

  - ``performance``: include optional modules that can improve performance

  - ``common``: all of the tile sources and above packages that will install directly from pypi without other external libraries on linux, OSX, and Windows.

  - ``all``: for all of the above

- ``large-image-converter``: A utility for using pyvips and other libraries to convert images into pyramidal tiff files that can be read efficiently by large_image.
  You can specify extras_require of ``jp2k`` to include modules to allow output to JPEG2000 compression, ``sources`` to include all sources, ``stats`` to include modules to allow computing compression noise statistics, ``geospatial`` to include support for converting geospatial sources, or ``all`` for all of the optional extras_require.

- Tile sources:

  - ``large-image-source-bioformats``: A tile source for reading any file handled by the Java Bioformats library.

  - ``large-image-source-deepzoom``: A tile source for reading Deepzoom tiles.

  - ``large-image-source-dicom``: A tile source for reading DICOM Whole Slide Images (WSI).

  - ``large-image-source-gdal``: A tile source for reading geotiff files via GDAL.  This handles source data with more complex transforms than the mapnik tile source.

  - ``large-image-source-mapnik``: A tile source for reading geotiff and netcdf files via Mapnik and GDAL.  This handles more vector issues than the gdal tile source.

  - ``large-image-source-multi``: A tile source for compositing other tile sources into a single multi-frame source.

  - ``large-image-source-nd2``: A tile source for reading nd2 (NIS Element) images.

  - ``large-image-source-ometiff``: A tile source using the tiff library that can handle most multi-frame OMETiff files that are compliant with the specification.

  - ``large-image-source-openjpeg``: A tile source using the Glymur library to read jp2 (JPEG 2000) files.

  - ``large-image-source-openslide``: A tile source using the OpenSlide library.  This works with svs, ndpi, Mirax, tiff, vms, and other file formats.

  - ``large-image-source-pil``: A tile source for small images via the Python Imaging Library (Pillow). By default, the maximum size is 4096, but the maximum size can be configured.

  - ``large-image-source-tiff``: A tile source for reading pyramidal tiff files in common compression formats.

  - ``large-image-source-tifffile``: A tile source using the tifffile library that can handle a wide variety of tiff-like files.

  - ``large-image-source-vips``: A tile source for reading any files handled by libvips.  This also can be used for writing tiled images from numpy arrays (up to 4 dimensions).

  - ``large-image-source-zarr``: A tile source using the zarr library that can handle OME-Zarr (OME-NGFF) files as well as some other zarr files. This can also be used for writing N-dimensional tiled images from numpy arrays. Written images can be saved as any supported format.

  - ``large-image-source-test``: A tile source that generates test tiles, including a simple fractal pattern.  Useful for testing extreme zoom levels.

  - ``large-image-source-dummy``: A tile source that does nothing. This is an absolutely minimal implementation of a tile source used for testing. If you want to create a custom tile source, start with this implementation.


As a `Girder`_ plugin, ``large-image`` adds end points to access all of the image formats it can read both to get metadata and to act as a tile server.
In the Girder UI, ``large-image`` shows images on item pages, and can show thumbnails in item lists when browsing folders.
There is also cache management to balance memory use and speed of response in Girder when ``large-image`` is used as a tile server.

Most tile sources can be used with Girder Large Image.  You can specify an extras_require of ``girder`` to install the following packages:

- ``girder-large-image``: Large Image as a Girder 3.x plugin.

  You can install ``large-image[tasks]`` to install a Girder Worker task that can convert otherwise unreadable images to pyramidal tiff files.

- ``girder-large-image-annotation``: Adds models to the Girder database for supporting annotating large images.  These annotations can be rendered on images. Annotations can include polygons, points, image overlays, and other types. Each annotation can have a label and metadata.

- ``large-image-tasks``: A utility for running the converter via Girder Worker.

  You can specify an extras_require of ``girder`` to include modules needed to work with the Girder remote worker or ``worker`` to include modules needed on the remote side of the Girder remote worker.  If neither is specified, some conversion tasks can be run using Girder local jobs.



.. _Girder: https://girder.readthedocs.io/en/latest/
