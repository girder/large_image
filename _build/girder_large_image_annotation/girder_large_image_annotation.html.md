# girder_large_image_annotation package

## Subpackages

* [girder_large_image_annotation.models package](girder_large_image_annotation.models.md)
  * [Submodules](girder_large_image_annotation.models.md#submodules)
  * [girder_large_image_annotation.models.annotation module](girder_large_image_annotation.models.md#module-girder_large_image_annotation.models.annotation)
    * [`Annotation`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation)
      * [`Annotation.Skill`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.Skill)
      * [`Annotation.baseFields`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.baseFields)
      * [`Annotation.createAnnotation()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.createAnnotation)
      * [`Annotation.deleteMetadata()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.deleteMetadata)
      * [`Annotation.findAnnotatedImages()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.findAnnotatedImages)
      * [`Annotation.geojson()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.geojson)
      * [`Annotation.getVersion()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.getVersion)
      * [`Annotation.idRegex`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.idRegex)
      * [`Annotation.initialize()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.initialize)
      * [`Annotation.injectAnnotationGroupSet()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.injectAnnotationGroupSet)
      * [`Annotation.load()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.load)
      * [`Annotation.numberInstance`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.numberInstance)
      * [`Annotation.remove()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.remove)
      * [`Annotation.removeOldAnnotations()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.removeOldAnnotations)
      * [`Annotation.revertVersion()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.revertVersion)
      * [`Annotation.save()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.save)
      * [`Annotation.setAccessList()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.setAccessList)
      * [`Annotation.setMetadata()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.setMetadata)
      * [`Annotation.updateAnnotation()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.updateAnnotation)
      * [`Annotation.validate()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.validate)
      * [`Annotation.validatorAnnotation`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.validatorAnnotation)
      * [`Annotation.validatorAnnotationElement`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.validatorAnnotationElement)
      * [`Annotation.versionList()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.Annotation.versionList)
    * [`AnnotationSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema)
      * [`AnnotationSchema.annotationElementSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.annotationElementSchema)
      * [`AnnotationSchema.annotationSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.annotationSchema)
      * [`AnnotationSchema.arrowShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.arrowShapeSchema)
      * [`AnnotationSchema.baseElementSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.baseElementSchema)
      * [`AnnotationSchema.baseRectangleShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.baseRectangleShapeSchema)
      * [`AnnotationSchema.baseShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.baseShapeSchema)
      * [`AnnotationSchema.circleShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.circleShapeSchema)
      * [`AnnotationSchema.colorRangeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.colorRangeSchema)
      * [`AnnotationSchema.colorSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.colorSchema)
      * [`AnnotationSchema.coordSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.coordSchema)
      * [`AnnotationSchema.coordValueSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.coordValueSchema)
      * [`AnnotationSchema.ellipseShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.ellipseShapeSchema)
      * [`AnnotationSchema.griddataSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.griddataSchema)
      * [`AnnotationSchema.groupSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.groupSchema)
      * [`AnnotationSchema.heatmapSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.heatmapSchema)
      * [`AnnotationSchema.labelSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.labelSchema)
      * [`AnnotationSchema.overlaySchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.overlaySchema)
      * [`AnnotationSchema.patternSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.patternSchema)
      * [`AnnotationSchema.pixelmapCategorySchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.pixelmapCategorySchema)
      * [`AnnotationSchema.pixelmapSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.pixelmapSchema)
      * [`AnnotationSchema.pointShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.pointShapeSchema)
      * [`AnnotationSchema.polylineShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.polylineShapeSchema)
      * [`AnnotationSchema.rangeValueSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.rangeValueSchema)
      * [`AnnotationSchema.rectangleGridShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.rectangleGridShapeSchema)
      * [`AnnotationSchema.rectangleShapeSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.rectangleShapeSchema)
      * [`AnnotationSchema.transformArray`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.transformArray)
      * [`AnnotationSchema.userSchema`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.AnnotationSchema.userSchema)
    * [`extendSchema()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotation.extendSchema)
  * [girder_large_image_annotation.models.annotationelement module](girder_large_image_annotation.models.md#module-girder_large_image_annotation.models.annotationelement)
    * [`Annotationelement`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement)
      * [`Annotationelement.bboxKeys`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.bboxKeys)
      * [`Annotationelement.countElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.countElements)
      * [`Annotationelement.getElementGroupSet()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.getElementGroupSet)
      * [`Annotationelement.getElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.getElements)
      * [`Annotationelement.getNextVersionValue()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.getNextVersionValue)
      * [`Annotationelement.initialize()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.initialize)
      * [`Annotationelement.removeElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.removeElements)
      * [`Annotationelement.removeOldElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.removeOldElements)
      * [`Annotationelement.removeWithQuery()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.removeWithQuery)
      * [`Annotationelement.saveElementAsFile()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.saveElementAsFile)
      * [`Annotationelement.updateElementChunk()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.updateElementChunk)
      * [`Annotationelement.updateElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.updateElements)
      * [`Annotationelement.yieldElements()`](girder_large_image_annotation.models.md#girder_large_image_annotation.models.annotationelement.Annotationelement.yieldElements)
  * [Module contents](girder_large_image_annotation.models.md#module-girder_large_image_annotation.models)
* [girder_large_image_annotation.rest package](girder_large_image_annotation.rest.md)
  * [Submodules](girder_large_image_annotation.rest.md#submodules)
  * [girder_large_image_annotation.rest.annotation module](girder_large_image_annotation.rest.md#module-girder_large_image_annotation.rest.annotation)
    * [`AnnotationResource`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource)
      * [`AnnotationResource.canCreateFolderAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.canCreateFolderAnnotations)
      * [`AnnotationResource.copyAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.copyAnnotation)
      * [`AnnotationResource.createAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.createAnnotation)
      * [`AnnotationResource.createItemAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.createItemAnnotations)
      * [`AnnotationResource.deleteAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.deleteAnnotation)
      * [`AnnotationResource.deleteFolderAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.deleteFolderAnnotations)
      * [`AnnotationResource.deleteItemAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.deleteItemAnnotations)
      * [`AnnotationResource.deleteMetadata()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.deleteMetadata)
      * [`AnnotationResource.deleteOldAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.deleteOldAnnotations)
      * [`AnnotationResource.existFolderAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.existFolderAnnotations)
      * [`AnnotationResource.find()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.find)
      * [`AnnotationResource.findAnnotatedImages()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.findAnnotatedImages)
      * [`AnnotationResource.getAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotation)
      * [`AnnotationResource.getAnnotationAccess()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotationAccess)
      * [`AnnotationResource.getAnnotationHistory()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotationHistory)
      * [`AnnotationResource.getAnnotationHistoryList()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotationHistoryList)
      * [`AnnotationResource.getAnnotationSchema()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotationSchema)
      * [`AnnotationResource.getAnnotationWithFormat()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getAnnotationWithFormat)
      * [`AnnotationResource.getFolderAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getFolderAnnotations)
      * [`AnnotationResource.getItemAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getItemAnnotations)
      * [`AnnotationResource.getItemListAnnotationCounts()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getItemListAnnotationCounts)
      * [`AnnotationResource.getItemPlottableData()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getItemPlottableData)
      * [`AnnotationResource.getItemPlottableElements()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getItemPlottableElements)
      * [`AnnotationResource.getOldAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.getOldAnnotations)
      * [`AnnotationResource.patchAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.patchAnnotation)
      * [`AnnotationResource.returnFolderAnnotations()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.returnFolderAnnotations)
      * [`AnnotationResource.revertAnnotationHistory()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.revertAnnotationHistory)
      * [`AnnotationResource.setFolderAnnotationAccess()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.setFolderAnnotationAccess)
      * [`AnnotationResource.setMetadata()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.setMetadata)
      * [`AnnotationResource.updateAnnotation()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.updateAnnotation)
      * [`AnnotationResource.updateAnnotationAccess()`](girder_large_image_annotation.rest.md#girder_large_image_annotation.rest.annotation.AnnotationResource.updateAnnotationAccess)
  * [Module contents](girder_large_image_annotation.rest.md#module-girder_large_image_annotation.rest)
* [girder_large_image_annotation.utils package](girder_large_image_annotation.utils.md)
  * [Module contents](girder_large_image_annotation.utils.md#module-girder_large_image_annotation.utils)
    * [`AnnotationGeoJSON`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON)
      * [`AnnotationGeoJSON.circleType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.circleType)
      * [`AnnotationGeoJSON.elementToGeoJSON()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.elementToGeoJSON)
      * [`AnnotationGeoJSON.ellipseType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.ellipseType)
      * [`AnnotationGeoJSON.geojson`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.geojson)
      * [`AnnotationGeoJSON.pointType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.pointType)
      * [`AnnotationGeoJSON.polylineType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.polylineType)
      * [`AnnotationGeoJSON.rectangleType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.rectangleType)
      * [`AnnotationGeoJSON.rotate()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.AnnotationGeoJSON.rotate)
    * [`GeoJSONAnnotation`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation)
      * [`GeoJSONAnnotation.annotation`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.annotation)
      * [`GeoJSONAnnotation.annotationToJSON()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.annotationToJSON)
      * [`GeoJSONAnnotation.circleType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.circleType)
      * [`GeoJSONAnnotation.elementCount`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.elementCount)
      * [`GeoJSONAnnotation.elements`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.elements)
      * [`GeoJSONAnnotation.ellipseType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.ellipseType)
      * [`GeoJSONAnnotation.linestringType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.linestringType)
      * [`GeoJSONAnnotation.multilinestringType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.multilinestringType)
      * [`GeoJSONAnnotation.multipointType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.multipointType)
      * [`GeoJSONAnnotation.multipolygonType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.multipolygonType)
      * [`GeoJSONAnnotation.pointType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.pointType)
      * [`GeoJSONAnnotation.polygonType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.polygonType)
      * [`GeoJSONAnnotation.polylineType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.polylineType)
      * [`GeoJSONAnnotation.rectangleType()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.GeoJSONAnnotation.rectangleType)
    * [`PlottableItemData`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData)
      * [`PlottableItemData.allowedTypes`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.allowedTypes)
      * [`PlottableItemData.columns`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.columns)
      * [`PlottableItemData.commonColumns`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.commonColumns)
      * [`PlottableItemData.computeColumns`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.computeColumns)
      * [`PlottableItemData.data()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.data)
      * [`PlottableItemData.datafileAnnotationElementSelector()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.datafileAnnotationElementSelector)
      * [`PlottableItemData.itemNameIDSelector()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.itemNameIDSelector)
      * [`PlottableItemData.keySelector()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.keySelector)
      * [`PlottableItemData.maxAnnotationElements`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.maxAnnotationElements)
      * [`PlottableItemData.maxDistinct`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.maxDistinct)
      * [`PlottableItemData.maxItems`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.maxItems)
      * [`PlottableItemData.recordSelector()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.PlottableItemData.recordSelector)
    * [`isGeoJSON()`](girder_large_image_annotation.utils.md#girder_large_image_annotation.utils.isGeoJSON)

## Submodules

## girder_large_image_annotation.constants module

## girder_large_image_annotation.handlers module

### girder_large_image_annotation.handlers.process_annotations(event)

Add annotations to an image on a `data.process` event

### girder_large_image_annotation.handlers.resolveAnnotationGirderIds(event, results, data, possibleGirderIds)

If an annotation has references to girderIds, resolve them to actual ids.

* **Parameters:**
  * **event** – a data.process event.
  * **results** – the results from \_itemFromEvent,
  * **data** – annotation data.
  * **possibleGirderIds** – a list of annotation elements with girderIds
    needing resolution.
* **Returns:**
  True if all ids were processed.

## Module contents

### *class* girder_large_image_annotation.LargeImageAnnotationPlugin(entrypoint)

Bases: `GirderPlugin`

#### CLIENT_SOURCE_PATH *= 'web_client'*

The path of the plugin’s web client source code.  This path is given relative to the python
package.  This property is used to link the web client source into the staging area while
building in development mode.  When this value is None it indicates there is no web client
component.

#### DISPLAY_NAME *= 'Large Image Annotation'*

This is the named displayed to users on the plugin page.  Unlike the entrypoint name
used internally, this name can be an arbitrary string.

#### load(info)

### girder_large_image_annotation.metadataSearchHandler(\*args, \*\*kwargs)

### girder_large_image_annotation.validateBoolean(doc)
