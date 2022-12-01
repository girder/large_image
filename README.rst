Large Image
===========

|build-status| |codecov-io| |license-badge| |doi-badge| |pypi-badge|

.. |build-status| image:: https://img.shields.io/circleci/build/github/girder/large_image.svg
    :target: https://circleci.com/gh/girder/large_image
    :alt: Build Status

.. |license-badge| image:: https://img.shields.io/badge/license-Apache%202-blue.svg
    :target: https://raw.githubusercontent.com/girder/large_image/master/LICENSE
    :alt: License

.. |codecov-io| image:: https://img.shields.io/codecov/c/github/girder/large_image.svg
   :target: https://codecov.io/github/girder/large_image?branch=master
   :alt: codecov.io

.. |doi-badge| image:: https://img.shields.io/badge/DOI-10.5281%2Fzenodo.4723355-blue
   :target: https://zenodo.org/badge/latestdoi/45569214

.. |pypi-badge| image:: https://img.shields.io/pypi/v/large-image.svg?logo=python&logoColor=white
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

In addition to installing the ``large-image`` package, you'll need at least one tile source (a ``large-image-source-xxx`` package).   You can install everything from the main project with one of these commands:

Pip
~~~

Install all tile sources on linux::

    pip install large-image[all] --find-links https://girder.github.io/large_image_wheels

Install all tile sources and all Girder plugins on linux::

    pip install large-image[all] girder-large-image-annotation[tasks] --find-links https://girder.github.io/large_image_wheels


Conda
~~~~~

Conda makes dependency management a bit easier if not on Linux. Some of the source modules are available on conda-forge. You can install the following::

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

  - ``all``: for all of the above

- ``large-image-converter``: A utility for using pyvips and other libraries to convert images into pyramidal tiff files that can be read efficiently by large_image.
  You can specify extras_require of ``jp2k`` to include modules to allow output to JPEG2000 compression, ``sources`` to include all sources, and ``stats`` to include modules to allow computing compression noise statistics.

- Tile sources:

  - ``large-image-source-tiff``: A tile source for reading pyramidal tiff files in common compression formats.

  - ``large-image-source-openslide``: A tile source using the OpenSlide library.  This works with svs, ndpi, Mirax, tiff, vms, and other file formats.

  - ``large-image-source-ometiff``: A tile source using the tiff library that can handle some multi-frame OMETiff files.

  - ``large-image-source-pil``: A tile source for small images via the Python Imaging Library (Pillow).

  - ``large-image-source-gdal``: A tile source for reading geotiff files via GDAL.  This handles source data with more complex transforms than the mapnik tile source.

  - ``large-image-source-mapnik``: A tile source for reading geotiff and netcdf files via Mapnik and GDAL.  This handles more vector issues than the gdal tile source.

  - ``large-image-source-openjpeg``: A tile source using the Glymur library to read jp2 (JPEG 2000) files.

  - ``large-image-source-nd2``: A tile source for reading nd2 (NIS Element) images.

  - ``large-image-source-bioformats``: A tile source for reading any file handled by the Java Bioformats library.

  - ``large-image-source-deepzoom``: A tile source for reading Deepzoom tiles.

  - ``large-image-source-multi``: A tile source for compositing other tile sources into a single multi-frame source.

  - ``large-image-source-vips``: A tile source for reading any files handled by libvips.  This also can be used for writing tiled images from numpy arrays.

  - ``large-image-source-tifffile``: A tile source using the tifffile library that can handle a wide variety of tiff-like files.

  - ``large-image-source-dicom``: A tile source for reading DICOM WSI images.

  - ``large-image-source-test``: A tile source that generates test tiles, including a simple fractal pattern.  Useful for testing extreme zoom levels.

  - ``large-image-source-dummy``: A tile source that does nothing.

  Most tile sources can be used with girder-large-image.  You can specific an extras_require of ``girder`` to include ``girder-large-image`` with the source.

- As a Girder plugin:

  - ``girder-large-image``: Large Image as a Girder_ 3.x plugin.
    You can specify extras_require of ``tasks`` to install a Girder Worker task that can convert otherwise unreadable images to pyramidal tiff files.

  - ``girder-large-image-annotation``: Annotations for large images as a Girder_ 3.x plugin.

  - ``large-image-tasks``: A utility for running the converter via Girder Worker.
    You can specify an extras_require of ``girder`` to include modules needed to work with the Girder remote worker or ``worker`` to include modules needed on the remote side of the Girder remote worker.  If neither is specified, some conversion tasks can be run using Girder local jobs.


Developer Installation
----------------------

To install all packages from source, clone the repository::

    git clone https://github.com/girder/large_image.git
    cd large_image

Install all packages and dependencies::

    pip install -e . -r requirements-dev.txt

If you aren't developing with Girder 3, you can skip installing those components.  Use ``requirements-dev-core.txt`` instead of ``requirements-dev.txt``::

    pip install -e . -r requirements-dev-core.txt


Tile source prerequisites
=========================

Many tile sources have complex prerequisites.  These can be installed directly using your system's package manager or from some prebuilt Python wheels for Linux.  The prebuilt wheels are not official packages, but they can be used by instructing pip to use them by preference::

    pip install -e . -r requirements-dev.txt --find-links https://girder.github.io/large_image_wheels


.. _Girder: https://github.com/girder/girder
