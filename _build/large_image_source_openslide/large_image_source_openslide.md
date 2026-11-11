# large_image_source_openslide package

## Submodules

## large_image_source_openslide.girder_source module

### *class* large_image_source_openslide.girder_source.OpenslideGirderTileSource(\*args, \*\*kwargs)

Bases: [`OpenslideFileTileSource`](#large_image_source_openslide.OpenslideFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items with an SVS file or other files that
the openslide library can read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensionsWithAdjacentFiles *= {'dcm', 'dicom', 'mrxs'}*

#### mimeTypesWithAdjacentFiles *= {'application/dicom', 'image/mirax'}*

#### name *= 'openslide'*

## Module contents

### *class* large_image_source_openslide.OpenslideFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to SVS files and other files the openslide library can
read.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – a filesystem path for the tile source.

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'bif': SourcePriority.LOW, 'czi': SourcePriority.PREFERRED, 'dcm': SourcePriority.MEDIUM, 'ini': SourcePriority.LOW, 'mrxs': SourcePriority.PREFERRED, 'ndpi': SourcePriority.PREFERRED, 'scn': SourcePriority.LOW, 'svs': SourcePriority.HIGH, 'svslide': SourcePriority.PREFERRED, 'tif': SourcePriority.MEDIUM, 'tiff': SourcePriority.MEDIUM, 'vms': SourcePriority.HIGH, 'vmu': SourcePriority.HIGH, None: SourcePriority.MEDIUM}*

#### getAssociatedImagesList()

Get a list of all associated images.

* **Returns:**
  the list of image keys.

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### getNativeMagnification()

Get the magnification at a particular level.

* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

#### getPreferredLevel(level)

Given a desired level (0 is minimum resolution, self.levels - 1 is max
resolution), return the level that contains actual data that is no
lower resolution.

* **Parameters:**
  **level** – desired level
* **Returns level:**
  a level with actual data that is no lower resolution.

#### getTile(x, y, z, pilImageAllowed=False, numpyAllowed=False, \*\*kwargs)

Get a tile from a tile source, returning it as an binary image, a PIL
image, or a numpy array.

* **Parameters:**
  * **x** – the 0-based x position of the tile on the specified z level.
    0 is left.
  * **y** – the 0-based y position of the tile on the specified z level.
    0 is top.
  * **z** – the z level of the tile.  May range from [0, self.levels],
    where 0 is the lowest resolution, single tile for the whole source.
  * **pilImageAllowed** – True if a PIL image may be returned.
  * **numpyAllowed** – True if a numpy image may be returned.  ‘always’
    to return a numpy array.
  * **sparseFallback** – if False and a tile doesn’t exist, raise an
    error.  If True, check if a lower resolution tile exists, and, if
    so, interpolate the needed data for this tile.
  * **frame** – the frame number within the tile source.  None is the
    same as 0 for multi-frame sources.
* **Returns:**
  either a numpy array, a PIL image, or a memory object with an
  image file.

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'application/dicom': SourcePriority.MEDIUM, 'image/czi': SourcePriority.PREFERRED, 'image/mirax': SourcePriority.PREFERRED, 'image/tiff': SourcePriority.MEDIUM, 'image/x-tiff': SourcePriority.MEDIUM, None: SourcePriority.FALLBACK}*

#### name *= 'openslide'*

### large_image_source_openslide.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_openslide.open(\*args, \*\*kwargs)

Create an instance of the module class.
