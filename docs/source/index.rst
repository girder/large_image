.. large_image documentation master file, created by
   sphinx-quickstart on Tue Dec 31 14:43:10 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root ``toctree`` directive.

large_image
===========

large_image is a set of python modules to work with large multiresolution images.  To use, you need the core module ``large-image``, plus one or more tile sources (named ``large-image-source-*``).  Optionally, if you have an image that can't be read by one of the tile sources, the image can be converted using ``large-image-tasks`` and then read with ``large-image-source-tiff``.

large_image also works as a Girder plugin with optional annotation support.

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   tilesource_options
   config_options
   image_conversion
   large_image/modules
   large_image_source_dummy/modules
   large_image_source_gdal/modules
   large_image_source_mapnik/modules
   large_image_source_nd2/modules
   large_image_source_ometiff/modules
   large_image_source_openjpeg/modules
   large_image_source_openslide/modules
   large_image_source_pil/modules
   large_image_source_test/modules
   large_image_source_tiff/modules
   large_image_converter/modules
   large_image_tasks/modules
   girder_large_image/modules
   girder_large_image_annotation/modules


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
