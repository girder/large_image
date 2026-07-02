# girder_large_image.models package

## Submodules

## girder_large_image.models.image_item module

### *class* girder_large_image.models.image_item.ImageItem(\*args, \*\*kwargs)

Bases: `Item`

#### cacheSaveDataManagement(timeout=0.0)

Check any of the threads used for caching data from slow functions and
join those that are finished.

* **Parameters:**
  **timeout** – 0 to return without blocking, just harvesting the
  finished threads.  None to block until all are finished.  Since all
  threads will be checked, specifying a positive timeout will
  possibly take that long times the number of threads.
* **Returns:**
  the number of active threads

#### checkForDocumentDB()

#### convertImage(item, fileObj, user=None, token=None, localJob=True, \*\*kwargs)

#### createImageItem(item, fileObj, user=None, token=None, createJob=True, notify=False, localJob=None, \*\*kwargs)

#### delete(item, skipFileIds=None)

#### getAndCacheImageOrDataRun(checkAndCreate, imageFunc, item, key, keydict, pickleCache, lockkey, \*\*kwargs)

Actually execute a cached function.

#### getAssociatedImage(item, imageKey, checkAndCreate=False, \*args, \*\*kwargs)

Return an associated image.

* **Parameters:**
  * **item** – the item with the tile source.
  * **imageKey** – the key of the associated image to retrieve.
  * **kwargs** – optional arguments.  Some options are width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.
* **Returns:**
  imageData, imageMime: the image data and the mime type, or
  None if the associated image doesn’t exist.

#### getAssociatedImagesList(item, \*\*kwargs)

Return a list of associated images.

* **Parameters:**
  **item** – the item with the tile source.
* **Returns:**
  a list of keys of associated images.

#### getBandInformation(item, statistics=True, \*\*kwargs)

Using a tile source, get band information of the image.

* **Parameters:**
  * **item** – the item with the tile source.
  * **kwargs** – optional arguments.  See the tilesource
    getBandInformation method.
* **Returns:**
  band information.

#### getInternalMetadata(item, \*\*kwargs)

#### getMetadata(item, \*\*kwargs)

#### getPixel(item, \*\*kwargs)

Using a tile source, get a single pixel from the image.

* **Parameters:**
  * **item** – the item with the tile source.
  * **kwargs** – optional arguments.  Some options are left, top.
* **Returns:**
  a dictionary of the color channel values, possibly with
  additional information

#### getRegion(item, \*\*kwargs)

Using a tile source, get an arbitrary region of the image, optionally
scaling the results.  Aspect ratio is preserved.

* **Parameters:**
  * **item** – the item with the tile source.
  * **kwargs** – optional arguments.  Some options are left, top,
    right, bottom, regionWidth, regionHeight, units, width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.  This
    is also passed to the tile source.
* **Returns:**
  regionData, regionMime: the image data and the mime type.

#### getThumbnail(item, checkAndCreate=False, width=None, height=None, \*\*kwargs)

Using a tile source, get a basic thumbnail.  Aspect ratio is
preserved.  If neither width nor height is given, a default value is
used.  If both are given, the thumbnail will be no larger than either
size.

* **Parameters:**
  * **item** – the item with the tile source.
  * **checkAndCreate** – if the thumbnail is already cached, just return
    True.  If it does not, create, cache, and return it.  If ‘nosave’,
    return values from the cache, but do not store new results in the
    cache.
  * **width** – maximum width in pixels.
  * **height** – maximum height in pixels.
  * **kwargs** – optional arguments.  Some options are encoding,
    jpegQuality, jpegSubsampling, tiffCompression, fill.  This is also
    passed to the tile source.
* **Returns:**
  thumbData, thumbMime: the image data and the mime type OR
  a generator which will yield a file.

#### getTile(item, x, y, z, mayRedirect=False, \*\*kwargs)

#### histogram(item, checkAndCreate=False, \*\*kwargs)

Using a tile source, get a histogram of the image.

* **Parameters:**
  * **item** – the item with the tile source.
  * **kwargs** – optional arguments.  See the tilesource histogram
    method.
* **Returns:**
  histogram object.

#### initialize()

Subclasses should override this and set the name of the collection as
self.name. Also, they should set any indexed fields that they require.

#### mayHaveAdjacentFiles(item, imageFile=None)

Check if an item may have adajent files.

* **Parameters:**
  * **item** – the item to check.
  * **imageFile** – the largeImage file; if not passed, it is looked up,
    passing it just saves a database lookup.
* **Returns:**
  None if this isn’t a largeImage, False if we think it can’t
  have adjacent files, ‘local’ if we think the adjacent files are
  local to the item, True if there could be adjacent files in other
  items.

#### removeThumbnailFiles(item, keep=0, sort=None, imageKey=None, onlyList=False, \*\*kwargs)

Remove all large image thumbnails from an item.

* **Parameters:**
  * **item** – the item that owns the thumbnails.
  * **keep** – keep this many entries.
  * **sort** – the sort method used.  The first (keep) records in this
    sort order are kept.
  * **imageKey** – None for the basic thumbnail, otherwise an associated
    imageKey.
  * **onlyList** – if True, return a list of known thumbnails or data
    files that would be removed, but don’t remove them.
  * **kwargs** – additional parameters to determine which files to
    remove.
* **Returns:**
  a tuple of (the number of files before removal, the number of
  files removed).

#### tileFrames(item, checkAndCreate='nosave', \*\*kwargs)

Given the parameters for getRegion, plus a list of frames and the
number of frames across, make a larger image composed of a region from
each listed frame composited together.

* **Parameters:**
  * **item** – the item with the tile source.
  * **checkAndCreate** – if False, use the cache.  If True and the result
    is already cached, just return True.  If is not, create, cache, and
    return it.  If ‘nosave’, return values from the cache, but do not
    store new results in the cache.
  * **kwargs** – optional arguments.  Some options are left, top,
    right, bottom, regionWidth, regionHeight, units, width, height,
    encoding, jpegQuality, jpegSubsampling, and tiffCompression.  This
    is also passed to the tile source.  These also include frameList
    and framesAcross.
* **Returns:**
  regionData, regionMime: the image data and the mime type.

#### tileSource(item, \*\*kwargs)

Get a tile source for an item.

* **Parameters:**
  **item** – the item with the tile source.
* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

## Module contents
