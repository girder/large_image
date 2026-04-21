Multi Source Schema
===================

A multi-source tile source is used to composite multiple other sources into a
single conceptual tile source.  It is specified by a yaml or json file that
conforms to the appropriate schema.

Examples
--------

All of the examples presented here are in yaml; json works just as well.

Multi Z-position
~~~~~~~~~~~~~~~~

For example, if you have a set of individual files that you wish to treat as
multiple z slices in a single file, you can do something like:

::

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

Here, each of the files is explicitly listed with a specific ``z`` value.
Since these files are ordered, this could equivalently be done in a simpler
manner using a ``pathPattern``, which is a regular expression that can match
multiple files.

::

    ---
    sources:
      - path: .
        pathPattern: 'test_orient[1-8]\.tif'
        zStep: 1

Since the ``z`` value will default to 0, this works.  The files are sorted in
C-sort order (lexically using the ASCII or UTF code points).  This sorting will
break down if you have files with variable length numbers (e.g., ``file10.tif``
will appear before ``file9.tiff``.  You can instead assign values from the
file name using named expressions:

::

    ---
    sources:
      - path: .
        pathPattern: 'test_orient(?P<z1>[1-8])\.tif'

Note that the name in the expression (``z1`` in this example) is the name of
the value in the schema.  If a ``1`` is added, then it is assumed to be 1-based
indexed.  Without the ``1``, it is assumed to be zero-indexed.

Composite To A Single Frame
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Multiple sources can be made to appear as a single frame.  For instance:

::

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

Here, the total width and height of the final image is specified, along with
the upper-left position of each image in the frame.

Composite With Scaling
~~~~~~~~~~~~~~~~~~~~~~

Transforms can be applied to scale the individual sources:

::

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

Note that the zero values from the previous example have been omitted as they
are unnecessary.

Controlling Axis Values
~~~~~~~~~~~~~~~~~~~~~~~

Each frame can have a specific value per axis.  For each axis (e.g., ``t``) there are four controlling parameters, many of which only are applied when the source contains multiple frames.  For instance, suppose you have a source that contains 5 frames at ``t == [0, 1, 2, 3, 4]``.

Specifying ``<axis>Set`` (e.g., ``tSet``) with the source will set the value of that axis for all frames of that source.  In our example, ``tSet: 3`` will result in ``t == [3, 3, 3, 3, 3]``.  This can be useful if those frames are arranged on another axis.

If ``<axis>Set`` is not specified, specifying ``<axis>`` (e.g., ``t``) with the source will be a direct offset.  In our example, ``t: 3`` will add to the source;s t-values, such that ``t == [3, 4, 5, 6, 7]``.

If ``<axis>Set`` is not specified, specifying ``<axis>Values`` (e.g., ``tValues``) with the source will add the positional value to the frame value.  If ``<axis>Values`` is an array of length 1, this is functionally just added to ``<axis>``.  If ``<axis>Values`` is shorter than the number of frames, the last two values in the array are used as a stride.  In our example, if ``t: 3`` and ``tValues: [2]`` we end up with ``t == [5, 6, 7, 8, 9]``.  If ``t: 3`` and ``tValues: [2, 4]``, we end up with ``t == [5, 7, 9, 11, 13]``.  If ``t: 3`` and ``tValues: [0, 1, 3, 6, 10]``, we end up with ``t == [3, 5, 8, 12, 17``.

``<axis>Step`` (e.g., ``tStep``) is used with ``pathPattern`` to add a value to each separate source path.  The other parameters all affect a single source file with multiple frames.  For instance, if ``pathPattern`` includes 3 source files and ``tStep: 1``, then those three source files functionally have ``t: 0``, ``t: 1``, ``t: 2``.

Full Schema
-----------

The full schema (jsonschema Draft6 standard) can be obtained by referencing the
Python at ``large_image_source_multi.MultiSourceSchema``.
