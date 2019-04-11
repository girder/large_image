Large Image |build-status| |codecov-io| |license-badge|
=======================================================

Python modules to work with large multiresolution images.

Large Image consists of several Python modules designed to work together.  These include:

- ``large_image``: The core module.
  You can specify extras_require of the name of any tile source included with this repository, ``sources`` for all of the tile sources in the repository, ``memcached`` for using memcached for tile caching, or ``all`` for all of the tile sources and memcached.

- ``girder_large_image``: Large Image as a Girder_ 3.x plugin.
  You can specify extras_require of ``tasks`` to install a Girder Worker task that can convert otherwise unreadable images to pyramidal tiff files.

- ``girder_large_image_annotation``: Annotations for large images as a Girder_ 3.x plugin.

- ``large_image_tasks``: A utility for using pyvips to convert images into pyramidal tiff files that can be read efficiently by large_image.  This can be used by itself or with Girder Worker.

- Tile sources:

  - ``large-image-source-tiff``: A tile source for reading pyramidal tiff files in common compression formats.

  - ``large-image-source-openslide``: A tile source using the OpenSlide library.  This works with svs, ndpi, Mirax, tiff, vms, and other file formats.

  - ``large-image-source-pil``: A tile source for small images via the Python Imaging Library (Pillow).

  - ``large-image-source-mapnik``: A tile source for reading geotiff and netcdf files via Mapnik and GDAL.

  - ``large-image-source-test``: A tile source that generates test tiles, including a simple fractal pattern.  Useful for testing extreme zoom levels.

  - ``large-image-source-dummy``: A tile source that does nothing.

  Most tile sources can be used with girder_large_image.


Installation
------------

To install all packages from source, clone

1.  ``git clone https://github.com/girder/large_image.git``

2.  Install all packages and dependencies:

    ``pip install -e large_image[memcached] -r requirements-dev.txt``


Tile source prerequisites
=========================

Many tile sources have complex prerequisites.  These can be installed directly using your system's package manager or from some prebuilt Python wheels for Linux.  The prebuilt wheels are not official packages, but they can be used by instructing pip to use them by preference:

    ``pip install -e large_image[memcached] -r requirements-dev.txt --find-links https://manthey.github.io/large_image_wheels``


.. _Girder: https://github.com/girder/girder

.. |build-status| image:: https://travis-ci.org/girder/large_image.svg?branch=master
    :target: https://travis-ci.org/girder/large_image
    :alt: Build Status

.. |license-badge| image:: https://img.shields.io/badge/license-Apache%202-blue.svg
    :target: https://raw.githubusercontent.com/girder/large_image/master/LICENSE
    :alt: License

.. |codecov-io| image:: https://codecov.io/github/girder/large_image/coverage.svg?branch=master
   :target: https://codecov.io/github/girder/large_image?branch=master
   :alt: codecov.io
