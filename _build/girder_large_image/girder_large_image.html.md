# girder_large_image package

## Subpackages

* [girder_large_image.models package](girder_large_image.models.md)
  * [Submodules](girder_large_image.models.md#submodules)
  * [girder_large_image.models.image_item module](girder_large_image.models.md#module-girder_large_image.models.image_item)
    * [`ImageItem`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem)
      * [`ImageItem.cacheSaveDataManagement()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.cacheSaveDataManagement)
      * [`ImageItem.checkForDocumentDB()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.checkForDocumentDB)
      * [`ImageItem.convertImage()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.convertImage)
      * [`ImageItem.createImageItem()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.createImageItem)
      * [`ImageItem.delete()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.delete)
      * [`ImageItem.getAndCacheImageOrDataRun()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getAndCacheImageOrDataRun)
      * [`ImageItem.getAssociatedImage()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getAssociatedImage)
      * [`ImageItem.getAssociatedImagesList()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getAssociatedImagesList)
      * [`ImageItem.getBandInformation()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getBandInformation)
      * [`ImageItem.getInternalMetadata()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getInternalMetadata)
      * [`ImageItem.getMetadata()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getMetadata)
      * [`ImageItem.getPixel()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getPixel)
      * [`ImageItem.getRegion()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getRegion)
      * [`ImageItem.getThumbnail()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getThumbnail)
      * [`ImageItem.getTile()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.getTile)
      * [`ImageItem.histogram()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.histogram)
      * [`ImageItem.initialize()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.initialize)
      * [`ImageItem.mayHaveAdjacentFiles()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.mayHaveAdjacentFiles)
      * [`ImageItem.removeThumbnailFiles()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.removeThumbnailFiles)
      * [`ImageItem.tileFrames()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.tileFrames)
      * [`ImageItem.tileSource()`](girder_large_image.models.md#girder_large_image.models.image_item.ImageItem.tileSource)
  * [Module contents](girder_large_image.models.md#module-girder_large_image.models)
* [girder_large_image.rest package](girder_large_image.rest.md)
  * [Submodules](girder_large_image.rest.md#submodules)
  * [girder_large_image.rest.item_meta module](girder_large_image.rest.md#module-girder_large_image.rest.item_meta)
    * [`InternalMetadataItemResource`](girder_large_image.rest.md#girder_large_image.rest.item_meta.InternalMetadataItemResource)
      * [`InternalMetadataItemResource.deleteMetadataKey()`](girder_large_image.rest.md#girder_large_image.rest.item_meta.InternalMetadataItemResource.deleteMetadataKey)
      * [`InternalMetadataItemResource.getMetadataKey()`](girder_large_image.rest.md#girder_large_image.rest.item_meta.InternalMetadataItemResource.getMetadataKey)
      * [`InternalMetadataItemResource.updateMetadataKey()`](girder_large_image.rest.md#girder_large_image.rest.item_meta.InternalMetadataItemResource.updateMetadataKey)
  * [girder_large_image.rest.large_image_resource module](girder_large_image.rest.md#module-girder_large_image.rest.large_image_resource)
    * [`LargeImageResource`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource)
      * [`LargeImageResource.cacheClear()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.cacheClear)
      * [`LargeImageResource.cacheInfo()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.cacheInfo)
      * [`LargeImageResource.configFormat()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.configFormat)
      * [`LargeImageResource.configReplace()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.configReplace)
      * [`LargeImageResource.configValidate()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.configValidate)
      * [`LargeImageResource.countAssociatedImages()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.countAssociatedImages)
      * [`LargeImageResource.countHistograms()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.countHistograms)
      * [`LargeImageResource.countThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.countThumbnails)
      * [`LargeImageResource.createLargeImages()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.createLargeImages)
      * [`LargeImageResource.createThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.createThumbnails)
      * [`LargeImageResource.deleteAssociatedImages()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.deleteAssociatedImages)
      * [`LargeImageResource.deleteHistograms()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.deleteHistograms)
      * [`LargeImageResource.deleteIncompleteTiles()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.deleteIncompleteTiles)
      * [`LargeImageResource.deleteThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.deleteThumbnails)
      * [`LargeImageResource.getPublicSettings()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.getPublicSettings)
      * [`LargeImageResource.listSources()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.LargeImageResource.listSources)
    * [`createThumbnailsJob()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.createThumbnailsJob)
    * [`createThumbnailsJobLog()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.createThumbnailsJobLog)
    * [`createThumbnailsJobTask()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.createThumbnailsJobTask)
    * [`createThumbnailsJobThread()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.createThumbnailsJobThread)
    * [`cursorNextOrNone()`](girder_large_image.rest.md#girder_large_image.rest.large_image_resource.cursorNextOrNone)
  * [girder_large_image.rest.tiles module](girder_large_image.rest.md#module-girder_large_image.rest.tiles)
    * [`TilesItemResource`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource)
      * [`TilesItemResource.addTilesThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.addTilesThumbnails)
      * [`TilesItemResource.convertImage()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.convertImage)
      * [`TilesItemResource.createTiles()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.createTiles)
      * [`TilesItemResource.deleteTiles()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.deleteTiles)
      * [`TilesItemResource.deleteTilesThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.deleteTilesThumbnails)
      * [`TilesItemResource.getAssociatedImage()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getAssociatedImage)
      * [`TilesItemResource.getAssociatedImageMetadata()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getAssociatedImageMetadata)
      * [`TilesItemResource.getAssociatedImagesList()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getAssociatedImagesList)
      * [`TilesItemResource.getBandInformation()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getBandInformation)
      * [`TilesItemResource.getDZIInfo()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getDZIInfo)
      * [`TilesItemResource.getDZITile()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getDZITile)
      * [`TilesItemResource.getHistogram()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getHistogram)
      * [`TilesItemResource.getInternalMetadata()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getInternalMetadata)
      * [`TilesItemResource.getTestTile()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTestTile)
      * [`TilesItemResource.getTestTilesInfo()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTestTilesInfo)
      * [`TilesItemResource.getTile()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTile)
      * [`TilesItemResource.getTileWithFrame()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTileWithFrame)
      * [`TilesItemResource.getTilesInfo()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTilesInfo)
      * [`TilesItemResource.getTilesPixel()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTilesPixel)
      * [`TilesItemResource.getTilesRegion()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTilesRegion)
      * [`TilesItemResource.getTilesThumbnail()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.getTilesThumbnail)
      * [`TilesItemResource.listTilesThumbnails()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.listTilesThumbnails)
      * [`TilesItemResource.tileFrames()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.tileFrames)
      * [`TilesItemResource.tileFramesQuadInfo()`](girder_large_image.rest.md#girder_large_image.rest.tiles.TilesItemResource.tileFramesQuadInfo)
  * [Module contents](girder_large_image.rest.md#module-girder_large_image.rest)
    * [`addSystemEndpoints()`](girder_large_image.rest.md#girder_large_image.rest.addSystemEndpoints)
    * [`getYAMLConfigFile()`](girder_large_image.rest.md#girder_large_image.rest.getYAMLConfigFile)
    * [`putYAMLConfigFile()`](girder_large_image.rest.md#girder_large_image.rest.putYAMLConfigFile)

## Submodules

## girder_large_image.constants module

### *class* girder_large_image.constants.PluginSettings

Bases: `object`

#### LARGE_IMAGE_AUTO_SET *= 'large_image.auto_set'*

#### LARGE_IMAGE_CONFIG_FOLDER *= 'large_image.config_folder'*

#### LARGE_IMAGE_DEFAULT_VIEWER *= 'large_image.default_viewer'*

#### LARGE_IMAGE_ICC_CORRECTION *= 'large_image.icc_correction'*

#### LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE *= 'large_image.max_small_image_size'*

#### LARGE_IMAGE_MAX_THUMBNAIL_FILES *= 'large_image.max_thumbnail_files'*

#### LARGE_IMAGE_MERGE_DICOM *= 'large_image.merge_dicom'*

#### LARGE_IMAGE_NOTIFICATION_STREAM_FALLBACK *= 'large_image.notification_stream_fallback'*

#### LARGE_IMAGE_SHOW_EXTRA *= 'large_image.show_extra'*

#### LARGE_IMAGE_SHOW_EXTRA_ADMIN *= 'large_image.show_extra_admin'*

#### LARGE_IMAGE_SHOW_EXTRA_PUBLIC *= 'large_image.show_extra_public'*

#### LARGE_IMAGE_SHOW_ITEM_EXTRA *= 'large_image.show_item_extra'*

#### LARGE_IMAGE_SHOW_ITEM_EXTRA_ADMIN *= 'large_image.show_item_extra_admin'*

#### LARGE_IMAGE_SHOW_ITEM_EXTRA_PUBLIC *= 'large_image.show_item_extra_public'*

#### LARGE_IMAGE_SHOW_THUMBNAILS *= 'large_image.show_thumbnails'*

#### LARGE_IMAGE_SHOW_VIEWER *= 'large_image.show_viewer'*

## girder_large_image.girder_tilesource module

### *class* girder_large_image.girder_tilesource.GirderTileSource(item, \*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **item** – a Girder item document which contains
  [‘largeImage’][‘fileId’] identifying the Girder file to be used
  for the tile source.

#### extensionsWithAdjacentFiles *= {}*

#### *static* getLRUHash(\*args, \*\*kwargs)

Return a string hash used as a key in the recently-used cache for tile
sources.

* **Returns:**
  a string hash value.

#### getState()

Return a string reflecting the state of the tile source.  This is used
as part of a cache key when hashing function return values.

* **Returns:**
  a string hash value of the source state.

#### girderSource *= True*

#### mayHaveAdjacentFiles(largeImageFile)

#### mimeTypesWithAdjacentFiles *= {}*

### girder_large_image.girder_tilesource.getGirderTileSource(item, file=None, \*args, \*\*kwargs)

Get a Girder tilesource using the known sources.

* **Parameters:**
  * **item** – a Girder item or an item id.
  * **file** – if specified, the Girder file object to use as the large image
    file; used here only to check extensions.
* **Returns:**
  A girder tilesource for the item.

### girder_large_image.girder_tilesource.getGirderTileSourceName(item, file=None, \*args, \*\*kwargs)

Get a Girder tilesource name using the known sources.  If tile sources have
not yet been loaded, load them.

* **Parameters:**
  * **item** – a Girder item.
  * **file** – if specified, the Girder file object to use as the large image
    file; used here only to check extensions.
* **Returns:**
  The name of a tilesource that can read the Girder item.

### girder_large_image.girder_tilesource.loadGirderTileSources()

Load all Girder tilesources from entrypoints and add them to the
AvailableGiderTileSources dictionary.

## girder_large_image.loadmodelcache module

### girder_large_image.loadmodelcache.invalidateLoadModelCache(\*args, \*\*kwargs)

Empty the LoadModelCache.

### girder_large_image.loadmodelcache.loadModel(resource, model, plugin='_core', id=None, allowCookie=False, level=None)

Load a model based on id using the current cherrypy token parameter for
authentication, caching the results.  This must be called in a cherrypy
context.

* **Parameters:**
  * **resource** – the resource class instance calling the function.  Used
    for access to the current user and model importer.
  * **model** – the model name, e.g., ‘item’.
  * **plugin** – the plugin name when loading a plugin model.
  * **id** – a string id of the model to load.
  * **allowCookie** – true if the cookie authentication method is allowed.
  * **level** – access level desired.
* **Returns:**
  the loaded model.

## Module contents

### *class* girder_large_image.LargeImagePlugin(entrypoint)

Bases: `GirderPlugin`

#### CLIENT_SOURCE_PATH *= 'web_client'*

The path of the plugin’s web client source code.  This path is given relative to the python
package.  This property is used to link the web client source into the staging area while
building in development mode.  When this value is None it indicates there is no web client
component.

#### DISPLAY_NAME *= 'Large Image'*

This is the named displayed to users on the plugin page.  Unlike the entrypoint name
used internally, this name can be an arbitrary string.

#### load(info)

### girder_large_image.addSettingsToConfig(config, user, name=None)

Add the settings for showing thumbnails and images in item lists to a
config file if the itemList or itemListDialog options are not set.

* **Parameters:**
  * **config** – the config dictionary to modify.
  * **user** – the current user.
  * **name** – the name of the config file.

### girder_large_image.adjustConfigForUser(config, user)

Given the current user, adjust the config so that only relevant and
combined values are used.  If the root of the config dictionary contains
“access”: {“user”: <dict>, “admin”: <dict>}, the base values are updated
based on the user’s access level.  If the root of the config contains
“group”: {<group-name>: <dict>, …}, the base values are updated for
every group the user is a part of.

The order of update is groups in C-sort alphabetical order followed by
access/user and then access/admin as they apply.

* **Parameters:**
  **config** – a config dictionary.

### girder_large_image.checkForLargeImageFiles(event)

### girder_large_image.checkForMergeDicom(item)

### girder_large_image.handleCopyItem(event)

When copying an item, finish adjusting the largeImage fileId reference to
the copied file.

### girder_large_image.handleFileSave(event)

When a file is first saved, mark its mime type based on its extension if we
would otherwise just mark it as generic application/octet-stream.

### girder_large_image.handleRemoveFile(event)

When a file is removed, check if it is a largeImage fileId.  If so, delete
the largeImage record.

### girder_large_image.handleSettingSave(event)

When certain settings are changed, clear the caches.

### girder_large_image.metadataSearchHandler(query, types, user=None, level=None, limit=0, offset=0, models=None, searchModels=None, metakey='meta')

Provide a substring search on metadata.

### girder_large_image.patchMount()

### girder_large_image.prepareCopyItem(event)

When copying an item, adjust the largeImage fileId reference so it can be
matched to the to-be-copied file.

### girder_large_image.removeThumbnails(event)

### girder_large_image.unbindGirderEventsByHandlerName(handlerName)

### girder_large_image.validateBoolean(doc)

### girder_large_image.validateBooleanOrAll(doc)

### girder_large_image.validateBooleanOrICCIntent(doc)

### girder_large_image.validateDefaultViewer(doc)

### girder_large_image.validateDictOrJSON(doc)

### girder_large_image.validateFolder(doc)

### girder_large_image.validateNonnegativeInteger(doc)

### girder_large_image.yamlConfigFile(folder, name, user)

Get a resolved named config file based on a folder and user.

* **Parameters:**
  * **folder** – a Girder folder model.
  * **name** – the name of the config file.
  * **user** – the user that the response if adjusted for.
* **Returns:**
  either None if no config file, or a yaml record.

### girder_large_image.yamlConfigFileWrite(folder, name, user, yaml_config, user_context)

If the user has appropriate permissions, create or modify an item in the
specified folder with the specified name, storing the config value as a
file.

* **Parameters:**
  * **folder** – a Girder folder model.
  * **name** – the name of the config file.
  * **user** – the user that the response if adjusted for.
  * **yaml_config** – a yaml config string.
  * **user_context** – whether these settings should only apply to the current user.
