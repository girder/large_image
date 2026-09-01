# girder_large_image.rest package

## Submodules

## girder_large_image.rest.item_meta module

### *class* girder_large_image.rest.item_meta.InternalMetadataItemResource(apiRoot)

Bases: `Item`

#### deleteMetadataKey(item, key, params)

#### getMetadataKey(item, key, params)

#### updateMetadataKey(item, key, params)

## girder_large_image.rest.large_image_resource module

### *class* girder_large_image.rest.large_image_resource.LargeImageResource

Bases: `Resource`

#### cacheClear(params)

#### cacheInfo(params)

#### configFormat(config)

#### configReplace(config, restart)

#### configValidate(config)

#### countAssociatedImages(params)

#### countHistograms(params)

#### countThumbnails(params)

#### createLargeImages(folder, createJobs, localJobs, recurse, cancelJobs, redoExisting)

#### createThumbnails(params)

#### deleteAssociatedImages(params)

#### deleteHistograms(params)

#### deleteIncompleteTiles(params)

#### deleteThumbnails(params)

#### getPublicSettings(params)

#### listSources(params)

### girder_large_image.rest.large_image_resource.createThumbnailsJob(job)

### girder_large_image.rest.large_image_resource.createThumbnailsJobLog(job, info, prefix='', status=None)

Log information about the create thumbnails job.

* **Parameters:**
  * **job** – the job object.
  * **info** – a dictionary with the number of thumbnails checked, created,
    and failed.
  * **prefix** – a string to place in front of the log message.
  * **status** – if not None, a new status for the job.

### girder_large_image.rest.large_image_resource.createThumbnailsJobTask(item, spec)

For an individual item, check or create all of the appropriate thumbnails.

* **Parameters:**
  * **item** – the image item.
  * **spec** – a list of thumbnail specifications.
* **Returns:**
  a dictionary with the total status of the thumbnail job.

### girder_large_image.rest.large_image_resource.createThumbnailsJobThread(job)

Create thumbnails for all of the large image items.

The job object contains:

```default
- spec: an array, each entry of which is the parameter dictionary
  for the model getThumbnail function.
- logInterval: the time in seconds between log messages.  This
  also controls the granularity of cancelling the job.
- concurrent: the number of threads to use.  0 for the number of
  cpus.
```

* **Parameters:**
  **job** – the job object including kwargs.

### girder_large_image.rest.large_image_resource.cursorNextOrNone(cursor)

Given a Mongo cursor, return the next value if there is one.  If not,
return None.

* **Parameters:**
  **cursor** – a cursor to get a value from.
* **Returns:**
  the next value or None.

## girder_large_image.rest.tiles module

### *class* girder_large_image.rest.tiles.TilesItemResource(apiRoot)

Bases: `Item`

#### addTilesThumbnails(item, key, mimeType, thumbnail=False, data=None)

#### convertImage(item, params)

#### createTiles(item, params)

#### deleteTiles(item, params)

#### deleteTilesThumbnails(item, keep, key=None, thumbnail=True)

#### getAssociatedImage(itemId, image, params)

#### getAssociatedImageMetadata(item, image, params)

#### getAssociatedImagesList(item, params)

#### getBandInformation(item, params)

#### getDZIInfo(item, params)

#### getDZITile(item, level, xandy, params)

#### getHistogram(item, params)

#### getInternalMetadata(item, params)

#### getTestTile(z, x, y, params)

#### getTestTilesInfo(params)

#### getTile(itemId, z, x, y, params)

#### getTileWithFrame(itemId, frame, z, x, y, params)

#### getTilesInfo(item, params)

#### getTilesPixel(item, params)

#### getTilesRegion(item, params)

#### getTilesThumbnail(item, params)

#### listTilesThumbnails(item)

#### tileFrames(item, params)

#### tileFramesQuadInfo(item, params)

## Module contents

### girder_large_image.rest.addSystemEndpoints(apiRoot)

This adds endpoints to routes that already exist in Girder.

* **Parameters:**
  **apiRoot** – Girder api root class.

### girder_large_image.rest.getYAMLConfigFile(self, folder, name)

### girder_large_image.rest.putYAMLConfigFile(self, folder, name, config, user_context)
