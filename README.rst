Large Image |build-status| |codecov-io| |license-badge|
=======================================================

As a Girder_ Plugin
-------------------

A Girder plugin to create, serve, and display large multiresolution images.

Upload image files to Girder.  If they are not already in a tiled-format, they can be converted to tiled images.  The plugin has a variety of viewers to examine the images.


As a stand-alone Python module
------------------------------

A Python module to work with large multiresolution images.

Installation
++++++++++++

1.  `Install OpenSlide <http://openslide.org/download/>`_

    If you are using Ubuntu 14.04, there is a known bug in OpenJPEG that will prevent OpenSlide from reading certain files.  This requires building OpenJPEG, libtiff, and OpenSlide from source to work around the problem.  For more information, there is an `ansible script <https://github.com/DigitalSlideArchive/HistomicsTK/blob/master/ansible/roles/openslide/tasks/main.yml>`_ that builds these libraries, and some `notes on the process <https://github.com/DigitalSlideArchive/digital_slide_archive/wiki/VIPS-and-OpenSlide-Installation>`_.

    You may want to install optional utilities:

    * memcached - this allows memcached to be used for caching

2.  pip install --user numpy==1.10.2

    The python libtiff library fails to include numpy as a dependency, which means that it must be installed manually before you can install large_image.

    You may want to pip install optional modules:

    * psutil - this helps determine how much memory is available for caching

3.  git clone https://github.com/girder/large_image.git

4.  cd large_image

5.  python setup.py install --user

Examples
++++++++

*   `Finding the average color of an image <examples/average_color.py>`_

    This opens a tiled image and computes the average color at a specified magnification.


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
