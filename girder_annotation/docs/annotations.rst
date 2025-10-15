Annotation Schema
=================

An annotation consists of a basic structure which includes a free-form
``attributes`` object and a list of ``elements``. The elements are
strictly specified by the schema and are mostly limited to a set of defined
shapes.

In addition to elements defined as shapes, image overlays are supported.

Partial annotations are shown below with some example values. Note that
the comments are not part of a valid annotation:

::

  {
    "name": "MyAnnotationName",              # Non-empty string.  Optional
    "description": "This is a description",  # String.  Optional
    "display": {                             # Object.  Optional
        "visible": "new",                    # String or boolean.  Optional.
                    # If "new", display this annotation when it first is added
                    # to the system.  If false, don't display the annotation by
                    # default.  If true, display the annotation when the item
                    # is loaded.
    },
    "attributes": {                          # Object.  Optional
      "key1": "value1",
      "key2": ["any", {"value": "can"}, "go", "here"]
    },
    "elements": []                           # A list.  Optional.
                                             # See below for valid elements.
  }

Elements
--------

Currently, most defined elements are shapes. Image overlays are not defined as
shapes. All of the shape elements have some properties that they are allowed.
Each element type is listed below:

All shapes
~~~~~~~~~~

All shapes have the following properties. If a property is not listed,
it is not allowed. If element IDs are specified, they must be unique.

::

  {
    "type": "point",                  # Exact string for the specific shape.  Required
    "id": "0123456789abcdef01234567", # String, 24 lowercase hexadecimal digits.  Optional.
    "label": {                        # Object.  Optional
      "value": "This is a label",     # String.  Required
      "visibility": "hidden",         # String.  One of "always", "hidden", "onhover".  Optional
      "fontSize": 3.4,                # Number.  Optional
      "color": "#0000FF"              # String.  See note about colors.  Optional
    },
    "group": "group name",            # String. Optional
    "user": {},                       # User properties -- this can contain anything,
                                      # but should be kept small.  Optional.
    <shape specific properties>
  }


All Vector Shapes
~~~~~~~~~~~~~~~~~

These properties exist for all vector shapes (all but heatmaps, grid data, and image and pixelmap overlays).

::

  {
    "lineColor": "#000000",           # String.  See note about colors.  Optional
    "lineWidth": 1,                   # Number >= 0.  Optional
  }

Circle
~~~~~~

::

  {
    "type": "circle",                  # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "radius": 5.3,                     # Number >= 0.  Required
    "fillColor": "#0000fF",            # String.  See note about colors.  Optional
  }

Ellipse
~~~~~~~

The width and height of an ellipse are the major and minor axes.

::

  {
    "type": "ellipse",                 # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.
                                       # Optional
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
  }

Point
~~~~~

::

  {
    "type": "point",                   # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "center": [123.3, 144.6, -123]     # Coordinate.  Required
  }

Polyline (Polygons and Lines)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When closed, this is a polygon. When open, this is a continuous line.

::

  {
    "type": "polyline",                # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "points": [                        # At least two points must be specified
      [5,6,0],                         # Coordinate.  At least two required
      [-17,6,0],
      [56,-45,6]
    ],
    "closed": true,                    # Boolean.  Default is false.  Optional
    "holes": [                         # Only used if closed is true.  A list of a list of
                                       # coordinates.  Each list of coordinates is a
                                       # separate hole within the main polygon, and is expected
                                       # to be contained within it and not cross the main
                                       # polygon or other holes.
      [
        [10,10,0],
        [20,30,0],
        [10,30,0]
      ]
    ],
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
  }

Rectangle
~~~~~~~~~

::

  {
    "type": "rectangle",               # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.
                                       # Optional
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
  }

Heatmap
~~~~~~~

A list of points with values that is interpreted as a heatmap so that
near by values aggregate together when viewed.

::

  {
    "type": "heatmap",                 # Exact string.  Required
    <id, label, group, user>           # Optional general shape properties
    "points": [                        # A list of coordinate-value entries.  Each is x, y, z, value.
      [32320, 48416, 0, 0.192],
      [40864, 109568, 0, 0.87],
      [53472, 63392, 0, 0.262],
      [23232, 96096, 0, 0.364],
      [10976, 93376, 0, 0.2],
      [42368, 65248, 0, 0.054]
    ],
    "radius": 25,                      # Positive number.  Optional.  The size of the gaussian point
                                       # spread
    "colorRange": ["rgba(0, 0, 0, 0)", "rgba(255, 255, 0, 1)"],  # A list of colors corresponding to
                                       # the rangeValues.  Optional
    "rangeValues": [0, 1],             # A list of range values corresponding to the colorRange list
                                       # and possibly normalized to a scale of [0, 1].  Optional
    "normalizeRange": true,            # If true, the rangeValues are normalized to [0, 1].  If
                                       # false, the rangeValues are in the
                                       # value domain.  Defaults to true.  Optional
    "scaleWithZoom": true              # If true, scale the size of points with the zoom level of
                                       # the map. In this case, radius is in pixels of the
                                       # associated image.  If false or unspecified, radius is in
                                       # screen pixels. Defaults to false. Optional
  }

