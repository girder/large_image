# large_image package

## Subpackages

* [large_image.cache_util package](large_image.cache_util.md)
  * [Submodules](large_image.cache_util.md#submodules)
  * [large_image.cache_util.base module](large_image.cache_util.md#module-large_image.cache_util.base)
    * [`BaseCache`](large_image.cache_util.md#large_image.cache_util.base.BaseCache)
      * [`BaseCache.clear()`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.clear)
      * [`BaseCache.curritems`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.curritems)
      * [`BaseCache.currsize`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.currsize)
      * [`BaseCache.getCache()`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.getCache)
      * [`BaseCache.logError()`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.logError)
      * [`BaseCache.maxsize`](large_image.cache_util.md#large_image.cache_util.base.BaseCache.maxsize)
  * [large_image.cache_util.cache module](large_image.cache_util.md#module-large_image.cache_util.cache)
    * [`LruCacheMetaclass`](large_image.cache_util.md#large_image.cache_util.cache.LruCacheMetaclass)
      * [`LruCacheMetaclass.classCaches`](large_image.cache_util.md#large_image.cache_util.cache.LruCacheMetaclass.classCaches)
      * [`LruCacheMetaclass.namedCaches`](large_image.cache_util.md#large_image.cache_util.cache.LruCacheMetaclass.namedCaches)
    * [`getTileCache()`](large_image.cache_util.md#large_image.cache_util.cache.getTileCache)
    * [`isTileCacheSetup()`](large_image.cache_util.md#large_image.cache_util.cache.isTileCacheSetup)
    * [`methodcache()`](large_image.cache_util.md#large_image.cache_util.cache.methodcache)
    * [`strhash()`](large_image.cache_util.md#large_image.cache_util.cache.strhash)
  * [large_image.cache_util.cachefactory module](large_image.cache_util.md#module-large_image.cache_util.cachefactory)
    * [`CacheFactory`](large_image.cache_util.md#large_image.cache_util.cachefactory.CacheFactory)
      * [`CacheFactory.getCache()`](large_image.cache_util.md#large_image.cache_util.cachefactory.CacheFactory.getCache)
      * [`CacheFactory.getCacheSize()`](large_image.cache_util.md#large_image.cache_util.cachefactory.CacheFactory.getCacheSize)
      * [`CacheFactory.logged`](large_image.cache_util.md#large_image.cache_util.cachefactory.CacheFactory.logged)
    * [`getFirstAvailableCache()`](large_image.cache_util.md#large_image.cache_util.cachefactory.getFirstAvailableCache)
    * [`loadCaches()`](large_image.cache_util.md#large_image.cache_util.cachefactory.loadCaches)
    * [`pickAvailableCache()`](large_image.cache_util.md#large_image.cache_util.cachefactory.pickAvailableCache)
  * [large_image.cache_util.memcache module](large_image.cache_util.md#module-large_image.cache_util.memcache)
    * [`MemCache`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache)
      * [`MemCache.clear()`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache.clear)
      * [`MemCache.curritems`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache.curritems)
      * [`MemCache.currsize`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache.currsize)
      * [`MemCache.getCache()`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache.getCache)
      * [`MemCache.maxsize`](large_image.cache_util.md#large_image.cache_util.memcache.MemCache.maxsize)
  * [large_image.cache_util.rediscache module](large_image.cache_util.md#module-large_image.cache_util.rediscache)
    * [`RedisCache`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache)
      * [`RedisCache.clear()`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache.clear)
      * [`RedisCache.curritems`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache.curritems)
      * [`RedisCache.currsize`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache.currsize)
      * [`RedisCache.getCache()`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache.getCache)
      * [`RedisCache.maxsize`](large_image.cache_util.md#large_image.cache_util.rediscache.RedisCache.maxsize)
  * [Module contents](large_image.cache_util.md#module-large_image.cache_util)
    * [`CacheFactory`](large_image.cache_util.md#large_image.cache_util.CacheFactory)
      * [`CacheFactory.getCache()`](large_image.cache_util.md#large_image.cache_util.CacheFactory.getCache)
      * [`CacheFactory.getCacheSize()`](large_image.cache_util.md#large_image.cache_util.CacheFactory.getCacheSize)
      * [`CacheFactory.logged`](large_image.cache_util.md#large_image.cache_util.CacheFactory.logged)
    * [`LruCacheMetaclass`](large_image.cache_util.md#large_image.cache_util.LruCacheMetaclass)
      * [`LruCacheMetaclass.classCaches`](large_image.cache_util.md#large_image.cache_util.LruCacheMetaclass.classCaches)
      * [`LruCacheMetaclass.namedCaches`](large_image.cache_util.md#large_image.cache_util.LruCacheMetaclass.namedCaches)
    * [`MemCache`](large_image.cache_util.md#large_image.cache_util.MemCache)
      * [`MemCache.clear()`](large_image.cache_util.md#large_image.cache_util.MemCache.clear)
      * [`MemCache.curritems`](large_image.cache_util.md#large_image.cache_util.MemCache.curritems)
      * [`MemCache.currsize`](large_image.cache_util.md#large_image.cache_util.MemCache.currsize)
      * [`MemCache.getCache()`](large_image.cache_util.md#large_image.cache_util.MemCache.getCache)
      * [`MemCache.maxsize`](large_image.cache_util.md#large_image.cache_util.MemCache.maxsize)
    * [`RedisCache`](large_image.cache_util.md#large_image.cache_util.RedisCache)
      * [`RedisCache.clear()`](large_image.cache_util.md#large_image.cache_util.RedisCache.clear)
      * [`RedisCache.curritems`](large_image.cache_util.md#large_image.cache_util.RedisCache.curritems)
      * [`RedisCache.currsize`](large_image.cache_util.md#large_image.cache_util.RedisCache.currsize)
      * [`RedisCache.getCache()`](large_image.cache_util.md#large_image.cache_util.RedisCache.getCache)
      * [`RedisCache.maxsize`](large_image.cache_util.md#large_image.cache_util.RedisCache.maxsize)
    * [`getTileCache()`](large_image.cache_util.md#large_image.cache_util.getTileCache)
    * [`isTileCacheSetup()`](large_image.cache_util.md#large_image.cache_util.isTileCacheSetup)
    * [`methodcache()`](large_image.cache_util.md#large_image.cache_util.methodcache)
    * [`pickAvailableCache()`](large_image.cache_util.md#large_image.cache_util.pickAvailableCache)
    * [`strhash()`](large_image.cache_util.md#large_image.cache_util.strhash)
* [large_image.tilesource package](large_image.tilesource.md)
  * [Subpackages](large_image.tilesource.md#subpackages)
    * [large_image.tilesource.eager_utils package](large_image.tilesource.eager_utils.md)
      * [Submodules](large_image.tilesource.eager_utils.md#submodules)
      * [large_image.tilesource.eager_utils.eager_fn module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_fn)
      * [large_image.tilesource.eager_utils.eager_image_modifications module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_image_modifications)
      * [large_image.tilesource.eager_utils.eager_pytorch_threading_context module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_pytorch_threading_context)
      * [large_image.tilesource.eager_utils.eager_read_args module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_read_args)
      * [large_image.tilesource.eager_utils.eager_shared_array module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_shared_array)
      * [large_image.tilesource.eager_utils.eager_wsi_operations module](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils.eager_wsi_operations)
      * [Module contents](large_image.tilesource.eager_utils.md#module-large_image.tilesource.eager_utils)
  * [Submodules](large_image.tilesource.md#submodules)
  * [large_image.tilesource.base module](large_image.tilesource.md#module-large_image.tilesource.base)
    * [`FileTileSource`](large_image.tilesource.md#large_image.tilesource.base.FileTileSource)
      * [`FileTileSource.addKnownMimetypes()`](large_image.tilesource.md#large_image.tilesource.base.FileTileSource.addKnownMimetypes)
      * [`FileTileSource.canRead()`](large_image.tilesource.md#large_image.tilesource.base.FileTileSource.canRead)
      * [`FileTileSource.getLRUHash()`](large_image.tilesource.md#large_image.tilesource.base.FileTileSource.getLRUHash)
      * [`FileTileSource.getState()`](large_image.tilesource.md#large_image.tilesource.base.FileTileSource.getState)
    * [`TileSource`](large_image.tilesource.md#large_image.tilesource.base.TileSource)
      * [`TileSource.axesToFrame()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.axesToFrame)
      * [`TileSource.bandCount`](large_image.tilesource.md#large_image.tilesource.base.TileSource.bandCount)
      * [`TileSource.canRead()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.canRead)
      * [`TileSource.channelNames`](large_image.tilesource.md#large_image.tilesource.base.TileSource.channelNames)
      * [`TileSource.convertRegionScale()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.convertRegionScale)
      * [`TileSource.dtype`](large_image.tilesource.md#large_image.tilesource.base.TileSource.dtype)
      * [`TileSource.eagerIterator()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.eagerIterator)
      * [`TileSource.extensions`](large_image.tilesource.md#large_image.tilesource.base.TileSource.extensions)
      * [`TileSource.frameToAxes()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.frameToAxes)
      * [`TileSource.frames`](large_image.tilesource.md#large_image.tilesource.base.TileSource.frames)
      * [`TileSource.geospatial`](large_image.tilesource.md#large_image.tilesource.base.TileSource.geospatial)
      * [`TileSource.getAssociatedImage()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getAssociatedImage)
      * [`TileSource.getAssociatedImagesList()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getAssociatedImagesList)
      * [`TileSource.getBandInformation()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getBandInformation)
      * [`TileSource.getBounds()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getBounds)
      * [`TileSource.getCenter()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getCenter)
      * [`TileSource.getGeospatialRegion()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getGeospatialRegion)
      * [`TileSource.getICCProfiles()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getICCProfiles)
      * [`TileSource.getInternalMetadata()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getInternalMetadata)
      * [`TileSource.getLRUHash()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getLRUHash)
      * [`TileSource.getLevelForMagnification()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getLevelForMagnification)
      * [`TileSource.getMagnificationForLevel()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getMagnificationForLevel)
      * [`TileSource.getMetadata()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getMetadata)
      * [`TileSource.getNativeMagnification()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getNativeMagnification)
      * [`TileSource.getOneBandInformation()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getOneBandInformation)
      * [`TileSource.getPixel()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getPixel)
      * [`TileSource.getPointAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getPointAtAnotherScale)
      * [`TileSource.getPreferredLevel()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getPreferredLevel)
      * [`TileSource.getRegion()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getRegion)
      * [`TileSource.getRegionAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getRegionAtAnotherScale)
      * [`TileSource.getSingleTile()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getSingleTile)
      * [`TileSource.getSingleTileAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getSingleTileAtAnotherScale)
      * [`TileSource.getState()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getState)
      * [`TileSource.getThumbnail()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getThumbnail)
      * [`TileSource.getTile()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getTile)
      * [`TileSource.getTileCount()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getTileCount)
      * [`TileSource.getTileMimeType()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.getTileMimeType)
      * [`TileSource.histogram()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.histogram)
      * [`TileSource.levels`](large_image.tilesource.md#large_image.tilesource.base.TileSource.levels)
      * [`TileSource.metadata`](large_image.tilesource.md#large_image.tilesource.base.TileSource.metadata)
      * [`TileSource.mimeTypes`](large_image.tilesource.md#large_image.tilesource.base.TileSource.mimeTypes)
      * [`TileSource.name`](large_image.tilesource.md#large_image.tilesource.base.TileSource.name)
      * [`TileSource.nameMatches`](large_image.tilesource.md#large_image.tilesource.base.TileSource.nameMatches)
      * [`TileSource.newPriority`](large_image.tilesource.md#large_image.tilesource.base.TileSource.newPriority)
      * [`TileSource.sizeX`](large_image.tilesource.md#large_image.tilesource.base.TileSource.sizeX)
      * [`TileSource.sizeY`](large_image.tilesource.md#large_image.tilesource.base.TileSource.sizeY)
      * [`TileSource.style`](large_image.tilesource.md#large_image.tilesource.base.TileSource.style)
      * [`TileSource.tileFrames()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.tileFrames)
      * [`TileSource.tileHeight`](large_image.tilesource.md#large_image.tilesource.base.TileSource.tileHeight)
      * [`TileSource.tileIterator()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.tileIterator)
      * [`TileSource.tileIteratorAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.tileIteratorAtAnotherScale)
      * [`TileSource.tileWidth`](large_image.tilesource.md#large_image.tilesource.base.TileSource.tileWidth)
      * [`TileSource.wrapKey()`](large_image.tilesource.md#large_image.tilesource.base.TileSource.wrapKey)
  * [large_image.tilesource.eageriterator module](large_image.tilesource.md#module-large_image.tilesource.eageriterator)
    * [`EagerIterator`](large_image.tilesource.md#large_image.tilesource.eageriterator.EagerIterator)
      * [`EagerIterator.cleanup()`](large_image.tilesource.md#large_image.tilesource.eageriterator.EagerIterator.cleanup)
      * [`EagerIterator.get_output_image_count()`](large_image.tilesource.md#large_image.tilesource.eageriterator.EagerIterator.get_output_image_count)
      * [`EagerIterator.read()`](large_image.tilesource.md#large_image.tilesource.eageriterator.EagerIterator.read)
  * [large_image.tilesource.geo module](large_image.tilesource.md#module-large_image.tilesource.geo)
    * [`GDALBaseFileTileSource`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource)
      * [`GDALBaseFileTileSource.extensions`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.extensions)
      * [`GDALBaseFileTileSource.geospatial`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.geospatial)
      * [`GDALBaseFileTileSource.getBounds()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getBounds)
      * [`GDALBaseFileTileSource.getHexColors()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getHexColors)
      * [`GDALBaseFileTileSource.getNativeMagnification()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getNativeMagnification)
      * [`GDALBaseFileTileSource.getPixelSizeInMeters()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getPixelSizeInMeters)
      * [`GDALBaseFileTileSource.getThumbnail()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getThumbnail)
      * [`GDALBaseFileTileSource.getTileCorners()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.getTileCorners)
      * [`GDALBaseFileTileSource.isGeospatial()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.isGeospatial)
      * [`GDALBaseFileTileSource.mimeTypes`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.mimeTypes)
      * [`GDALBaseFileTileSource.pixelToProjection()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.pixelToProjection)
      * [`GDALBaseFileTileSource.projection`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.projection)
      * [`GDALBaseFileTileSource.projectionOrigin`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.projectionOrigin)
      * [`GDALBaseFileTileSource.sourceLevels`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.sourceLevels)
      * [`GDALBaseFileTileSource.sourceSizeX`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.sourceSizeX)
      * [`GDALBaseFileTileSource.sourceSizeY`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.sourceSizeY)
      * [`GDALBaseFileTileSource.toNativePixelCoordinates()`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.toNativePixelCoordinates)
      * [`GDALBaseFileTileSource.unitsAcrossLevel0`](large_image.tilesource.md#large_image.tilesource.geo.GDALBaseFileTileSource.unitsAcrossLevel0)
    * [`GeoBaseFileTileSource`](large_image.tilesource.md#large_image.tilesource.geo.GeoBaseFileTileSource)
    * [`make_vsi()`](large_image.tilesource.md#large_image.tilesource.geo.make_vsi)
  * [large_image.tilesource.jupyter module](large_image.tilesource.md#module-large_image.tilesource.jupyter)
    * [`IPyLeafletMixin`](large_image.tilesource.md#large_image.tilesource.jupyter.IPyLeafletMixin)
      * [`IPyLeafletMixin.JUPYTER_HOST`](large_image.tilesource.md#large_image.tilesource.jupyter.IPyLeafletMixin.JUPYTER_HOST)
      * [`IPyLeafletMixin.JUPYTER_PROXY`](large_image.tilesource.md#large_image.tilesource.jupyter.IPyLeafletMixin.JUPYTER_PROXY)
      * [`IPyLeafletMixin.as_leaflet_layer()`](large_image.tilesource.md#large_image.tilesource.jupyter.IPyLeafletMixin.as_leaflet_layer)
      * [`IPyLeafletMixin.iplmap`](large_image.tilesource.md#large_image.tilesource.jupyter.IPyLeafletMixin.iplmap)
    * [`Map`](large_image.tilesource.md#large_image.tilesource.jupyter.Map)
      * [`Map.add_region_indicator()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.add_region_indicator)
      * [`Map.from_map()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.from_map)
      * [`Map.get_frame_histogram()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.get_frame_histogram)
      * [`Map.id`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.id)
      * [`Map.layer`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.layer)
      * [`Map.make_layer()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.make_layer)
      * [`Map.make_map()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.make_map)
      * [`Map.map`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.map)
      * [`Map.metadata`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.metadata)
      * [`Map.to_map()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.to_map)
      * [`Map.update_frame()`](large_image.tilesource.md#large_image.tilesource.jupyter.Map.update_frame)
    * [`NumpyEncoder`](large_image.tilesource.md#large_image.tilesource.jupyter.NumpyEncoder)
      * [`NumpyEncoder.default()`](large_image.tilesource.md#large_image.tilesource.jupyter.NumpyEncoder.default)
    * [`RequestManager`](large_image.tilesource.md#large_image.tilesource.jupyter.RequestManager)
      * [`RequestManager.port`](large_image.tilesource.md#large_image.tilesource.jupyter.RequestManager.port)
      * [`RequestManager.ports`](large_image.tilesource.md#large_image.tilesource.jupyter.RequestManager.ports)
      * [`RequestManager.tile_source`](large_image.tilesource.md#large_image.tilesource.jupyter.RequestManager.tile_source)
    * [`launch_tile_server()`](large_image.tilesource.md#large_image.tilesource.jupyter.launch_tile_server)
  * [large_image.tilesource.resample module](large_image.tilesource.md#module-large_image.tilesource.resample)
    * [`ResampleMethod`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod)
      * [`ResampleMethod.NP_MAX`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MAX)
      * [`ResampleMethod.NP_MAX_COLOR`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MAX_COLOR)
      * [`ResampleMethod.NP_MEAN`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MEAN)
      * [`ResampleMethod.NP_MEDIAN`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MEDIAN)
      * [`ResampleMethod.NP_MIN`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MIN)
      * [`ResampleMethod.NP_MIN_COLOR`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MIN_COLOR)
      * [`ResampleMethod.NP_MODE`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_MODE)
      * [`ResampleMethod.NP_NEAREST`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.NP_NEAREST)
      * [`ResampleMethod.PIL_BICUBIC`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_BICUBIC)
      * [`ResampleMethod.PIL_BILINEAR`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_BILINEAR)
      * [`ResampleMethod.PIL_BOX`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_BOX)
      * [`ResampleMethod.PIL_HAMMING`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_HAMMING)
      * [`ResampleMethod.PIL_LANCZOS`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_LANCZOS)
      * [`ResampleMethod.PIL_MAX_ENUM`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_MAX_ENUM)
      * [`ResampleMethod.PIL_NEAREST`](large_image.tilesource.md#large_image.tilesource.resample.ResampleMethod.PIL_NEAREST)
    * [`downsampleTileHalfRes()`](large_image.tilesource.md#large_image.tilesource.resample.downsampleTileHalfRes)
    * [`numpyResize()`](large_image.tilesource.md#large_image.tilesource.resample.numpyResize)
    * [`pilResize()`](large_image.tilesource.md#large_image.tilesource.resample.pilResize)
  * [large_image.tilesource.stylefuncs module](large_image.tilesource.md#module-large_image.tilesource.stylefuncs)
    * [`maskPixelValues()`](large_image.tilesource.md#large_image.tilesource.stylefuncs.maskPixelValues)
    * [`medianFilter()`](large_image.tilesource.md#large_image.tilesource.stylefuncs.medianFilter)
  * [large_image.tilesource.tiledict module](large_image.tilesource.md#module-large_image.tilesource.tiledict)
    * [`LazyTileDict`](large_image.tilesource.md#large_image.tilesource.tiledict.LazyTileDict)
      * [`LazyTileDict.release()`](large_image.tilesource.md#large_image.tilesource.tiledict.LazyTileDict.release)
      * [`LazyTileDict.setFormat()`](large_image.tilesource.md#large_image.tilesource.tiledict.LazyTileDict.setFormat)
  * [large_image.tilesource.tileiterator module](large_image.tilesource.md#module-large_image.tilesource.tileiterator)
    * [`TileIterator`](large_image.tilesource.md#large_image.tilesource.tileiterator.TileIterator)
  * [large_image.tilesource.utilities module](large_image.tilesource.md#module-large_image.tilesource.utilities)
    * [`ImageBytes`](large_image.tilesource.md#large_image.tilesource.utilities.ImageBytes)
      * [`ImageBytes.mimetype`](large_image.tilesource.md#large_image.tilesource.utilities.ImageBytes.mimetype)
    * [`JSONDict`](large_image.tilesource.md#large_image.tilesource.utilities.JSONDict)
    * [`addPILFormatsToOutputOptions()`](large_image.tilesource.md#large_image.tilesource.utilities.addPILFormatsToOutputOptions)
    * [`dictToEtree()`](large_image.tilesource.md#large_image.tilesource.utilities.dictToEtree)
    * [`etreeToDict()`](large_image.tilesource.md#large_image.tilesource.utilities.etreeToDict)
    * [`fullAlphaValue()`](large_image.tilesource.md#large_image.tilesource.utilities.fullAlphaValue)
    * [`getAvailableNamedPalettes()`](large_image.tilesource.md#large_image.tilesource.utilities.getAvailableNamedPalettes)
    * [`getPaletteColors()`](large_image.tilesource.md#large_image.tilesource.utilities.getPaletteColors)
    * [`getTileFramesQuadInfo()`](large_image.tilesource.md#large_image.tilesource.utilities.getTileFramesQuadInfo)
    * [`histogramThreshold()`](large_image.tilesource.md#large_image.tilesource.utilities.histogramThreshold)
    * [`isValidPalette()`](large_image.tilesource.md#large_image.tilesource.utilities.isValidPalette)
    * [`nearPowerOfTwo()`](large_image.tilesource.md#large_image.tilesource.utilities.nearPowerOfTwo)
  * [Module contents](large_image.tilesource.md#module-large_image.tilesource)
    * [`FileTileSource`](large_image.tilesource.md#large_image.tilesource.FileTileSource)
      * [`FileTileSource.addKnownMimetypes()`](large_image.tilesource.md#large_image.tilesource.FileTileSource.addKnownMimetypes)
      * [`FileTileSource.canRead()`](large_image.tilesource.md#large_image.tilesource.FileTileSource.canRead)
      * [`FileTileSource.getLRUHash()`](large_image.tilesource.md#large_image.tilesource.FileTileSource.getLRUHash)
      * [`FileTileSource.getState()`](large_image.tilesource.md#large_image.tilesource.FileTileSource.getState)
    * [`TileGeneralError`](large_image.tilesource.md#large_image.tilesource.TileGeneralError)
    * [`TileGeneralException`](large_image.tilesource.md#large_image.tilesource.TileGeneralException)
    * [`TileSource`](large_image.tilesource.md#large_image.tilesource.TileSource)
      * [`TileSource.axesToFrame()`](large_image.tilesource.md#large_image.tilesource.TileSource.axesToFrame)
      * [`TileSource.bandCount`](large_image.tilesource.md#large_image.tilesource.TileSource.bandCount)
      * [`TileSource.canRead()`](large_image.tilesource.md#large_image.tilesource.TileSource.canRead)
      * [`TileSource.channelNames`](large_image.tilesource.md#large_image.tilesource.TileSource.channelNames)
      * [`TileSource.convertRegionScale()`](large_image.tilesource.md#large_image.tilesource.TileSource.convertRegionScale)
      * [`TileSource.dtype`](large_image.tilesource.md#large_image.tilesource.TileSource.dtype)
      * [`TileSource.eagerIterator()`](large_image.tilesource.md#large_image.tilesource.TileSource.eagerIterator)
      * [`TileSource.extensions`](large_image.tilesource.md#large_image.tilesource.TileSource.extensions)
      * [`TileSource.frameToAxes()`](large_image.tilesource.md#large_image.tilesource.TileSource.frameToAxes)
      * [`TileSource.frames`](large_image.tilesource.md#large_image.tilesource.TileSource.frames)
      * [`TileSource.geospatial`](large_image.tilesource.md#large_image.tilesource.TileSource.geospatial)
      * [`TileSource.getAssociatedImage()`](large_image.tilesource.md#large_image.tilesource.TileSource.getAssociatedImage)
      * [`TileSource.getAssociatedImagesList()`](large_image.tilesource.md#large_image.tilesource.TileSource.getAssociatedImagesList)
      * [`TileSource.getBandInformation()`](large_image.tilesource.md#large_image.tilesource.TileSource.getBandInformation)
      * [`TileSource.getBounds()`](large_image.tilesource.md#large_image.tilesource.TileSource.getBounds)
      * [`TileSource.getCenter()`](large_image.tilesource.md#large_image.tilesource.TileSource.getCenter)
      * [`TileSource.getGeospatialRegion()`](large_image.tilesource.md#large_image.tilesource.TileSource.getGeospatialRegion)
      * [`TileSource.getICCProfiles()`](large_image.tilesource.md#large_image.tilesource.TileSource.getICCProfiles)
      * [`TileSource.getInternalMetadata()`](large_image.tilesource.md#large_image.tilesource.TileSource.getInternalMetadata)
      * [`TileSource.getLRUHash()`](large_image.tilesource.md#large_image.tilesource.TileSource.getLRUHash)
      * [`TileSource.getLevelForMagnification()`](large_image.tilesource.md#large_image.tilesource.TileSource.getLevelForMagnification)
      * [`TileSource.getMagnificationForLevel()`](large_image.tilesource.md#large_image.tilesource.TileSource.getMagnificationForLevel)
      * [`TileSource.getMetadata()`](large_image.tilesource.md#large_image.tilesource.TileSource.getMetadata)
      * [`TileSource.getNativeMagnification()`](large_image.tilesource.md#large_image.tilesource.TileSource.getNativeMagnification)
      * [`TileSource.getOneBandInformation()`](large_image.tilesource.md#large_image.tilesource.TileSource.getOneBandInformation)
      * [`TileSource.getPixel()`](large_image.tilesource.md#large_image.tilesource.TileSource.getPixel)
      * [`TileSource.getPointAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.TileSource.getPointAtAnotherScale)
      * [`TileSource.getPreferredLevel()`](large_image.tilesource.md#large_image.tilesource.TileSource.getPreferredLevel)
      * [`TileSource.getRegion()`](large_image.tilesource.md#large_image.tilesource.TileSource.getRegion)
      * [`TileSource.getRegionAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.TileSource.getRegionAtAnotherScale)
      * [`TileSource.getSingleTile()`](large_image.tilesource.md#large_image.tilesource.TileSource.getSingleTile)
      * [`TileSource.getSingleTileAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.TileSource.getSingleTileAtAnotherScale)
      * [`TileSource.getState()`](large_image.tilesource.md#large_image.tilesource.TileSource.getState)
      * [`TileSource.getThumbnail()`](large_image.tilesource.md#large_image.tilesource.TileSource.getThumbnail)
      * [`TileSource.getTile()`](large_image.tilesource.md#large_image.tilesource.TileSource.getTile)
      * [`TileSource.getTileCount()`](large_image.tilesource.md#large_image.tilesource.TileSource.getTileCount)
      * [`TileSource.getTileMimeType()`](large_image.tilesource.md#large_image.tilesource.TileSource.getTileMimeType)
      * [`TileSource.histogram()`](large_image.tilesource.md#large_image.tilesource.TileSource.histogram)
      * [`TileSource.levels`](large_image.tilesource.md#large_image.tilesource.TileSource.levels)
      * [`TileSource.metadata`](large_image.tilesource.md#large_image.tilesource.TileSource.metadata)
      * [`TileSource.mimeTypes`](large_image.tilesource.md#large_image.tilesource.TileSource.mimeTypes)
      * [`TileSource.name`](large_image.tilesource.md#large_image.tilesource.TileSource.name)
      * [`TileSource.nameMatches`](large_image.tilesource.md#large_image.tilesource.TileSource.nameMatches)
      * [`TileSource.newPriority`](large_image.tilesource.md#large_image.tilesource.TileSource.newPriority)
      * [`TileSource.sizeX`](large_image.tilesource.md#large_image.tilesource.TileSource.sizeX)
      * [`TileSource.sizeY`](large_image.tilesource.md#large_image.tilesource.TileSource.sizeY)
      * [`TileSource.style`](large_image.tilesource.md#large_image.tilesource.TileSource.style)
      * [`TileSource.tileFrames()`](large_image.tilesource.md#large_image.tilesource.TileSource.tileFrames)
      * [`TileSource.tileHeight`](large_image.tilesource.md#large_image.tilesource.TileSource.tileHeight)
      * [`TileSource.tileIterator()`](large_image.tilesource.md#large_image.tilesource.TileSource.tileIterator)
      * [`TileSource.tileIteratorAtAnotherScale()`](large_image.tilesource.md#large_image.tilesource.TileSource.tileIteratorAtAnotherScale)
      * [`TileSource.tileWidth`](large_image.tilesource.md#large_image.tilesource.TileSource.tileWidth)
      * [`TileSource.wrapKey()`](large_image.tilesource.md#large_image.tilesource.TileSource.wrapKey)
    * [`TileSourceAssetstoreError`](large_image.tilesource.md#large_image.tilesource.TileSourceAssetstoreError)
    * [`TileSourceAssetstoreException`](large_image.tilesource.md#large_image.tilesource.TileSourceAssetstoreException)
    * [`TileSourceError`](large_image.tilesource.md#large_image.tilesource.TileSourceError)
    * [`TileSourceException`](large_image.tilesource.md#large_image.tilesource.TileSourceException)
    * [`TileSourceFileNotFoundError`](large_image.tilesource.md#large_image.tilesource.TileSourceFileNotFoundError)
    * [`canRead()`](large_image.tilesource.md#large_image.tilesource.canRead)
    * [`dictToEtree()`](large_image.tilesource.md#large_image.tilesource.dictToEtree)
    * [`etreeToDict()`](large_image.tilesource.md#large_image.tilesource.etreeToDict)
    * [`getSourceNameFromDict()`](large_image.tilesource.md#large_image.tilesource.getSourceNameFromDict)
    * [`getTileSource()`](large_image.tilesource.md#large_image.tilesource.getTileSource)
    * [`listExtensions()`](large_image.tilesource.md#large_image.tilesource.listExtensions)
    * [`listMimeTypes()`](large_image.tilesource.md#large_image.tilesource.listMimeTypes)
    * [`listSources()`](large_image.tilesource.md#large_image.tilesource.listSources)
    * [`nearPowerOfTwo()`](large_image.tilesource.md#large_image.tilesource.nearPowerOfTwo)
    * [`new()`](large_image.tilesource.md#large_image.tilesource.new)
    * [`open()`](large_image.tilesource.md#large_image.tilesource.open)

## Submodules

## large_image.config module

### large_image.config.cpu_count(logical: bool = True) → int

Get the usable CPU count.  If psutil is available, it is used, since it can
determine the number of physical CPUS versus logical CPUs.  This returns
the smaller of that value from psutil and the number of cpus allowed by the
os scheduler, which means that for physical requests (logical=False), the
returned value may be more the the number of physical cpus that are usable.

* **Parameters:**
  **logical** – True to get the logical usable CPUs (which include
  hyperthreading).  False for the physical usable CPUs.
* **Returns:**
  the number of usable CPUs.

### large_image.config.getConfig(key: str | None = None, default: str | bool | int | Logger | None = None) → Any

Get the config dictionary or a value from the cache config settings.

* **Parameters:**
  * **key** – if None, return the config dictionary.  Otherwise, return the
    value of the key if it is set or the default value if it is not.
  * **default** – a value to return if a key is requested and not set.
* **Returns:**
  either the config dictionary or the value of a key.

### large_image.config.getLogger(key: str | None = None, default: Logger | None = None) → Logger

Get a logger from the config.  Ensure that it is a valid logger.

* **Parameters:**
  * **key** – if None, return the ‘logger’.
  * **default** – a value to return if a key is requested and not set.
* **Returns:**
  a logger.

### large_image.config.minimizeCaching(mode: str | None = None) → None

Set python cache sizes to very low values.

* **Parameters:**
  **mode** – None for all caching, ‘tile’ for the tile cache, ‘source’ for
  the source cache.

### large_image.config.setConfig(key: str, value: str | bool | int | Logger | None) → None

Set a value in the config settings.

* **Parameters:**
  * **key** – the key to set.
  * **value** – the value to store in the key.

### large_image.config.total_memory() → int

Get the total memory in the system.  If this is in a container, try to
determine the memory available to the cgroup.

* **Returns:**
  the available memory in bytes, or 8 GB if unknown.

## large_image.constants module

### *class* large_image.constants.SourcePriority(value)

Bases: `IntEnum`

#### FALLBACK *= 11*

#### FALLBACK_HIGH *= 10*

#### HIGH *= 3*

#### HIGHER *= 2*

#### IMPLICIT *= 8*

#### IMPLICIT_HIGH *= 7*

#### IMPLICIT_LOW *= 9*

#### LOW *= 5*

#### LOWER *= 6*

#### MANUAL *= 12*

#### MEDIUM *= 4*

#### NAMED *= 0*

#### PREFERRED *= 1*

## large_image.exceptions module

### *exception* large_image.exceptions.TileCacheConfigurationError

Bases: [`TileCacheError`](#large_image.exceptions.TileCacheError)

### *exception* large_image.exceptions.TileCacheError

Bases: [`TileGeneralError`](#large_image.exceptions.TileGeneralError)

### *exception* large_image.exceptions.TileGeneralError

Bases: `Exception`

### large_image.exceptions.TileGeneralException

alias of [`TileGeneralError`](#large_image.exceptions.TileGeneralError)

### *exception* large_image.exceptions.TileSourceAssetstoreError

Bases: [`TileSourceError`](#large_image.exceptions.TileSourceError)

### large_image.exceptions.TileSourceAssetstoreException

alias of [`TileSourceAssetstoreError`](#large_image.exceptions.TileSourceAssetstoreError)

### *exception* large_image.exceptions.TileSourceError

Bases: [`TileGeneralError`](#large_image.exceptions.TileGeneralError)

### large_image.exceptions.TileSourceException

alias of [`TileSourceError`](#large_image.exceptions.TileSourceError)

### *exception* large_image.exceptions.TileSourceFileNotFoundError(\*args)

Bases: [`TileSourceError`](#large_image.exceptions.TileSourceError), `FileNotFoundError`

### *exception* large_image.exceptions.TileSourceInefficientError

Bases: [`TileSourceError`](#large_image.exceptions.TileSourceError)

### *exception* large_image.exceptions.TileSourceMalformedError

Bases: [`TileSourceError`](#large_image.exceptions.TileSourceError)

### *exception* large_image.exceptions.TileSourceRangeError

Bases: [`TileSourceError`](#large_image.exceptions.TileSourceError)

### *exception* large_image.exceptions.TileSourceXYZRangeError

Bases: [`TileSourceRangeError`](#large_image.exceptions.TileSourceRangeError)

## Module contents
