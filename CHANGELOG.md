# Change Log

## Version 1.7.1

### Improvements
- More control over associated image caching (#638)
- Better handling some geospatial bounds (#639)

## Version 1.7.0

### Features
- Provide band information on all tile sources (#622, #623)
- Add a tileFrames method to tile sources and appropriate endpoints to composite regions from multiple frames to a single output image (#629)
- The test tile source now support frames (#631, #632, #634, #634)

### Improvements
- Better handle TIFFs with missing levels and tiles (#624, #627)
- Better report inefficient TIFFs (#626)
- Smoother cross-frame navigation (#635)

## Version 1.6.2

### Improvements
- Better reporting of memcached cache (#613)
- Better handle whether proj string need the +init prefix (#620)

### Changes
- Avoid a bad version of Pillow (#619)

## Version 1.6.1

### Improvements
- Allow specifying content disposition filenames in Girder REST endpoints (#604)
- Improve caching of unstyled tiles when compositing styled types (#605)
- Speed up compositing some styled tiles (#606, #609)
- Handle some nd2 files with missing metadata (#608)
- Allow setting default tile query parameters in the Girder client (#611)

### Changes
- Don't use underscore parameters in image caching keys (#610)

## Version 1.6.0

### Features
- Allow setting the cache memory portion and maximum for tilesources (#601)
- Add heatmap and griddata to the annotation schema (#589)
- Regions can be output as tiled tiffs with scale or geospatial metadata (#594)

### Improvements
- Cache histogram requests (#598)
- Allow configuring bioformats ignored extensions (#603)
- Tilesources always have self.logger for logging (#602)

### Changes
- Use float rather than numpy.float (#600)

### Bug Fixes
- The nd2reader module now requires files to have an nd2 extension (#599)
- Fix the progress bar when uploading annotations (#589)

## Version 1.5.0

### Features
- Allow converting a single frame of a multiframe image (#579)
- Add a convert endpoint to the Girder plugin (#578)
- Added support for creating Aperio svs files (#580)
- Added support for geospatial files with GCP (#588)

### Improvements
- More untiled tiff files are handles by the bioformats reader (#569)
- Expose a concurrent option on endpoints for converting images (#583)
- Better concurrency use in image conversion (#587)
- Handle more OME tiffs (#585, #591)
- Better memcached error logging (#592)

### Changes
- Exceptions on cached items are no longer within the KeyError context (#584)
- Simplified thumbnail generation by removing the level-0 option (#593)

### Bug Fixes
- Updated dependencies to work with changes to the nd2reader (#596)

## Version 1.4.3

### Improvements
- In Girder, prefer geospatial sources for geospatial data (#564)

### Bug Fixes
- The GDAL source failed when getting band ranges on non-integer data (#565)

## Version 1.4.2

### Features
- Added a Girder endpoint to get metadata on associated images (#561)
- Added an option to try all Girder items for use as large images (#562)

### Improvements
- Reduce gdal warning about projection strings (#559)
- Don't report needless frame information for some single frame files (#558)
- Send Backbone events on frame changes in the viewer (#563)

### Changes
- The PIL tilesource priority is slightly higher than other fallback sources (#560)

### Bug Fixes
- Fix compositing when using different frame numbers and partial tiles (#557)

## Version 1.4.1

### Features
- Multiple frames can be composited together with the style option (#554, #556)

### Improvements
- Warn when opening an inefficient tiff file (#555)

## Version 1.4.0

### Features
- Added a `canRead` method to the core module (#512)
- Image conversion supports JPEG 2000 (jp2k) compression (#522)
- Image conversion can now convert images readable by large_image sources but not by vips (#529)
- Added an `open` method to the core module as an alias to `getTileSource` (#550)
- Added an `open` method to each file source module (#550)
- Numerous improvement to image conversion (#533, #535, #537, #541, #544, #545, #546, #549)

### Improvements
- Better release bioformats resources (#502)
- Better handling of tiff files with JPEG compression and RGB colorspace (#503)
- The openjpeg tile source can decode with parallelism (#511)
- Geospatial tile sources are preferred for geospatial files (#512)
- Support decoding JP2k compressed tiles in the tiff tile source (#514)
- Hardened tests against transient timing issues (#532, #536)

### Changes
- The image conversion task has been split into two packages, large_image_converter and large_image_tasks.  The tasks module is used with Girder and Girder Worker for converting images and depends on the converter package.  The converter package can be used as a stand-alone command line tool (#518)

### Bug Fixes
- Harden updates of the item view after making a large image (#508, #515)
- Tiles in an unexpected color mode weren't consistently adjusted (#510)
- Harden trying to add an annotation before the viewer is ready (#547)
- Correctly report the tile size after resampling in the tileIterator (#538)

## Version 1.3.2

### Improvements
- Reduce caching associated images when the parent item changes (#491)
- Test with Python 3.9 (#493)
- Add a hideAnnotation function in the client (#490)
- Expose more resample options for region and histogram endpoints (#496)
- Improve OME tiff preferred level calculation for OME tiffs with subifds (#496)

### Changes
- Include the annotationType to the annotation conversion method in the client (#490)

### Notes
- This will be the last version to support Python 2.7 and 3.5.

## Version 1.3.1

### Improvements
- Include ETag support in some Girder rest requests to reduce data transfer (#488)

### Changes
- Don't let bioformats handle pngs (#487)

## Version 1.3.0

### Features
- Added bioformats tile source (#463)
- Handle OME Tiff files with sub-ifd images (#469)

### Improvements
- Expose more internal metadata (#479)
- Improve how Philips XML internal metadata is reported (#475)
- Show aperio version in internal metadata (#474)
- Add css classes to metadata on the item page (#472)
- The Girder web client exports the ItemViewWidget (#483)
- Read more associated images in openslide formats (#486)

### Bug Fixes
- Add a reference to updated time to avoid overcaching associated images (#477)
- Fix a typo in the settings page (#473)

## Version 1.2.0

### Features
- Added endpoints to remove old annotations (#432)
- Show auxiliary images and metadata on Girder item pages (#457)

### Improvements
- Migrate some database values on start to allow better annotation count reporting (#431)
- Speed up Girder item list annotation counts (#454)
- Read more OME Tiff files (#450)
- Handle subimages of different component depths (#449)
- When scaling, adjust reported mm_x/y (#441)

### Changes
- Standardize metadata for tile sources with multiple frames (#433)
- Unify code to check if a tile exists (#462)
- Switch to ElementTree, as cElementTree is deprecate (#461)
- Refactor how frame information is added to metadata (#460)
- Upgrade GeoJS to the latest version (#451)

### Bug Fixes
- Fix a threading issue with multiple styled tiles (#444)
- Guard against reading tiff tiles outside of the image (#458)
- Guard against a missing annotation value (#456(
- Fix handling Girder filenames with multiple periods in a row (#459)
- Work around a file descriptor issue in cheroot (#465)

## Version 1.1.0

### Features
- Added nd2 tile source (#419)

### Bug Fixes
- Fixed an issue where, if users or groups were deleted outside of normal methods, checking an annotation's access would delete its elements (#428)
- Fix an issue where retiling some tile sources could fail (#427)

### Improvements
- Testing fully with Python 3.8 (#429)

## Version 1.0.4

### Bug Fixes
- Fixed an issue where retiling some tile sources could fail (#427)

## Version 1.0.3

### Features
- Added gdal tile source (#418)
- Added a GET large_image/sources endpoint to list versions of all installed sources (#421)

### Bug Fixes
- Fixed an issue where changing the annotation history setting when Girder's settings' cache was enable wouldn't take effect until after a restart (#422)
- Fixed an issue when used as a Girder plugin and served with a proxy with a prefix path (#423)

### Improvements
- Better handling of imported file formats with adjacent files (#424)

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
