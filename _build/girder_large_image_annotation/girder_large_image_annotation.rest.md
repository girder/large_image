# girder_large_image_annotation.rest package

## Submodules

## girder_large_image_annotation.rest.annotation module

### *class* girder_large_image_annotation.rest.annotation.AnnotationResource

Bases: `Resource`

#### canCreateFolderAnnotations(folder)

#### copyAnnotation(annotation, params)

#### createAnnotation(item, params)

#### createItemAnnotations(item, annotations)

#### deleteAnnotation(annotation, params)

#### deleteFolderAnnotations(id, params)

#### deleteItemAnnotations(item)

#### deleteMetadata(annotation, fields)

#### deleteOldAnnotations(age, versions)

#### existFolderAnnotations(id, recurse)

#### find(params)

#### findAnnotatedImages(params)

#### getAnnotation(id, params)

#### getAnnotationAccess(annotation, params)

#### getAnnotationHistory(id, version)

#### getAnnotationHistoryList(id, limit, offset, sort)

#### getAnnotationSchema(params)

#### getAnnotationWithFormat(annotation, format)

#### getFolderAnnotations(id, recurse, user, limit=False, offset=False, sort=False, sortDir=False, count=False)

#### getItemAnnotations(item)

#### getItemListAnnotationCounts(items)

#### getItemPlottableData(item, keys, adjacentItems, annotations, requiredKeys, sources=None, compute=None, uuid=None)

#### getItemPlottableElements(item, annotations, adjacentItems, sources=None, uuid=None)

#### getOldAnnotations(age, versions)

#### patchAnnotation(annotation, params)

#### returnFolderAnnotations(id, recurse, limit, offset, sort)

#### revertAnnotationHistory(id, version)

#### setFolderAnnotationAccess(id, params)

#### setMetadata(annotation, metadata, allowNull)

#### updateAnnotation(annotation, params)

#### updateAnnotationAccess(annotation, params)

## Module contents
