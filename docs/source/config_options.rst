Configuration Options
=====================

Some functionality of large_image is controlled through configuration parameters.  These can be read or set via python using functions in the ``large_image.config`` module, `getConfig <./large_image/large_image.html#large_image.config.getConfig>`_ and `setConfig <./large_image/large_image.html#large_image.config.setConfig>`_.

Configuration parameters:

- ``logger``: a Python logger.  Most log messages are sent here.

- ``logprint``: a Python logger.  Messages about available tilesources are sent here.

- ``cache_backend``: either ``python`` (the default) or ``memcached``, specifying where tiles are cached.  If memcached is not available for any reason, the python cache is used instead.

- ``cache_python_memory_portion``: If tiles are cached in python, the cache is sized so that it is expected to use less than 1 / (``cache_python_memory_portion``) of the available memory.  This is an integer.

- ``cache_memcached_url``: If tiles are cached in memcached, the url or list of urls where the memcached server is located.  Default '127.0.0.1'.

- ``cache_memcached_username``: A username for the memcached server.  Default ``None``.

- ``cache_memcached_password``: A password for the memcached server.  Default ``None``.

- ``cache_tilesource_memory_portion``: Tilesources are cached on open so that subsequent accesses can be faster.  These use file handles and memory.  This limits the maximum based on a memory estimation and using no more than 1 / (``cache_tilesource_memory_portion``) of the available memory.

- ``cache_tilesource_maximum``: If this is non-zero, this further limits the number of tilesources than can be cached to this value.

- ``max_small_image_size``: The PIL tilesource is used for small images if they are no more than this many pixels along their maximum dimension.

- ``source_bioformats_ignored_extensions``: The bioformats tilesource can read some files that are better read by other tilesources or ignored.  Since reading these files is suboptimal, by default files with particular extensions are ignored by the bioformats tilesource.  This defaults to ``.jpg,.jpeg,.jpe,.png,.tif,.tiff``.


Configuration within the Girder Plugin
--------------------------------------

For the Girder plugin, these can also be set in the ``girder.cfg`` file in a ``large_image`` section.  For example::

  [large_image]
  # cache_backend, used for caching tiles, is either "memcached" or "python"
  cache_backend = "python"
  # 'python' cache can use 1/(val) of the available memory
  cache_python_memory_portion = 32
  # 'memcached' cache backend can specify the memcached server.
  # cache_memcached_url may be a list
  cache_memcached_url = "127.0.0.1"
  cache_memcached_username = None
  cache_memcached_password = None
  # The tilesource cache uses the lesser of a value based on available file
  # handles, the memory portion, and the maximum (if not 0)
  cache_tilesource_memory_portion = 8
  cache_tilesource_maximum = 0
  # The PIL tilesource won't read images larger than the max small images size
  max_small_image_size = 4096
  # The bioformats tilesource won't read files that end in a comma-separated
  # list of extensions
  source_bioformats_ignored_extensions = '.jpg,.jpeg,.jpe,.png,.tif,.tiff'
