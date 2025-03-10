.. include:: ../girder_annotation/docs/annotations.rst

This returns the following:

.. include:: ../build/docs-work/annotation_schema.json
   :literal:

Uploading Via REST Endpoints
----------------------------

Annotations can be uploaded through the Girder UI on the item page.  Internally, this uploads files as usual in Girder via the ``POST`` ``file`` endpoint and passes a ``reference`` json parameter of ``{"identifier": "LargeImageAnnotationUpload", "itemId": <item id>}``.

Alternate Formats
-----------------

In addition to the native format for annotations, annotations in **geojson** can be passed to the ``Annotation.createAnnotation`` method, uploaded via the standard UI on the Girder item page or via the ``POST`` ``file`` endpoint.  All annotations can be read in geojson format via the ``Annotation.geojson`` method or downloaded via specifying the appropriate format from the ``GET`` ``annotation/{id}/{format}`` endpoint.
