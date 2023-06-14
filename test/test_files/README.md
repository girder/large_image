# Test Files

Contextual information on testing files:

## Files of the form `geotiff_*.png`

These files are used to confirm that specific tiles of specific sources are rendered the way we expect.  Files with the same root are all valid with minor variations depending on some sources (such as GDAL or mapnik) perform image rounding from different versions of the underlying libraries.

## `global_dem.tif`

This file is used to test that geospatial bounds are handled correctly on files that slightly misreport their values.

## `grey10kx5k.tif`

This file is used to test conversion and use of single band files.

## Files of the form `multi_*.yml`

These test a variety of the multi source options including different bands, channels, and scaling.

## `notanimage.txt`

This is used to test that non-images files are properly rejected.

## `rgb_geotiff.tif` and `rgba_geotiff.tiff`

Please note the `a` in `rgba_geotiff.tiff` -- this is a very different file
from `rgb_geotiff.tiff`.

The uniqueness of these files comes from their spatial reference.
These files do not have a transform/CRS but rather use ground control points
(GCPs).

At the time of writing this, only the `GDALFileTileSource` handles this in
its `_getGeoTransform()` method which looks like:

```py
from osgeo import gdal

dataset = gdal.Open('rgba_geotiff.tiff')
gt = dataset.GetGeoTransform()
if (dataset.GetGCPProjection() and dataset.GetGCPs()):
    gt = gdal.GCPsToGeoTransform(dataset.GetGCPs())
```

Note that for this file, `dataset.GetGeoTransform()` yields nothing:

```py
>>> dataset.GetGeoTransform()
(0.0, 1.0, 0.0, 0.0, 0.0, 1.0)
```

So to get the proper transform, we need to do:

```py
>>> gdal.GCPsToGeoTransform(dataset.GetGCPs())
(-10871649.873181608, 97.77818507997574, 0.0, 3949392.8198705595, 0.0, -97.72497866707454)
```

Whereas if we look at other files that do not use GCPs, they look like:

```py
>>> gdal.Open('global_dem.tif').GetGeoTransform()
(-180.00416667, 1.0, 0.0, 90.00416667, 0.0, -1.0)
```

## `sample.girder.cfg`

This file is used to test that girder config files are rendered in the UI correctly.

## `small_la.tiff`

This file is used to ensure that tiny files are opened and handled correctly.

## Files of the form `test_L*.png` and `test_RGB*.png`

These files test that different channels and bit depths are handled correctly.

## Files of the form `test_orient*.tif`

These files test that orientation is used when showing files.  The `test_orient0.tif` tests that an invalid orientation is handled.

## `yb10kx5k.png` and `yb10kx5ktrans.png`

These files are used to test conversion to more efficient encodings.

## `yb10kx5k.zstd.tiff`

This file is used to test support for zstd compression.

## `zero_gi.tif`

This file tests behavior when a file has a zero dimension.
