# Change Log

## 1.19.3

### Improvements
- Speed up rendering Girder item page metadata in some instances ([#1031](../../pull/1031))

### Bug Fixes
- Fix an issue with non-square tiles in the multi source ([#1032](../../pull/1032))

## 1.19.2

### Improvements
- Better parse svs pixel size in tiff and tifffile sources ([#1021](../../pull/1021))
- Add geojson to known mime types ([#1022](../../pull/1022))
- Handle upcoming matplotlib deprecations ([#1025](../../pull/1025))
- Handle upcoming numpy deprecations ([#1026](../../pull/1026))

## 1.19.1

### Improvements
- Improve tifffile associated image detection ([#1019](../../pull/1019))

## 1.19.0

### Features
- Add a frames property to the tile source as a short hand for getting the number of frames from the metadata ([#1014](../../pull/1014))

### Improvements
- Better release file handles ([#1007](../../pull/1007))
- Support tiny images from the test source ([#1013](../../pull/1013))
- Speed up loading or parsing some multi sources ([#1015](../../pull/1015))
- Better scale uint32 images ([#1017](../../pull/1017))

### Changes
- Don't report filename in internal PIL metadata ([#1006](../../pull/1006))

### Bug Fixes
- Better output new vips images as float32 ([#1016](../../pull/1016))
- Pin tinycolor2 for annotations ([#1018](../../pull/1018))

## 1.18.0

### Features
- Add a DICOM tile source ([#1005](../../pull/1005))

### Improvements
- Better control dtype on multi sources ([#993](../../pull/993))
- Don't use dask threads when using nd2 to fetch tiles ([#994](../../pull/994))
- Set mime type for imported girder files ([#995](../../pull/995))
- Specify token scopes for girder endpoints ([#999](../../pull/999), [#1000](../../pull/1000))
- Set the qptiff extension to prefer the tiff reader ([#1003](../../pull/1003))

### Bug Fixes
- Use open.read rather than download to access files in Girder ([#989](../../pull/989))
- Fix nd2 source scale ([#990](../../pull/990))

## 1.17.3

### Changes
- Test on Python 3.11 ([#986](../../pull/986))

## 1.17.2

### Bug Fixes
- Fixed overcaching annotations ([#983](../../pull/983))
- Depending on timing, annotations could be inappropriately paged ([#984](../../pull/984))

## 1.17.1

### Improvements
- Fallback when server notification streams are turned off ([#967](../../pull/967))
- Show and edit yaml and json files using codemirror ([#969](../../pull/969), [#971](../../pull/971))
- Show configured item lists even if there are no large images ([#972](../../pull/972))
- Add metadata and annotation metadata search modes to Girder ([#974](../../pull/974))
- Add the ability to show annotation metadata in item annotation lists ([#977](../../pull/977))
- Support ETAG in annotation rest responses for better browser caching ([#978](../../pull/978))
- Thumbnail maintenance endpoints ([#980](../../pull/980))
- Handle lif file extensions ([#981](../../pull/981))

### Bug Fixes
- Fixed an issue with compositing multiple frames ([#982](../../pull/982))

## 1.17.0

### Features
- Style functions ([#960](../../pull/960))
- Annotation metadata endpoints ([#963](../../pull/963))

### Improvements
- Reduce rest calls to get settings ([#953](../../pull/953))
- Add an endpoint to delete all annotations in a folder ([#954](../../pull/954))
- Support relabeling axes in the multi source ([#957](../../pull/957))
- Reduce a restriction on reading some tiff files ([#958](../../pull/958))

### Changes
- Improve internals for handling large annotation elements ([#961](../../pull/961))

### Bug Fixes
- Harden adding images to the item list ([#955](../../pull/955))
- Fix checking user annotation document length ([#956](../../pull/956))
- Improve scaled overlays ([#959](../../pull/959))

## 1.16.2

### Improvements
- Add a general filter control to item lists ([#938](../../pull/938), [#941](../../pull/941))
- Item list modal dialogs are wider ([#939](../../pull/939))
- Improve mimetypes on upload to Girder ([#944](../../pull/944))

### Bug Fixes
- Fix iterating tiles where the overlap larger than the tile size ([#940](../../pull/940))
- Better ignore tiff directories that aren't part of the pyramid ([#943](../../pull/943))
- Fix an issue with styling frames in ome tiffs ([#945](../../pull/945))
- Better handle large user records in annotation elements ([#949](../../pull/949))
- Harden which output formats are supported ([#950](../../pull/950))

### Changes
- Adjusted rest request logging rates for region endpoint ([#948](../../pull/948))

## 1.16.1

### Improvements
- Add annotation access controls at the folder level ([#905](../../pull/905))
- Reduce error messages and make canRead results more accurate ([#918](../../pull/918), [#919](../../pull/919), [#920](../../pull/920))
- Sort columns in item lists based ([#925](../../pull/925), [#928](../../pull/928))
- Better handle tiffs with orientation flags in pil source ([#924](../../pull/924))
- Support a bands parameter for the test source ([#935](../../pull/935))
- Add annotation creation access flag ([#937](../../pull/937))

### Changes
- Remove some extraneous values from metadata responses ([#932](../../pull/932))
- Reduce some messages to stderr from other libraries ([#919](../../pull/919))
- Avoid some warnings in Python 3.10 ([#913](../../pull/913))

## 1.16.0

### Features
- Add a tifffile tile source ([#885](../../pull/885), [#896](../../pull/896), [#903](../../pull/903))
- Added a canReadList method to large_image to show which source can be used ([#895](../../pull/895))
- Optionally show metadata in item lists ([#901](../../pull/901))
- Register the tile output formats from PIL ([#904](../../pull/904))
- Copy tilesource instances to add styles ([#894](../../pull/894))

### Improvements
- Pass options to the annotationLayer mode ([#881](../../pull/881))
- Support more style range options ([#883](../../pull/883))
- When converting girder images locally, prefer mount paths ([#886](../../pull/886))
- Store the id of job results for easier post-job work ([#887](../../pull/887))
- Harden style compositing of partial tiles ([#889](../../pull/889))
- Cache read_tiff calls to speed up restyling ([#891](../../pull/891))
- Speed up styling by doing less ([#892](../../pull/892))
- Add local color definitions ([#858](../../pull/858))
- Inheritable config files ([#897](../../pull/897))
- Add geospatial property ([#818](../../pull/818), [#908](../../pull/908))
- Improve repr of image bytes ([#902](../../pull/902))
- Handle nodata style when specified as a string ([#914](../../pull/914))

### Changes
- Be more consistent in source class name attribute assignment ([#884](../../pull/884))

### Bug Fixes
- Fix alpha on GDAL sources with a projection that have an explicit alpha channel ([#909](../../pull/909), [#915](../../pull/915))

## 1.15.1

### Improvements
- When scaling heatmap annoations, use an appropriate value ([#878](../../pull/878))
- Use the girder client build time for cache control ([#879](../../pull/879))

## 1.15.0

### Features
- Abstract caching and support entrypoints ([#876](../../pull/876))

### Bug Fixes
- Fix getPixel for single channel sources ([#875](../../pull/875))

## 1.14.5

### Improvements
- Speed up ingesting annotations ([#870](../../pull/870))
- Reduce the chance of blinking on annotation layers ([#871](../../pull/871))
- Reduce updates when modifying annotations ([#872](../../pull/872))

### Bug Fixes
- Improve annotation upload; support full annotation documents ([#869](../../pull/869))

## 1.14.4

### Improvements
- Better handle editing polygons with holes ([#857](../../pull/857))
- Support fetching yaml config files ([#860](../../pull/860))
- Optionally include bounding box information with annotation queries ([#851](../../pull/851))
- Reduce memory copying in the nd2 reader ([#853](../../pull/853))
- Add support for boolean annotation operations ([#865](../../pull/865))
- Speed up removing all annotations from an item ([#863](../../pull/863))

### Bug Fixes
- Fix issues with the nd2 reader ([#866](../../pull/866), [#867](../../pull/867))
- Honor the highlight size limit with centroid annotations ([#861](../../pull/861))

## 1.14.3

### Improvements
- Support polygon annotations with holes ([#844](../../pull/844))
- New annotations get a default name if they do not have one ([#843](../../pull/843))
- Explicitly mark vips output as tiled ([#848](../../pull/848))
- Change how annotations are uploaded from the UI ([#845](../../pull/845))

## 1.14.2

### Improvements
- Improve handling for vips pixel formats in addTile ([#838](../../pull/838))
- Add validateCOG method to GDALFileTileSource ([#835](../../pull/835))

### Changes
- The default logger now uses the null handler ([#840](../../pull/840))

## 1.14.1

### Changes
- The sources extra_installs didn't include all sources ([#833](../../pull/833))

## 1.14.0

### Features
- Vips tile source and tiled file writer ([#816](../../pull/816), [#827](../../pull/827), [#830](../../pull/830))

### Improvements
- Handle file URLs with GDAL ([#820](../../pull/820))
- Add a hasAlpha flag to image annotations ([#823](../../pull/823))
- Allow dict for style ([#817](../../pull/817))
- Support drawing multipolygon regions ([#832](../../pull/832))

### Bug Fixes
- Fix a range check for pixelmap annotations ([#815](../../pull/815))
- Harden checking if a PIL Image can be read directly from a file pointer ([#822](../../pull/822))

### Changes
- Handle PIL deprecations ([#824](../../pull/824))

## Version 1.13.0

### Features
- Add support for ellipse and circle annotations ([#811](../../pull/811))
- Support pickle output of numpy arrays for region, thumbnail, and tile_frames endpoints ([#812](../../pull/812))

### Improvements
- Improve parsing OME TIFF channel names ([#806](../../pull/806))
- Improve handling when a file vanishes ([#807](../../pull/807))
- Add TileSourceXYZRangeError ([#809](../../pull/809))

## Version 1.12.0

### Features
- Refactor the nd2 source to use the nd2 library ([#797](../../pull/797))

### Improvements
- Add options to threshold near min/max based on the histogram ([#798](../../pull/798))
- Mark vsi extensions as being preferred by the bioformats source ([#793](../../pull/793))
- Add mouse events to overlay annotations ([#794](../../pull/794))
- Use orjson instead of ujson for annotations ([#802](../../pull/802))
- Use simplejpeg for jpeg encoding rather than PIL ([#800](../../pull/800))
- Use pylibtiff instead of libtiff ([#799](../../pull/799))

### Bug Fixes
- Harden annotation ACL migration code ([#804](../../pull/804))

## Version 1.11.2

### Improvements
- Emit events when an overlay annotation layer is created ([#787](../../pull/787))
- Minor improvements to setFrameQuad to make it more flexible ([#790](../../pull/790))
- Support drawing polygon selection regions ([#791](../../pull/791))
- Add some automating options to getTileFramesQuadInfo  ([#792](../../pull/792))

### Changes
- Change how we do a version check ([#785](../../pull/785))

## Version 1.11.1

### Improvements
- Add options to get frame quad info from python ([#783](../../pull/783))

## Version 1.11.0

### Improvements
- Release memory associated with a lazy tile if it has been loaded ([#780](../../pull/780))

### Bug Fixes
- Tile overlaps on subset regions could be wrong ([#781](../../pull/781))

## Version 1.11.0

### Features
- Initial implementation of multi-source tile source ([#764](../../pull/764))
- Added pixelmap annotation element ([#767](../../pull/767), [#776](../../pull/776))

### Improvements
- Add more opacity support for image overlays ([#761](../../pull/761))
- Make annotation schema more uniform ([#763](../../pull/763))
- Improve TileSource class repr ([#765](../../pull/765))
- Improve frame slider response with base quads ([#771](../../pull/771))
- Default to nearest-neighbor scaling in lossless image conversion ([#772](../../pull/772))
- Improve the import time ([#775](../../pull/775), [#777](../../pull/777))

### Bug Fixes
- The tile iterator could return excess tiles with overlap ([#773](../../pull/773))

## Version 1.10.0

### Features
- Added image annotation element ([#742](../../pull/742), [#750](../../pull/750))
- Allow the discrete scheme to be used on all tile sources  ([#755](../../pull/755))

### Improvements
- Expand user paths ([#746](../../pull/746))
- Work with more matplotlib palettes ([#760](../../pull/760))

### Changes
- Use importlib rather than pkg_resources internally ([#747](../../pull/747), [#778](../../pull/778))

### Bug Fixes
- Fix expanding a style palette with a single named color ([#754](../../pull/754))

## Version 1.9.0

### Features
- Better palette support in styles ([#724](../../pull/724))
- Enumerate available palettes ([#741](../../pull/741))

### Improvements
- The openjpeg girder source handles uploaded files better ([#721](../../pull/721))
- Suppress some warnings on Girder and on bioformats ([#727](../../pull/727))

### Bug Fixes
- Harden detecting file-not-found ([#726](../../pull/726))
- Fix the pylibmc dependency for windows ([#725](../../pull/725))

## Version 1.8.11

### Changes
- Reduce extraneous files in large_image distribution ([#718](../../pull/718))

## Version 1.8.10

### Changes
- Improve library dependencies in setup.py ([#710](../../pull/710), [#715](../../pull/715))

## Version 1.8.9

### Changes
- Include the converter in the girder tasks dependency ([#707](../../pull/707))

## Version 1.8.8

### Changes
- Some log levels have been adjusted ([#689](../../pull/689), [#695](../../pull/695))

## Version 1.8.7

### Improvements
- Add the image converter to the extra requires ([#677](../../pull/677))
- All file tile sources can take either strings or pathlib.Path values ([#683](../../pull/683))
- On Girder with read-only assetstores, return results even if caching fails ([#684](../../pull/684))
- Handle geospatial files with no explicit projection ([#686](../../pull/686))

### Bug Fixes
- Fix default properties on annotations when emitted as centroids ([#687](../../pull/687))

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
