Plottable Data
==============

There is a python utility class and some REST endpoints to obtain plottable data related to a large image item optionally along with other items in the same Girder_ folder.  This plottable data can be drawn from item metadata, folder metadata, annotation attributes, and annotation element user properties, plus a few core properties of items, annotations, and annotation elements.

See the `PlottableItemData <_build/girder_large_image_annotation/girder_large_image_annotation.utils.html#girder_large_image_annotation.utils.PlottableItemData>`_ for the Python API, or ``POST`` ``annotation/item/{id}/plot/list`` and ``POST`` ``annotation/item/{id}/plot/data`` for the endpoints.

In general, data is parsed from the ``meta`` dictionary of items and folders, from the ``attributes`` dictionary of annotations, and the ``user`` dictionary of annotation elements.  For any of these locations, any data that has a data type of a string, number (floating point or integer), or boolean can be used.  Data must be referenced by a dictionary key, and can be in nested dictionaries and arrays, but not recursively.

Structurally, data can be referenced within the primary dictionary of each resource via any of the following access patterns (where ``data`` is the primary dictionary: ``meta``, ``attributes``, or ``user``):

For instance, each of the following has two separate keys with plottable data (some with one value and some with an array of three values):

+---------------------------+----------------------------------------------+
| Data Arrangement          | Example                                      |
+===========================+==============================================+
| key - value               | ::                                           |
|                           |                                              |
|                           |   "meta": {                                  |
|                           |     "nucleus_radius": 4.5,                   |
|                           |     "nucleus_circularity": 0.9               |
|                           |   }                                          |
+---------------------------+----------------------------------------------+
| key - value list          | ::                                           |
|                           |                                              |
|                           |   "meta": {                                  |
|                           |     "nucleus_radius": [4.5, 5.5, 5.1],       |
|                           |     "nucleus_circularity": [0.9, 0.86, 0.92] |
|                           |   }                                          |
+---------------------------+----------------------------------------------+
| nested key - value        | ::                                           |
|                           |                                              |
|                           |   "meta": {                                  |
|                           |     "nucleus": {                             |
|                           |       "radius": 4.5,                         |
|                           |       "circularity": 0.9                     |
|                           |     }                                        |
|                           |   }                                          |
+---------------------------+----------------------------------------------+
| nested key - value list   | ::                                           |
|                           |                                              |
|                           |   "meta": {                                  |
|                           |     "nucleus": {                             |
|                           |       "radius": [4.5, 5.5, 5.1],             |
|                           |       "circularity": [0.9, 0.86, 0.92]       |
|                           |     }                                        |
|                           |   }                                          |
+---------------------------+----------------------------------------------+
| key - list of key - value | ::                                           |
|                           |                                              |
|                           |   "meta": {                                  |
|                           |     "nucleus": [                             |
|                           |       {                                      |
|                           |         "radius": 4.5,                       |
|                           |         "circularity": 0.9                   |
|                           |       },                                     |
|                           |       {                                      |
|                           |         "radius": 5.5,                       |
|                           |         "circularity": 0.86                  |
|                           |       },                                     |
|                           |       {                                      |
|                           |         "radius": 5.1,                       |
|                           |         "circularity": 0.92                  |
|                           |       }                                      |
|                           |     ]                                        |
|                           |   }                                          |
+---------------------------+----------------------------------------------+

For plottable data in the ``meta`` key of a folder, (a) if the name of the most nested key matches the Python regular expression ``r'(?i)(item|image)_(id|name)$'``, then the value of that key will attempt to be resolved to the name or Girder _id of a item within the folder.  This will only match items that are included (the ``adjacentItems`` flag affects the results).  If a matching item is found, the item's canonical ``name`` and ``_id`` are used rather than the specified value.  (b) if the name of the key matches the Python regular expression ``r'(?i)(low|min|high|max)(_|)(x|y)'``, the value is assumed to be a coordinate of an image bounding box.  This can be used by clients to show a portion of the image associated with the plottable record.

After plottable data is gathered, columns of available data are summarized.  Each column contains:

* ``title``: a display-friendly title for the column.
* ``key``: the name of column for internal purposes and requests.
* ``type``: either ``'number'`` if all of the examined values for the data are None or can be cast to a ``float`` or ``'string'`` otherwise.
* ``count``: the number of rows where the value of this column is not None.
* ``distinct``: a list of distinct values if there are less than some maximum number of distinct values.
* ``distinctcount``: if ``distinct`` is present, the number of values in that list.
* ``min``: for number data columns, the lowest value present.
* ``max``: for number data columns, the highest value present.

Data rows are populated with more general data when possible.  For example, if data is selected from annotations, metadata from the parent item is present in each row.

.. _Girder: https://girder.readthedocs.io/en/latest/
