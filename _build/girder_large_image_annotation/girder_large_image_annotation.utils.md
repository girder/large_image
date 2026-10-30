# girder_large_image_annotation.utils package

## Module contents

### *class* girder_large_image_annotation.utils.AnnotationGeoJSON(annotationId, asFeatures=False, mustConvert=False)

Bases: `object`

Generate GeoJSON for an annotation via an iterator.

Return an itertor for converting an annotation into geojson.

* **Parameters:**
  * **annotatioId** – the id of the annotation.  No permissions checks
    are performed.
  * **asFeatures** – if False, return a geojson string.  If True, return
    the features of the geojson.  This can be wrapped in
    {‘type’: ‘FeatureCollection’, ‘features: […output…]}
    to make it a full geojson object.
  * **mustConvert** – if True, raise an exception if any annotation
    elements cannot be converted.  Otherwise, skip those elements.

#### circleType(element, geom, prop)

#### elementToGeoJSON(element)

#### ellipseType(element, geom, prop)

#### *property* geojson

#### pointType(element, geom, prop)

#### polylineType(element, geom, prop)

#### rectangleType(element, geom, prop)

#### rotate(r, cx, cy, x, y, z)

### *class* girder_large_image_annotation.utils.GeoJSONAnnotation(geojson)

Bases: `object`

#### *property* annotation

#### annotationToJSON()

#### circleType(elem, result)

#### *property* elementCount

#### *property* elements

#### ellipseType(elem, result)

#### linestringType(elem, result)

#### multilinestringType(elem, result)

#### multipointType(elem, result)

#### multipolygonType(elem, result)

#### pointType(elem, result)

#### polygonType(elem, result)

#### polylineType(elem, result)

#### rectangleType(elem, result)

### *class* girder_large_image_annotation.utils.PlottableItemData(user, item, annotations=None, adjacentItems=False, sources=None, compute=None, uuid=None)

Bases: `object`

Get plottable data associated with an item.

* **Parameters:**
  * **user** – authenticating user.
  * **item** – the item record.
  * **annotations** – None, a list of annotation ids, or \_\_all_\_.  If
    adjacent items are included, the most recent annotation with the
    same name will also be included.
  * **adjacentItems** – if True, include data from other items in the
    same folder.  If \_\_all_\_, include data from other items even if the
    data is not present in the current item.
  * **sources** – None for all, or a string with a comma-separated list
    or a list of strings; when a list, the options are folder, item,
    annotation, datafile.
  * **compute** – None for none, or a dictionary with keys “columns”: a
    list of columns to include in the computation; if unspecified or an
    empty list, no computation is done, “function”: a string with the
    name of the function, such as umap, “params”: additional parameters
    to pass to the function.  If none of the requiredKeys are
    compute.(x|y|z), the computation will not be performed.  Only rows
    which have all selected columns present will be included in the
    computation.
  * **uuid** – An optional uuid to allow cancelling a previous request.
    If specified and there are any outstanding requests with the same
    uuid, they may be cancelled to save resources.

#### allowedTypes *= (<class 'str'>, <class 'bool'>, <class 'int'>, <class 'float'>)*

#### *property* columns

Get a sorted list of plottable columns with some metadata for each.

Each data entry contains

> * **key:**
>   the column key.  For database entries, this is (item|
>   annotation|annotationelement).(id|name|description|group|
>   label).  For bounding boxes this is bbox.(x0|y0|x1|y1).  For
>   data from meta / attributes / user, this is
>   data.(key)[.0][.(key2)][.0]
> * **type:**
>   ‘string’ or ‘number’
> * **title:**
>   a human readable title
> * **count:**
>   the number of non-null entries in the column
> * **[distinct]:**
>   a list of distinct values if there are less than some
>   maximum number of distinct values.  This might not include
>   values from adjacent items
> * **[distinctcount]:**
>   if distinct is populated, this is len(distinct)
> * **[min]:**
>   for number data types, the lowest value present
> * **[max]:**
>   for number data types, the highest value present
* **Returns:**
  a sorted list of data entries.

#### commonColumns *= {'annotation.description': 'Annotation Description', 'annotation.id': 'Annotation ID', 'annotation.name': 'Annotation Name', 'annotationelement.group': 'Annotation Element Group', 'annotationelement.id': 'Annotation Element ID', 'annotationelement.label': 'Annotation Element Label', 'annotationelement.type': 'Annotation Element Type', 'bbox.x0': 'Bounding Box Low X', 'bbox.x1': 'Bounding Box High X', 'bbox.y0': 'Bounding Box Low Y', 'bbox.y1': 'Bounding Box High Y', 'compute.x': 'Dimension Reduction X', 'compute.y': 'Dimension Reduction Y', 'compute.z': 'Dimension Reduction Z', 'item.description': 'Item Description', 'item.id': 'Item ID', 'item.name': 'Item Name'}*

#### computeColumns *= {'compute.x', 'compute.y', 'compute.z'}*

#### data(columns, requiredColumns=None)

Get plottable data.

* **Parameters:**
  * **columns** – the columns to return.  Either a list of column names
    or a comma-delimited string.
  * **requiredColumns** – only return data rows where all of these
    columns are non-None.  Either a list of column names of a
    comma-delimited string.

#### datafileAnnotationElementSelector(key, cols)

#### itemNameIDSelector(isName, selector)

Given a data selector that returns something that is either an item id,
an item name, or an item name prefix, return the canonical item or
id string from the list of known items.

* **Parameters:**
  * **isName** – True to return the canonical name, False for the
    canonical id.
  * **selector** – the selector to get the initial value.
* **Returns:**
  a function that can be used as an overall selector.

#### *static* keySelector(mode, key, key2=None)

Given a pattern for getting data from a dictionary, return a selector
that gets that piece of data.

* **Parameters:**
  * **mode** – one of key, key0, keykey, keykey0, key0key, representing
    key lookups in dictionaries or array indices.
  * **key** – the first key.
  * **key2** – the second key, if needed.
* **Returns:**
  a pair of functions that can be used to select the value from
  the record and data structure.  This takes (record, data, row) and
  returns a value.  The record is the base record used, the data is
  the base dictionary, and the row is the location in the index.  The
  second function takes (record, data) and returns either None or the
  number of rows that are present.

#### maxAnnotationElements *= 25000*

#### maxDistinct *= 20*

#### maxItems *= 1000*

#### *static* recordSelector(doctype)

Given a document type, return a function that returns the main data
dictionary.

* **Parameters:**
  **doctype** – one of folder, item, annotaiton, annotationelement.
* **Returns:**
  a function that takes (record) and returns the data
  dictionary, if any.

### girder_large_image_annotation.utils.isGeoJSON(annotation)

Check if a list or dictionary appears to contain a GeoJSON record.

* **Parameters:**
  **annotation** – a list or dictionary.
* **Returns:**
  True if this appears to be GeoJSON
