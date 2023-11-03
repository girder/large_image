Caching in Large Image
======================

There are two main caches in large_image in addition to caching done on the operating system level.  These are:

- Tile Cache: The tile cache stores individual images and/or numpy arrays for each tile processed.

  - May be stored in the python process memory or memcached.  Other cache backends can also be added.
  - The cache key is a hash that includes the tile source, tile location within the source, format and compression, and style.
  - If memcached is used, cached tiles can be shared across multiple processes.
  - Tiles are often bigger than what memcached was optimized for, so memcached needs to be set to allow larger values.
  - Cached tiles can include original as-read data as well as styled or transformed data.  Tiles can be synthesized for sources that are missing specific resolutions; these are also cached.
  - If using memcached, memcached determines how much memory is used (and what machine it is stored on).  If using the python process, memory is limited to a fraction of total memory as reported by psutils.

- Tile Source Cache: The source cache stores file handles, parsed metadata, and other values to optimize reading a specific large image.

  - Always stored in the python process memory (not shared between processes).
  - Memory use is wildly different depending on tile source; an estimate is based on sample files and then the maximum number of sources that should be tiled is based on a frame of total memory as reported by psutils and this estimate.
  - The cache key includes the tile source, default tile format, and style.
  - File handles and other metadata are shared if sources only differ in style (for example if ICC color correction is applied in one and not in another).
  - Because file handles are shared across sources that only differ in style, if a source implements a custom ``__del__`` operator, it needs to check if it is the unstyled source.

Caching in Large Image in Girder
--------------------------------

Tile sources are opened: when large image files uploaded or imported; when large image files are viewed; when thumbnails are generated; when an item page with a large image is viewd; and from some API calls.  All of these result in the source being placed in the cache _except_ import.

Since there are multiple users, the cache size should be large enough that no user has an image that they are actively viewing fall out of cache.

Example of cache use when the ``GET`` ``/item/{id}/tile/zxy/{z}/{x}/{y}?style=<style>&encoding=<encoding>&...`` endpoint is called:

.. mermaid::

  graph TD;
    apicall(["GET /item/{id}/tile/zxy/{z}/{x}/{y}?style=&lt;style&gt;&amp;encoding=&lt;encoding&gt;&amp;..."])
    checktile1{Is tile in\ntile cache?}
    apicall --> checktile1;
    getfile[("Get file-like object\nor url from Girder")]
    checktile1 -- No --> getfile;
    servetile(["Serve tile 🖼️"])
    checktile1 -- Yes --> servetile;
    checksource{"Is file-like object\nin source cache\nwith {style}\nand {encoding}?"}
    getfile --> checksource;
    checkunstyled{"Is unstyled file\nin source cache\nwith {encoding}?"}
    checksource -- No --> checkunstyled;
    openunstyle["Open unstyled file with {encoding}"]
    checkunstyled -- No --> openunstyle;
    putunstyledsource[/"Put unstyled source in cache"/]
    openunstyle --> putunstyledsource;
    alter["Copy unstyled source\nand alter for {style}"]
    putunstyledsource --> alter;
    checkunstyled -- Yes --> alter;
    putsource[/"Put styled source in cache"/]
    alter --> putsource;
    checktile2{"Is unstyled tile\n{x}, {y}, {z},\n{frame}, {encoding}\nin tile cache?"}
    putsource --> checktile2;
    checksource -- Yes --> checktile2;
    checktile3{"Does tile exist\nin the file?"}
    checktile2 -- No --> checktile3;
    maketile[["Synthesize tile\nfrom higher\nresolution tiles"]]
    checktile3 -- No --> maketile;
    readfile[("Read tile from file")]
    checktile3 -- Yes --> readfile;
    puttile1[/"Put unstyled\ntile in cache"/]
    maketile --> puttile1;
    readfile --> puttile1;
    gettile[\"Read unstyled tile\nfrom cache"\]
    checktile2 -- Yes --> gettile;
    needstyle{"Is {style}\nrequired?"}
    puttile1 --> needstyle;
    gettile --> needstyle;
    checkencoding{"Is tile\nin {encoding}?"}
    needstyle -- No --> checkencoding;
    isnumpy{"Is unstyled\ntile a\nnumpy array?"}
    needstyle -- Yes --> isnumpy;
    makenumpy["Convert tile to numpy"]
    isnumpy -- No --> makenumpy;
    makestyle["Generate styled tile in numpy format\n(Note that this could fetch other tiles)"]
    isnumpy -- Yes --> makestyle;
    makenumpy --> makestyle;
    makestyle --> checkencoding;
    encode["Encode tile to {encoding}"]
    checkencoding -- No --> encode;
    puttile2[/"Put encoded tile\nin cache"/]
    encode --> puttile2;
    checkencoding -- Yes --> puttile2;
    puttile2 --> servetile;
