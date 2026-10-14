# large_image_source_bioformats package

## Submodules

## large_image_source_bioformats.girder_source module

### *class* large_image_source_bioformats.girder_source.BioformatsGirderTileSource(\*args, \*\*kwargs)

Bases: [`BioformatsFileTileSource`](#large_image_source_bioformats.BioformatsFileTileSource), [`GirderTileSource`](../girder_large_image/girder_large_image.md#girder_large_image.girder_tilesource.GirderTileSource)

Provides tile access to Girder items that can be read with bioformats.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – the associated file path.

#### cacheName *= 'tilesource'*

#### mayHaveAdjacentFiles(largeImageFile)

#### name *= 'bioformats'*

## Module contents

### *class* large_image_source_bioformats.BioformatsFileTileSource(\*args, \*\*kwargs)

Bases: [`FileTileSource`](../large_image/large_image.tilesource.md#large_image.tilesource.base.FileTileSource)

Provides tile access to via Bioformats.

Initialize the tile class.  See the base class for other available
parameters.

* **Parameters:**
  **path** – the associated file path.

#### *classmethod* addKnownExtensions()

#### cacheName *= 'tilesource'*

#### extensions *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'czi': SourcePriority.HIGH, 'ets': SourcePriority.LOW, 'lif': SourcePriority.MEDIUM, 'vsi': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### getAssociatedImagesList()

Return a list of associated images.

* **Returns:**
  the list of image keys.

#### getInternalMetadata(\*\*kwargs)

Return additional known metadata about the tile source.  Data returned
from this method is not guaranteed to be in any particular format or
have specific values.

* **Returns:**
  a dictionary of data or None.

#### getMetadata()

Return a dictionary of metadata containing levels, sizeX, sizeY,
tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

* **Returns:**
  metadata dictionary.

#### getNativeMagnification()

Get the magnification at a particular level.

* **Returns:**
  magnification, width of a pixel in mm, height of a pixel in mm.

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

#### mimeTypes *: dict[str | None, [SourcePriority](../large_image/large_image.md#large_image.constants.SourcePriority)]* *= {'image/czi': SourcePriority.HIGH, 'image/vsi': SourcePriority.PREFERRED, None: SourcePriority.FALLBACK}*

#### name *= 'bioformats'*

### large_image_source_bioformats.canRead(\*args, \*\*kwargs)

Check if an input can be read by the module class.

### large_image_source_bioformats.open(\*args, \*\*kwargs)

Create an instance of the module class.
