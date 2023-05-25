# Test Files

Contextual information on testing files

## `rgba_geotiff.tiff` and `small_la.tiff`

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
