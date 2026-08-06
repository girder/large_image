# Multi Source Schema

A multi-source tile source is used to composite multiple other sources into a
single conceptual tile source.  It is specified by a yaml or json file that
conforms to the appropriate schema.

## Examples

All of the examples presented here are in yaml; json works just as well.

### Multi Z-position

For example, if you have a set of individual files that you wish to treat as
multiple z slices in a single file, you can do something like:

```default
---
sources:
  - path: ./test_orient1.tif
    z: 0
  - path: ./test_orient2.tif
    z: 1
  - path: ./test_orient3.tif
    z: 2
  - path: ./test_orient4.tif
    z: 3
  - path: ./test_orient5.tif
    z: 4
  - path: ./test_orient6.tif
    z: 5
  - path: ./test_orient7.tif
    z: 6
  - path: ./test_orient8.tif
    z: 7
```

Here, each of the files is explicitly listed with a specific `z` value.
Since these files are ordered, this could equivalently be done in a simpler
manner using a `pathPattern`, which is a regular expression that can match
multiple files.

```default
---
sources:
  - path: .
    pathPattern: 'test_orient[1-8]\.tif'
    zStep: 1
```

Since the `z` value will default to 0, this works.  The files are sorted in
C-sort order (lexically using the ASCII or UTF code points).  This sorting will
break down if you have files with variable length numbers (e.g., `file10.tif`
will appear before `file9.tiff`.  You can instead assign values from the
file name using named expressions:

```default
---
sources:
  - path: .
    pathPattern: 'test_orient(?P<z1>[1-8])\.tif'
```

Note that the name in the expression (`z1` in this example) is the name of
the value in the schema.  If a `1` is added, then it is assumed to be 1-based
indexed.  Without the `1`, it is assumed to be zero-indexed.

### Composite To A Single Frame

Multiple sources can be made to appear as a single frame.  For instance:

```default
---
width: 360
height: 360
sources:
  - path: ./test_orient1.tif
    z: 0
    position:
      x: 0
      y: 0
  - path: ./test_orient2.tif
    z: 0
    position:
      x: 180
      y: 0
  - path: ./test_orient3.tif
    z: 0
    position:
      x: 0
      y: 180
  - path: ./test_orient4.tif
    z: 0
    position:
      x: 180
      y: 180
```

Here, the total width and height of the final image is specified, along with
the upper-left position of each image in the frame.

### Composite With Scaling

Transforms can be applied to scale the individual sources:

```default
---
width: 720
height: 720
sources:
  - path: ./test_orient1.tif
    position:
      scale: 2
  - path: ./test_orient2.tif
    position:
      scale: 2
      x: 360
  - path: ./test_orient3.tif
    position:
      scale: 2
      y: 360
  - path: ./test_orient4.tif
    position:
      scale: 2
      x: 180
      y: 180
```

Note that the zero values from the previous example have been omitted as they
are unnecessary.

### Controlling Axis Values

Each frame can have a specific value per axis.  For each axis (e.g., `t`) there are four controlling parameters, many of which only are applied when the source contains multiple frames.  For instance, suppose you have a source that contains 5 frames at `t == [0, 1, 2, 3, 4]`.

Specifying `<axis>Set` (e.g., `tSet`) with the source will set the value of that axis for all frames of that source.  In our example, `tSet: 3` will result in `t == [3, 3, 3, 3, 3]`.  This can be useful if those frames are arranged on another axis.

If `<axis>Set` is not specified, specifying `<axis>` (e.g., `t`) with the source will be a direct offset.  In our example, `t: 3` will add to the source;s t-values, such that `t == [3, 4, 5, 6, 7]`.

If `<axis>Set` is not specified, specifying `<axis>Values` (e.g., `tValues`) with the source will add the positional value to the frame value.  If `<axis>Values` is an array of length 1, this is functionally just added to `<axis>`.  If `<axis>Values` is shorter than the number of frames, the last two values in the array are used as a stride.  In our example, if `t: 3` and `tValues: [2]` we end up with `t == [5, 6, 7, 8, 9]`.  If `t: 3` and `tValues: [2, 4]`, we end up with `t == [5, 7, 9, 11, 13]`.  If `t: 3` and `tValues: [0, 1, 3, 6, 10]`, we end up with `t == [3, 5, 8, 12, 17`.

`<axis>Step` (e.g., `tStep`) is used with `pathPattern` to add a value to each separate source path.  The other parameters all affect a single source file with multiple frames.  For instance, if `pathPattern` includes 3 source files and `tStep: 1`, then those three source files functionally have `t: 0`, `t: 1`, `t: 2`.

## Full Schema

The full schema (jsonschema Draft6 standard) can be obtained by referencing the
Python at `large_image_source_multi.MultiSourceSchema`.

This returns the following:

```default
{
  "$schema": "http://json-schema.org/schema#",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "name": {
      "type": "string"
    },
    "description": {
      "type": "string"
    },
    "width": {
      "type": "integer",
      "exclusiveMinimum": 0
    },
    "height": {
      "type": "integer",
      "exclusiveMinimum": 0
    },
    "tileWidth": {
      "type": "integer",
      "exclusiveMinimum": 0
    },
    "tileHeight": {
      "type": "integer",
      "exclusiveMinimum": 0
    },
    "channels": {
      "description": "A list of channel names",
      "type": "array",
      "items": {
        "type": "string"
      },
      "minItems": 1
    },
    "scale": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "mm_x": {
          "type": "number",
          "exclusiveMinimum": 0
        },
        "mm_y": {
          "type": "number",
          "exclusiveMinimum": 0
        },
        "magnification": {
          "type": "integer",
          "exclusiveMinimum": 0
        }
      }
    },
    "backgroundColor": {
      "description": "A list of background color values (fill color) in the same scale and band order as the first tile source (e.g., white might be [255, 255, 255] for a three channel image).",
      "type": "array",
      "items": {
        "type": "number"
      }
    },
    "basePath": {
      "description": "A relative path that is used as a base for all paths in sources.  Defaults to the directory of the main file.",
      "type": "string"
    },
    "uniformSources": {
      "description": "If true and the first two sources are similar in frame layout and size, assume all sources are so similar",
      "type": "boolean"
    },
    "dtype": {
      "description": "If present, a numpy dtype name to use for the data.",
      "type": "string"
    },
    "singleBand": {
      "description": "If true, output only the first band of compositied results",
      "type": "boolean"
    },
    "axes": {
      "description": "A list of additional axes that will be parsed.  The default axes are z, t, xy, and c.  It is recommended that additional axes use terse names and avoid x, y, and s.",
      "type": "array",
      "items": {
        "type": "string"
      }
    },
    "sources": {
      "type": "array",
      "items": {
        "type": "object",
        "additionalProperties": true,
        "properties": {
          "name": {
            "type": "string"
          },
          "description": {
            "type": "string"
          },
          "path": {
            "description": "The relative path, including file name if pathPattern is not specified.  The relative path excluding file name if pathPattern is specified.  Or, girder://id for Girder sources.  If a specific tile source is specified that does not need an actual path, the special value of `__none__` can be used to bypass checking for an actual file.",
            "type": "string"
          },
          "pathPattern": {
            "description": "If specified, file names in the path are matched to this regular expression, sorted in C-sort order.  This can populate other properties via named expressions, e.g., base_(?<xy>\\d+).png.  Add 1 to the name for 1-based numerical values.",
            "type": "string"
          },
          "sourceName": {
            "description": "Require a specific source by name.  This is one of the large_image source names (e.g., this one is \"multi\".",
            "type": "string"
          },
          "frame": {
            "description": "Base value for all frames; only use this if the data does not conceptually have z, t, xy, or c arrangement.",
            "type": "integer",
            "minimum": 0
          },
          "z": {
            "description": "Base value for all frames",
            "type": "integer",
            "minimum": 0
          },
          "t": {
            "description": "Base value for all frames",
            "type": "integer",
            "minimum": 0
          },
          "xy": {
            "description": "Base value for all frames",
            "type": "integer",
            "minimum": 0
          },
          "c": {
            "description": "Base value for all frames",
            "type": "integer",
            "minimum": 0
          },
          "zSet": {
            "description": "Override value for frame",
            "type": "integer",
            "minimum": 0
          },
          "tSet": {
            "description": "Override value for frame",
            "type": "integer",
            "minimum": 0
          },
          "xySet": {
            "description": "Override value for frame",
            "type": "integer",
            "minimum": 0
          },
          "cSet": {
            "description": "Override value for frame",
            "type": "integer",
            "minimum": 0
          },
          "zValues": {
            "description": "The numerical z position of the different z indices of the source.  If only one value is specified, other indices are shifted based on the source.  If fewer values are given than z indices, the last two value given imply a stride for the remainder.",
            "type": "array",
            "items": {
              "type": "number"
            },
            "minItems": 1
          },
          "tValues": {
            "description": "The numerical t position of the different t indices of the source.  If only one value is specified, other indices are shifted based on the source.  If fewer values are given than t indices, the last two value given imply a stride for the remainder.",
            "type": "array",
            "items": {
              "type": "number"
            },
            "minItems": 1
          },
          "xyValues": {
            "description": "The numerical xy position of the different xy indices of the source.  If only one value is specified, other indices are shifted based on the source.  If fewer values are given than xy indices, the last two value given imply a stride for the remainder.",
            "type": "array",
            "items": {
              "type": "number"
            },
            "minItems": 1
          },
          "cValues": {
            "description": "The numerical c position of the different c indices of the source.  If only one value is specified, other indices are shifted based on the source.  If fewer values are given than c indices, the last two value given imply a stride for the remainder.",
            "type": "array",
            "items": {
              "type": "number"
            },
            "minItems": 1
          },
          "frameValues": {
            "description": "The numerical frame position of the different frame indices of the source.  If only one value is specified, other indices are shifted based on the source.  If fewer values are given than frame indices, the last two value given imply a stride for the remainder.",
            "type": "array",
            "items": {
              "type": "number"
            },
            "minItems": 1
          },
          "channel": {
            "description": "A channel name to correspond with the main image.  Ignored if c, cValues, or channels is specified.",
            "type": "string"
          },
          "channels": {
            "description": "A list of channel names used to correspond channels in this source with the main image.  Ignored if c or cValues is specified.",
            "type": "array",
            "items": {
              "type": "string"
            },
            "minItems": 1
          },
          "zStep": {
            "description": "Step value for multiple files included via pathPattern.  Applies to z or zValues",
            "type": "integer",
            "exclusiveMinimum": 0
          },
          "tStep": {
            "description": "Step value for multiple files included via pathPattern.  Applies to t or tValues",
            "type": "integer",
            "exclusiveMinimum": 0
          },
          "xyStep": {
            "description": "Step value for multiple files included via pathPattern.  Applies to x or xyValues",
            "type": "integer",
            "exclusiveMinimum": 0
          },
          "xStep": {
            "description": "Step value for multiple files included via pathPattern.  Applies to c or cValues",
            "type": "integer",
            "exclusiveMinimum": 0
          },
          "framesAsAxes": {
            "description": "An object with keys as axes and values as strides to interpret the source frames.  This overrides the internal metadata for frames.",
            "type": "object",
            "patternProperties": {
              "^(c|t|z|xy)$": {
                "type": "integer",
                "exclusiveMinimum": 0
              }
            },
            "additionalProperties": false
          },
          "position": {
            "type": "object",
            "additionalProperties": false,
            "description": "The image can be translated with x, y offset, apply an affine transform, and scaled.  If only part of the source is desired, a crop can be applied before the transformation.",
            "properties": {
              "x": {
                "type": "number"
              },
              "y": {
                "type": "number"
              },
              "crop": {
                "description": "Crop the source before applying a position transform",
                "type": "object",
                "additionalProperties": false,
                "properties": {
                  "left": {
                    "type": "integer"
                  },
                  "top": {
                    "type": "integer"
                  },
                  "right": {
                    "type": "integer"
                  },
                  "bottom": {
                    "type": "integer"
                  }
                }
              },
              "warp": {
                "description": "An object describing a series of landmarks which have both a source location and a destination location. These sets of points define a warp (thin plate spline (TPS) or affine transform) that will be applied to the source image.",
                "type": "object",
                "properties": {
                  "src": {
                    "description": "The set of source locations for landmarks defining a warp. This can be described by a list of [x, y] points or a mapping of unique marker IDs to [x, y] points.",
                    "type": [
                      "array",
                      "object"
                    ],
                    "items": {
                      "type": "array",
                      "items": {
                        "type": "number"
                      },
                      "minItems": 2,
                      "maxItems": 2
                    },
                    "additionalProperties": {
                      "type": "array",
                      "items": {
                        "type": "number"
                      },
                      "minItems": 2,
                      "maxItems": 2
                    }
                  },
                  "dst": {
                    "description": "The set of destination locations for landmarks defining a warp. This can be described by a list of [x, y] points or a mapping of unique marker IDs to [x, y] points.",
                    "type": [
                      "array",
                      "object"
                    ],
                    "items": {
                      "type": "array",
                      "items": {
                        "type": "number"
                      },
                      "minItems": 2,
                      "maxItems": 2
                    },
                    "additionalProperties": {
                      "type": "array",
                      "items": {
                        "type": "number"
                      },
                      "minItems": 2,
                      "maxItems": 2
                    }
                  }
                }
              },
              "scale": {
                "description": "Values less than 1 will downsample the source.  Values greater than 1 will upsample it.",
                "type": "number",
                "exclusiveMinimum": 0
              },
              "s11": {
                "type": "number"
              },
              "s12": {
                "type": "number"
              },
              "s21": {
                "type": "number"
              },
              "s22": {
                "type": "number"
              }
            }
          },
          "frames": {
            "description": "List of frames to use from source",
            "type": "array",
            "items": {
              "type": "integer"
            }
          },
          "sampleScale": {
            "description": "Each pixel sample values is divided by this scale after any sampleOffset has been applied",
            "type": "number"
          },
          "sampleOffset": {
            "description": "This is added to each pixel sample value before any sampleScale is applied",
            "type": "number"
          },
          "style": {
            "description": "A style specification to pass to the base tile source",
            "type": "object"
          },
          "params": {
            "description": "Additional parameters to pass to the base tile source",
            "type": "object"
          }
        },
        "required": [
          "path"
        ]
      }
    }
  },
  "required": [
    "sources"
  ]
}
```
