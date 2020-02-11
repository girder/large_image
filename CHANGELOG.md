# Change Log

## Unreleased

### Features
- Added a GET large_image/sources endpoint to list versions of all installed sources

## Version 1.0.2

### Features
- Add style options for all tile sources to remap channels and colors (#397)
- Better support for high bit-depth images (#397)

### Improvements
- Make it easier to load the annotation-enable web viewers (#402)
- Improved support for z-loops in OMETiff files (#397)
- Support using Glymur 0.9.1 (#411)

### Bug Fixes
- Fixed an issue where a Girder image conversion task could raise an error about a missing file (#409)

## Version 1.0.1

### Features
- Get annotations elements by centroid (#371)
- Added an annotation badge to the image list (#372)
- Added openjpeg tile source (#380)
- Handle different tiff orientations in the tiff tile source (#390)

### Improvements
- Increased the annotation page limit (#367)
- Increased the annotations response time limit (#389)
- Improved handling of tiff files with multiple tiled images (#373)
- Don't reset backbone models on saving existing annotations (#399)

### Changes
- Use girder/large_image_wheels (#384)
- Changed the mapnik tile source style defaults (#395)

### Bug Fixes
- Fixed the pyproj minimum version (#366)
- Guard against GDAL open errors (#375)
- Better handle annotations with zero elements (#398)
- Sorting tile layers could use a dictionary comparison (#396)

## Version 1.0.0

This is a substantial refactor from preliminary versions.  Now that setuptools_scm is used for versioning, all merges to master are automatically published to pypi as development versions.  

Tile sources are now fully modular and are installed via pip.  File extensions and mime type are now used as part of the order that tile sources are checked, giving more control over which tile source is used by default.

The Girder plugin has been divided into the parts requiring annotations and the parts that are only necessary for large images.  

Python 3.4 support was dropped.