Grid Data
~~~~~~~~~

For evenly spaced data that is interpreted as a heatmap, contour, or
choropleth, a grid with a list of values can be specified.

::

  {
    "type": "griddata",                # Exact string.  Required
    <id, label, group, user>           # Optional general shape properties
    "interpretation": "contour",       # One of heatmap, contour, or choropleth
    "gridWidth": 6,                    # Number of values across the grid.  Required
    "origin": [0, 0, 0],               # Origin including fixed z value.  Optional
    "dx": 32,                          # Grid spacing in x.  Optional
    "dy": 32,                          # Grid spacing in y.  Optional
    "colorRange": ["rgba(0, 0, 0, 0)", "rgba(255, 255, 0, 1)"], # A list of colors corresponding to
                                       # the rangeValues.  Optional
    "rangeValues": [0, 1],             # A list of range values corresponding to the colorRange list.
                                       # This should have the same number of entries as colorRange
                                       # unless a contour where stepped is true.  Possibly normalized
                                       # to a scale of [0, 1].  Optional
    "normalizeRange": false,           # If true, the rangeValues are normalized to [0, 1].  If
                                       # false, the rangeValues are in the value domain.  Defaults to
                                       # true.  Optional
    "minColor": "rgba(0, 0, 255, 1)",  # The color of data below the minimum range.  Optional
    "maxColor": "rgba(255, 255, 0, 1)", # The color of data above the maximum range.  Optional
    "stepped": true,                   # For contours, whether discrete colors or continuous colors
                                       # should be used.  Default false.  Optional
    "radius": 25,                      # Positive number.  Optional.  The size of the gaussian
                                       # point when using the heatman interprettation
    "scaleWithZoom": true              # If true, when using the heatmap interprettation,  scale
                                       # the size of points with the zoom level of the map. In
                                       # this case, radius is in pixels of the associated image.
                                       # If false or unspecified, radius is in screen pixels.
                                       # Defaults to false. Optional
    "values": [
      0.508,
      0.806,
      0.311,
      0.402,
      0.535,
      0.661,
      0.866,
      0.31,
      0.241,
      0.63,
      0.555,
      0.067,
      0.668,
      0.164,
      0.512,
      0.647,
      0.501,
      0.637,
      0.498,
      0.658,
      0.332,
      0.431,
      0.053,
      0.531
    ]
  }

Image overlays
~~~~~~~~~~~~~~

Image overlay annotations allow specifying a girder large image item
to display on top of the base image as an annotation. It supports
translation via the ``xoffset`` and ``yoffset`` properties, as well as other
types of transformations via its 'matrix' property which should be specified as
a ``2x2`` affine matrix.

::

  {
    "type": "image",                   # Exact string. Required
    <id, label, group, user>           # Optional general shape properties
    "girderId": <girder image id>,     # 24-character girder id pointing
                                       # to a large image object. Required
    "opacity": 1,                      # Default opacity for the overlay. Defaults to 1. Optional
    "hasAlpha": false,                 # Boolean specifying if the image has an alpha channel
                                       # that should be used in rendering.
    "transform": {                     # Object specifying additional overlay information. Optional
      "xoffset": 0,                    # How much to shift the overlaid image right.
      "yoffset": 0,                    # How much to shift the overlaid image down.
      "matrix": [                      # Affine matrix to specify transformations like scaling,
                                       # rotation, or shearing.
        [1, 0],
        [0, 1]
      ]
    }
  }

Tiled pixelmap overlays
~~~~~~~~~~~~~~~~~~~~~~~

Tiled pixelmap overlay annotations allow specifying a girder large
image item to display on top of the base image to help represent
categorical data. The specified large image overlay should be a
lossless tiled image where pixel values represent category indices
instead of colors. Data provided along with the ID of the image item
is used to color the pixelmap based on the categorical data.

