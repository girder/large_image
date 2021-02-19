*****************
Large Image Tasks
*****************

These are Girder Worker tasks used by Large Image.

The conversion task is typically accessed by selecting the Make Large Image
icon on the items detail page in Girder, or by accessing the ``POST``
``item/{itemId}/tiles`` endpoint.  Using the endpoint allows specifying more
options and converting an inefficient file into a preferred format.  See the
``large_image_converter`` for more details on the various options.
