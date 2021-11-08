# Change Log

## Version 1.8.6

### Bug Fixes
- A change in the Glymur library affected how missing files were handled ([#675](../../pull/675))

## Version 1.8.5

### Improvements
- Better Girder client exports ([#674](../../pull/674))

## Version 1.8.4

### Improvements
- Improve warnings on inefficient tiff files ([#668](../../pull/668))
- Add more options to setFrameQuad ([#669](../../pull/669), [#670](../../pull/670))
- Improved concurrency of opening multiple distinct tile sources ([#671](../../pull/671))

## Version 1.8.3

### Improvements
- Better handle item changes with tile caching ([#666](../../pull/666))

## Version 1.8.2

### Improvements
- Make the image viewer control css class more precise ([#665](../../pull/665))

## Version 1.8.1

### Improvements
- Allow GDAL source to read non-geospatial files ([#655](../../pull/655))
- Rename Exceptions to Errors, improve file-not-found errors ([#657](../../pull/657))
- More robust OME TIFF handling ([#660](../../pull/660))
- large-image-converter can exclude specified associated images ([#663](../../pull/663))
- Harden on some openslide errors ([#664](../../pull/664))

### Bug Fixes
- getBandInformation could fail on high bands in some cases ([#651](../../pull/651))
- Band information should always be 1-indexed ([#659](../../pull/659))
- Use GDAL to subset a non-geospatial image ([#662](../../pull/662))

## Version 1.8.0

### Features
- Deepzoom tile source ([#641](../../pull/641), [#647](../../pull/647))

### Bug Fixes
- Harden tile source detection ([#644](../../pull/644))

## Version 1.7.1

### Improvements
- More control over associated image caching ([#638](../../pull/638))
- Better handling some geospatial bounds ([#639](../../pull/639))

## Version 1.7.0

### Features
- Provide band information on all tile sources ([#622](../../pull/622), [#623](../../pull/623))
- Add a tileFrames method to tile sources and appropriate endpoints to composite regions from multiple frames to a single output image ([#629](../../pull/629))
- The test tile source now support frames ([#631](../../pull/631), [#632](../../pull/632), [#634](../../pull/634), [#634](../../pull/634))

### Improvements
- Better handle TIFFs with missing levels and tiles ([#624](../../pull/624), [#627](../../pull/627))
- Better report inefficient TIFFs ([#626](../../pull/626))
- Smoother cross-frame navigation ([#635](../../pull/635))

## Version 1.6.2

### Improvements
- Better reporting of memcached cache ([#613](../../pull/613))
- Better handle whether proj string need the +init prefix ([#620](../../pull/620))

### Changes
- Avoid a bad version of Pillow ([#619](../../pull/619))

## Version 1.6.1

### Improvements
- Allow specifying content disposition filenames in Girder REST endpoints ([#604](../../pull/604))
- Improve caching of unstyled tiles when compositing styled types ([#605](../../pull/605))
- Speed up compositing some styled tiles ([#606](../../pull/606), [#609](../../pull/609))
- Handle some nd2 files with missing metadata ([#608](../../pull/608))
- Allow setting default tile query parameters in the Girder client ([#611](../../pull/611))

### Changes
- Don't use underscore parameters in image caching keys ([#610](../../pull/610))

## Version 1.6.0

### Features
- Allow setting the cache memory portion and maximum for tilesources ([#601](../../pull/601))
- Add heatmap and griddata to the annotation schema ([#589](../../pull/589))
- Regions can be output as tiled tiffs with scale or geospatial metadata ([#594](../../pull/594))

### Improvements
- Cache histogram requests ([#598](../../pull/598))
- Allow configuring bioformats ignored extensions ([#603](../../pull/603))
- Tilesources always have self.logger for logging ([#602](../../pull/602))

### Changes
- Use float rather than numpy.float ([#600](../../pull/600))

### Bug Fixes
- The nd2reader module now requires files to have an nd2 extension ([#599](../../pull/599))
- Fix the progress bar when uploading annotations ([#589](../../pull/589))

## Version 1.5.0

### Features
- Allow converting a single frame of a multiframe image ([#579](../../pull/579))
- Add a convert endpoint to the Girder plugin ([#578](../../pull/578))
- Added support for creating Aperio svs files ([#580](../../pull/580))
- Added support for geospatial files with GCP ([#588](../../pull/588))

### Improvements
- More untiled tiff files are handles by the bioformats reader ([#569](../../pull/569))
- Expose a concurrent option on endpoints for converting images ([#583](../../pull/583))
- Better concurrency use in image conversion ([#587](../../pull/587))
- Handle more OME tiffs ([#585](../../pull/585), [#591](../../pull/591))
- Better memcached error logging ([#592](../../pull/592))

### Changes
- Exceptions on cached items are no longer within the KeyError context ([#584](../../pull/584))
- Simplified thumbnail generation by removing the level-0 option ([#593](../../pull/593))

### Bug Fixes
- Updated dependencies to work with changes to the nd2reader ([#596](../../pull/596))

## Version 1.4.3

### Improvements
- In Girder, prefer geospatial sources for geospatial data ([#564](../../pull/564))

### Bug Fixes
- The GDAL source failed when getting band ranges on non-integer data ([#565](../../pull/565))

## Version 1.4.2

### Features
- Added a Girder endpoint to get metadata on associated images ([#561](../../pull/561))
- Added an option to try all Girder items for use as large images ([#562](../../pull/562))

### Improvements
- Reduce gdal warning about projection strings ([#559](../../pull/559))
- Don't report needless frame information for some single frame files ([#558](../../pull/558))
- Send Backbone events on frame changes in the viewer ([#563](../../pull/563))

### Changes
- The PIL tilesource priority is slightly higher than other fallback sources ([#560](../../pull/560))

### Bug Fixes
- Fix compositing when using different frame numbers and partial tiles ([#557](../../pull/557))

## Version 1.4.1

### Features
- Multiple frames can be composited together with the style option ([#554](../../pull/554), [#556](../../pull/556))

### Improvements
- Warn when opening an inefficient tiff file ([#555](../../pull/555))

## Version 1.4.0

### Features
- Added a `canRead` method to the core module ([#512](../../pull/512))
- Image conversion supports JPEG 2000 (jp2k) compression ([#522](../../pull/522))
- Image conversion can now convert images readable by large_image sources but not by vips ([#529](../../pull/529))
- Added an `open` method to the core module as an alias to `getTileSource` ([#550](../../pull/550))
- Added an `open` method to each file source module ([#550](../../pull/550))
- Numerous improvement to image conversion ([#533](../../pull/533), [#535](../../pull/535), [#537](../../pull/537), [#541](../../pull/541), [#544](../../pull/544), [#545](../../pull/545), [#546](../../pull/546), [#549](../../pull/549))

### Improvements
- Better release bioformats resources ([#502](../../pull/502))
- Better handling of tiff files with JPEG compression and RGB colorspace ([#503](../../pull/503))
- The openjpeg tile source can decode with parallelism ([#511](../../pull/511))
- Geospatial tile sources are preferred for geospatial files ([#512](../../pull/512))
- Support decoding JP2k compressed tiles in the tiff tile source ([#514](../../pull/514))
- Hardened tests against transient timing issues ([#532](../../pull/532), [#536](../../pull/536))

### Changes
- The image conversion task has been split into two packages, large_image_converter and large_image_tasks.  The tasks module is used with Girder and Girder Worker for converting images and depends on the converter package.  The converter package can be used as a stand-alone command line tool ([#518](../../pull/518))

### Bug Fixes
- Harden updates of the item view after making a large image ([#508](../../pull/508), [#515](../../pull/515))
- Tiles in an unexpected color mode weren't consistently adjusted ([#510](../../pull/510))
- Harden trying to add an annotation before the viewer is ready ([#547](../../pull/547))
- Correctly report the tile size after resampling in the tileIterator ([#538](../../pull/538))

## Version 1.3.2

### Improvements
- Reduce caching associated images when the parent item changes ([#491](../../pull/491))
- Test with Python 3.9 ([#493](../../pull/493))
- Add a hideAnnotation function in the client ([#490](../../pull/490))
- Expose more resample options for region and histogram endpoints ([#496](../../pull/496))
- Improve OME tiff preferred level calculation for OME tiffs with subifds ([#496](../../pull/496))

### Changes
- Include the annotationType to the annotation conversion method in the client ([#490](../../pull/490))

### Notes
- This will be the last version to support Python 2.7 and 3.5.

## Version 1.3.1

### Improvements
- Include ETag support in some Girder rest requests to reduce data transfer ([#488](../../pull/488))

### Changes
- Don't let bioformats handle pngs ([#487](../../pull/487))

## Version 1.3.0

### Features
- Added bioformats tile source ([#463](../../pull/463))
- Handle OME Tiff files with sub-ifd images ([#469](../../pull/469))

### Improvements
- Expose more internal metadata ([#479](../../pull/479))
- Improve how Philips XML internal metadata is reported ([#475](../../pull/475))
- Show aperio version in internal metadata ([#474](../../pull/474))
- Add css classes to metadata on the item page ([#472](../../pull/472))
- The Girder web client exports the ItemViewWidget ([#483](../../pull/483))
- Read more associated images in openslide formats ([#486](../../pull/486))

### Bug Fixes
- Add a reference to updated time to avoid overcaching associated images ([#477](../../pull/477))
- Fix a typo in the settings page ([#473](../../pull/473))

## Version 1.2.0

### Features
- Added endpoints to remove old annotations ([#432](../../pull/432))
- Show auxiliary images and metadata on Girder item pages ([#457](../../pull/457))

### Improvements
- Migrate some database values on start to allow better annotation count reporting ([#431](../../pull/431))
- Speed up Girder item list annotation counts ([#454](../../pull/454))
- Read more OME Tiff files ([#450](../../pull/450))
- Handle subimages of different component depths ([#449](../../pull/449))
- When scaling, adjust reported mm_x/y ([#441](../../pull/441))

### Changes
- Standardize metadata for tile sources with multiple frames ([#433](../../pull/433))
- Unify code to check if a tile exists ([#462](../../pull/462))
- Switch to ElementTree, as cElementTree is deprecate ([#461](../../pull/461))
- Refactor how frame information is added to metadata ([#460](../../pull/460))
- Upgrade GeoJS to the latest version ([#451](../../pull/451))

### Bug Fixes
- Fix a threading issue with multiple styled tiles ([#444](../../pull/444))
- Guard against reading tiff tiles outside of the image ([#458](../../pull/458))
- Guard against a missing annotation value ([#456](../../pull/456)(
- Fix handling Girder filenames with multiple periods in a row ([#459](../../pull/459))
- Work around a file descriptor issue in cheroot ([#465](../../pull/465))

## Version 1.1.0

### Features
- Added nd2 tile source ([#419](../../pull/419))

### Bug Fixes
- Fixed an issue where, if users or groups were deleted outside of normal methods, checking an annotation's access would delete its elements ([#428](../../pull/428))
- Fix an issue where retiling some tile sources could fail ([#427](../../pull/427))

### Improvements
- Testing fully with Python 3.8 ([#429](../../pull/429))

## Version 1.0.4

### Bug Fixes
- Fixed an issue where retiling some tile sources could fail ([#427](../../pull/427))

## Version 1.0.3

### Features
- Added gdal tile source ([#418](../../pull/418))
- Added a GET large_image/sources endpoint to list versions of all installed sources ([#421](../../pull/421))

### Bug Fixes
- Fixed an issue where changing the annotation history setting when Girder's settings' cache was enable wouldn't take effect until after a restart ([#422](../../pull/422))
- Fixed an issue when used as a Girder plugin and served with a proxy with a prefix path ([#423](../../pull/423))

### Improvements
- Better handling of imported file formats with adjacent files ([#424](../../pull/424))

## Version 1.0.2

### Features
- Add style options for all tile sources to remap channels and colors ([#397](../../pull/397))
- Better support for high bit-depth images ([#397](../../pull/397))

### Improvements
- Make it easier to load the annotation-enable web viewers ([#402](../../pull/402))
- Improved support for z-loops in OMETiff files ([#397](../../pull/397))
- Support using Glymur 0.9.1 ([#411](../../pull/411))

### Bug Fixes
- Fixed an issue where a Girder image conversion task could raise an error about a missing file ([#409](../../pull/409))

## Version 1.0.1

### Features
- Get annotations elements by centroid ([#371](../../pull/371))
- Added an annotation badge to the image list ([#372](../../pull/372))
- Added openjpeg tile source ([#380](../../pull/380))
- Handle different tiff orientations in the tiff tile source ([#390](../../pull/390))

### Improvements
- Increased the annotation page limit ([#367](../../pull/367))
- Increased the annotations response time limit ([#389](../../pull/389))
- Improved handling of tiff files with multiple tiled images ([#373](../../pull/373))
- Don't reset backbone models on saving existing annotations ([#399](../../pull/399))

### Changes
- Use girder/large_image_wheels ([#384](../../pull/384))
- Changed the mapnik tile source style defaults ([#395](../../pull/395))

### Bug Fixes
- Fixed the pyproj minimum version ([#366](../../pull/366))
- Guard against GDAL open errors ([#375](../../pull/375))
- Better handle annotations with zero elements ([#398](../../pull/398))
- Sorting tile layers could use a dictionary comparison ([#396](../../pull/396))

## Version 1.0.0

This is a substantial refactor from preliminary versions.  Now that setuptools_scm is used for versioning, all merges to master are automatically published to pypi as development versions.

Tile sources are now fully modular and are installed via pip.  File extensions and mime type are now used as part of the order that tile sources are checked, giving more control over which tile source is used by default.

The Girder plugin has been divided into the parts requiring annotations and the parts that are only necessary for large images.

Python 3.4 support was dropped.