The element must contain a ``values`` array. The indices of this
array correspond to pixel values on the pixelmap, and the values are
integers which correspond to indices in a ``categories`` array.
::

  {
    "type": "pixelmap",                # Exact string. Required
    <id, label, group, user>           # Optional general shape properties
    "girderId": <girder image id>,     # 24-character girder id pointing
                                       # to a large image object. Required
    "opacity": 1,                      # Default opacity for the overlay. Defaults to 1. Optional
    "transform": {                     # Object specifying additional overlay information. Optional
      "xoffset": 0,                    # How much to shift the overlaid image right.
      "yoffset": 0,                    # How much to shift the overlaid image down.
      "matrix": [                      # Affine matrix to specify transformations like scaling,
                                       # rotation, or shearing.
        [1, 0],
        [0, 1]
      ]
    },
    "boundaries": false,               # Whether boundaries within the pixelmap have unique values.
                                       # If so, the values array should only be half as long as the
                                       # actual number of distinct pixel values in the pixelmap. In
                                       # this case, for a given index i in the values array, the
                                       # pixels with value 2i will be given the corresponding
                                       # fillColor from the category information, and the pixels
                                       # with value 2i + 1 will be given the corresponding
                                       # strokeColor from the category information. Required
    "values": [                        # An array where the value at index 'i' is an integer
                                       # pointing to an index in the categories array. Required
        1,
        2,
        1,
        1,
        2,
      ],
      "categories": [                  # An array whose values contain category information.
        {
          "fillColor": "#0000FF",      # The color pixels with this category should be. Required
          "label": "class_a",          # A human-readable label for this category. Optional
        },
        {
          "fillColor": "#00FF00",
          "label": "class_b",

        },
        {
          "fillColor": "#FF0000",
          "label": "class_c",
        },
    ]
  }

Arrow
~~~~~

Not currently rendered.

::

  {
    "type": "arrow",                   # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "points": [                        # Arrows ALWAYS have two points
      [5,6,0],                         # Coordinate.  Arrow head.  Required
      [-17,6,0]                        # Coordinate.  Aroow tail.  Required
    ]
  }

Rectangle Grid
~~~~~~~~~~~~~~

Not currently rendered.

A Rectangle Grid is a rectangle which contains regular subdivisions,
such as that used to show a regular scale grid overlay on an image.

::

  {
    "type": "rectanglegrid",           # Exact string.  Required
    <id, label, group, user, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.
                                       # Optional
    "widthSubdivisions": 3,            # Integer > 0.  Required
    "heightSubdivisions": 4,           # Integer > 0.  Required
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
  }

Component Values
----------------

Colors
~~~~~~

Colors are specified using a css-like string. Specifically, values of the form ``#RRGGBB``, ``#RGB``, ``#RRGGBBAA``, and ``#RGBA`` are allowed where ``R``,
``G``, ``B``, and ``A`` are case-insensitive hexadecimal digits. Additionally,
values of the form ``rgb(123, 123, 123)`` and ``rgba(123, 123, 123, 0.123)``
are allowed, where the colors are specified on a [0-255] integer scale, and
the opacity is specified as a [0-1] floating-point number.

Coordinates
~~~~~~~~~~~

Coordinates are specified as a triplet of floating point numbers. They
are **always** three dimensional. As an example:

``[1.3, -4.5, 0.3]``

A sample annotation
-------------------

A sample that shows off a valid annotation:

::

  {
    "name": "AnnotationName",
    "description": "This is a description",
    "attributes": {
      "key1": "value1",
      "key2": ["any", {"value": "can"}, "go", "here"]
    },
    "elements": [{
      "type": "point",
      "label": {
        "value": "This is a label",
        "visibility": "hidden",
        "fontSize": 3.4
      },
      "lineColor": "#000000",
      "lineWidth": 1,
      "center": [123.3, 144.6, -123]
    },{
      "type": "arrow",
      "points": [
        [5,6,0],
        [-17,6,0]
      ],
      "lineColor": "rgba(128, 128, 128, 0.5)"
    },{
      "type": "circle",
      "center": [10.3, -40.0, 0],
      "radius": 5.3,
      "fillColor": "#0000fF",
      "lineColor": "rgb(3, 6, 8)"
    },{
      "type": "rectangle",
      "center": [10.3, -40.0, 0],
      "width": 5.3,
      "height": 17.3,
      "rotation": 0,
      "fillColor": "rgba(0, 255, 0, 1)"
    },{
      "type": "ellipse",
      "center": [3.53, 4.8, 0],
      "width": 15.7,
      "height": 7.1,
      "rotation": 0.34,
      "fillColor": "rgba(128, 255, 0, 0.5)"
    },{
      "type": "polyline",
      "points": [
        [5,6,0],
        [-17,6,0],
        [56,-45,6]
      ],
      "closed": true
    },{
      "type": "rectanglegrid",
      "id": "0123456789abcdef01234567",
      "center": [10.3, -40.0, 0],
      "width": 5.3,
      "height": 17.3,
      "rotation": 0,
      "widthSubdivisions": 3,
      "heightSubdivisions": 4
    }]
  }

Full Schema
-----------

The full schema can be obtained by calling the Girder endpoint of
``GET`` ``/annotation/schema``.
