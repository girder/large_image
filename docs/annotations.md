# Annotation Schema

The full schema can be obtained by calling the Girder endpoint of `GET` `/annotation/schema`.

An annotation consists of a basic structure which includes a free-form `attributes` object and a list of `elements`.  The elements are strictly specified by the schema and are limited to a set of defined shapes.

Partial annotations are shown below with some example values.  Note that the comments are not part of a valid annotation:

```
{
  "name": "MyAnnotationName",              # Non-empty string.  Optional
  "description": "This is a description",  # String.  Optional
  "attributes": {                          # Object.  Optional
    "key1": "value1",
    "key2": ["any", {"value": "can"}, "go", "here"]
  },
  "elements": []                           # A list.  Optional.
                                           # See below for valid elements.
}
```

## Elements

Currently, all defined elements are shapes.  All of these have some properties that they are allowed.  Each shape is listed below:

### All shapes

All shapes have the following properties.  If a property is not listed, it is not allowed.  If element IDs are specified, they must be unique.

```
{
    "type": "point",                  # Exact string for the specific shape.  Required
    "id": "0123456789abcdef01234567", # String, 24 lowercase hexadecimal digits.  Optional.
    "label": {                        # Object.  Optional
      "value": "This is a label",     # String.  Optional
      "visability": "hidden",         # String.  One of "always", "hidden", "onhover".  Optional
      "fontSize": 3.4,                # Number.  Optional
      "color": "#0000FF"              # String.  See note about colors.  Optional
    },
    "lineColor": "#000000",           # String.  See note about colors.  Optional
    "lineWidth": 1,                   # Number >= 0.  Optional
    "group": "group name",            # String. Optional
    <shape specific properties>
}
```

### Arrow

```
{
    "type": "arrow",                   # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "points": [                        # Arrows ALWAYS have two points
      [5,6,0],                         # Coordinate.  Arrow head.  Required
      [-17,6,0]                        # Coordinate.  Aroow tail.  Required
    ]
}
```

### Circle

```
{
    "type": "circle",                  # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "radius": 5.3,                     # Number >= 0.  Required
    "fillColor": "#0000fF",            # String.  See note about colors.  Optional
}
```

### Ellipse

The width and height of an ellipse are the major and minor axes.

```
{
    "type": "rectangle",               # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.  Optional
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
}
```

### Point

```
{
    "type": "point",                   # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "center": [123.3, 144.6, -123]     # Coordinate.  Required
}
```

### Polyline

```
{
    "type": "polyline",                # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "points": [                        # At least two points must be specified
      [5,6,0],                         # Coordinate.  At least two required
      [-17,6,0],
      [56,-45,6]
    ],
    "closed": true,                    # Boolean.  Default is false.  Optional
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
}
```

### Rectangle

```
{
    "type": "rectangle",               # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.  Optional
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
}
```

### Rectangle Grid

A Rectangle Grid is a rectangle which contains regular subdivisions, such as that used to show a regular scale grid overlay on an image.

```
{
    "type": "rectanglegrid",           # Exact string.  Required
    <id, label, lineColor, lineWidth>  # Optional general shape properties
    "center": [10.3, -40.0, 0],        # Coordinate.  Required
    "width": 5.3,                      # Number >= 0.  Required
    "height": 17.3,                    # Number >= 0.  Required
    "rotation": 0,                     # Number.  Counterclockwise radians around normal.  Required
    "normal": [0, 0, 1.0],             # Three numbers specifying normal.  Default is positive Z.  Optional
    "widthSubdivisions": 3,            # Integer > 0.  Required
    "heightSubdivisions": 4,           # Integer > 0.  Required
    "fillColor": "rgba(0, 255, 0, 1)"  # String.  See note about colors.  Optional
}
```

## Component Values

### Colors

Colors are specified using a css-like string.  Specifically, values of the form `#RRGGBB` and `#RGB` are allowed where `R`, `G`, and `B` are case-insensitive hexadecimal digits.  Additonally, values of the form `rgb(123, 123, 123)` and `rgba(123, 123, 123, 0.123)` are allowed, where the colors are specified on a [0-255]  integer scale, and the opacity is specified as a [0-1] floating-point number.

### Coordinates

Coordinates are specified as a triplet of floating point numbers.  They are **always** three dimensional.  As an example:

`[1.3, -4.5, 0.3]`


## A sample annotation

A sample that shows off a valid annotation:

```
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
      "visability": "hidden",
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
```
