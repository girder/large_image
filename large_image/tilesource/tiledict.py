import numpy
import PIL
import PIL.Image
import PIL.ImageColor
import PIL.ImageDraw

from .. import exceptions
from ..constants import TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL
from .utilities import _encodeImage, _imageToNumpy, _imageToPIL


class LazyTileDict(dict):
    """
    Tiles returned from the tile iterator and dictionaries of information with
    actual image data in the 'tile' key and the format in the 'format' key.
    Since some applications need information about the tile but don't need the
    image data, these two values are lazily computed.  The LazyTileDict can be
    treated like a regular dictionary, except that when either of those two
    keys are first accessed, they will cause the image to be loaded and
    possibly converted to a PIL image and cropped.

    Unless setFormat is called on the tile, tile images may always be returned
    as PIL images.
    """

    def __init__(self, tileInfo, *args, **kwargs):
        """
        Create a LazyTileDict dictionary where there is enough information to
        load the tile image.  ang and kwargs are as for the dict() class.

        :param tileInfo: a dictionary of x, y, level, format, encoding, crop,
            and source, used for fetching the tile image.
        """
        self.x = tileInfo['x']
        self.y = tileInfo['y']
        self.frame = tileInfo.get('frame')
        self.level = tileInfo['level']
        self.format = tileInfo['format']
        self.encoding = tileInfo['encoding']
        self.crop = tileInfo['crop']
        self.source = tileInfo['source']
        self.resample = tileInfo.get('resample', False)
        self.requestedScale = tileInfo.get('requestedScale')
        self.metadata = tileInfo.get('metadata')
        self.retile = tileInfo.get('retile') and self.metadata

        self.deferredKeys = ('tile', 'format')
        self.alwaysAllowPIL = True
        self.imageKwargs = {}
        self.loaded = False
        result = super().__init__(*args, **kwargs)
        # We set this initially so that they are listed in known keys using the
        # native dictionary methods
        self['tile'] = None
        self['format'] = None
        self.width = self['width']
        self.height = self['height']
        return result

    def setFormat(self, format, resample=False, imageKwargs=None):
        """
        Set a more restrictive output format for a tile, possibly also resizing
        it via resampling.  If this is not called, the tile may either be
        returned as one of the specified formats or as a PIL image.

        :param format: a tuple or list of allowed formats.  Formats are members
            of TILE_FORMAT_*.  This will avoid converting images if they are
            in the desired output encoding (regardless of subparameters).
        :param resample: if not False or None, allow resampling.  Once turned
            on, this cannot be turned off on the tile.
        :param imageKwargs: additional parameters that should be passed to
            _encodeImage.
        """
        # If any parameters are changed, mark the tile as not loaded, so that
        # referring to a deferredKey will reload the image.
        self.alwaysAllowPIL = False
        if format is not None and format != self.format:
            self.format = format
            self.loaded = False
        if (resample not in (False, None) and not self.resample and
                self.requestedScale and round(self.requestedScale, 2) != 1.0):
            self.resample = resample
            self['scaled'] = 1.0 / self.requestedScale
            self['tile_x'] = self.get('tile_x', self['x'])
            self['tile_y'] = self.get('tile_y', self['y'])
            self['tile_width'] = self.get('tile_width', self.width)
            self['tile_height'] = self.get('tile_width', self.height)
            if self.get('magnification', None):
                self['tile_magnification'] = self.get('tile_magnification', self['magnification'])
            self['tile_mm_x'] = self.get('mm_x')
            self['tile_mm_y'] = self.get('mm_y')
            self['x'] = float(self['tile_x'])
            self['y'] = float(self['tile_y'])
            # Add provisional width and height
            if self.resample not in (False, None) and self.requestedScale:
                self['width'] = max(1, int(
                    self['tile_width'] / self.requestedScale))
                self['height'] = max(1, int(
                    self['tile_height'] / self.requestedScale))
                if self.get('tile_magnification', None):
                    self['magnification'] = self['tile_magnification'] / self.requestedScale
                if self.get('tile_mm_x', None):
                    self['mm_x'] = self['tile_mm_x'] * self.requestedScale
                if self.get('tile_mm_y', None):
                    self['mm_y'] = self['tile_mm_y'] * self.requestedScale
            # If we can resample the tile, many parameters may change once the
            # image is loaded.  Don't include width and height in this list;
            # the provisional values are sufficient.
            self.deferredKeys = ('tile', 'format')
            self.loaded = False
        if imageKwargs is not None:
            self.imageKwargs = imageKwargs
            self.loaded = False

    def _retileTile(self):
        """
        Given the tile information, create a numpy array and merge multiple
        tiles together to form a tile of a different size.
        """
        retile = None
        xmin = int(max(0, self['x'] // self.metadata['tileWidth']))
        xmax = int((self['x'] + self.width - 1) // self.metadata['tileWidth'] + 1)
        ymin = int(max(0, self['y'] // self.metadata['tileHeight']))
        ymax = int((self['y'] + self.height - 1) // self.metadata['tileHeight'] + 1)
        for x in range(xmin, xmax):
            for y in range(ymin, ymax):
                tileData = self.source.getTile(
                    x, y, self.level,
                    numpyAllowed='always', sparseFallback=True, frame=self.frame)
                tileData, _ = _imageToNumpy(tileData)
                if retile is None:
                    retile = numpy.zeros(
                        (self.height, self.width) if len(tileData.shape) == 2 else
                        (self.height, self.width, tileData.shape[2]),
                        dtype=tileData.dtype)
                x0 = int(x * self.metadata['tileWidth'] - self['x'])
                y0 = int(y * self.metadata['tileHeight'] - self['y'])
                if x0 < 0:
                    tileData = tileData[:, -x0:]
                    x0 = 0
                if y0 < 0:
                    tileData = tileData[-y0:, :]
                    y0 = 0
                tileData = tileData[:min(tileData.shape[0], self.height - y0),
                                    :min(tileData.shape[1], self.width - x0)]
                retile[y0:y0 + tileData.shape[0], x0:x0 + tileData.shape[1]] = tileData[
                    :, :, :retile.shape[2]]
        return retile

    def __getitem__(self, key, *args, **kwargs):
        """
        If this is the first time either the tile or format key is requested,
        load the tile image data.  Otherwise, just return the internal
        dictionary result.

        See the base dict class for function details.
        """
        if not self.loaded and key in self.deferredKeys:
            # Flag this immediately to avoid recursion if we refer to the
            # tile's own values.
            self.loaded = True

            if not self.retile:
                tileData = self.source.getTile(
                    self.x, self.y, self.level,
                    pilImageAllowed=True, numpyAllowed=True,
                    sparseFallback=True, frame=self.frame)
                if self.crop:
                    tileData, _ = _imageToNumpy(tileData)
                    tileData = tileData[self.crop[1]:self.crop[3], self.crop[0]:self.crop[2]]
            else:
                tileData = self._retileTile()

            pilData = _imageToPIL(tileData)

            # resample if needed
            if self.resample not in (False, None) and self.requestedScale:
                self['width'] = max(1, int(
                    pilData.size[0] / self.requestedScale))
                self['height'] = max(1, int(
                    pilData.size[1] / self.requestedScale))
                pilData = tileData = pilData.resize(
                    (self['width'], self['height']),
                    resample=PIL.Image.LANCZOS if self.resample is True else self.resample)

            tileFormat = (TILE_FORMAT_PIL if isinstance(tileData, PIL.Image.Image)
                          else (TILE_FORMAT_NUMPY if isinstance(tileData, numpy.ndarray)
                                else TILE_FORMAT_IMAGE))
            tileEncoding = None if tileFormat != TILE_FORMAT_IMAGE else (
                'JPEG' if tileData[:3] == b'\xff\xd8\xff' else
                'PNG' if tileData[:4] == b'\x89PNG' else
                'TIFF' if tileData[:4] == b'II\x2a\x00' else
                None)
            # Reformat the image if required
            if (not self.alwaysAllowPIL or
                    (TILE_FORMAT_NUMPY in self.format and isinstance(tileData, numpy.ndarray))):
                if (tileFormat in self.format and (tileFormat != TILE_FORMAT_IMAGE or (
                        tileEncoding and
                        tileEncoding == self.imageKwargs.get('encoding', self.encoding)))):
                    # already in an acceptable format
                    pass
                elif TILE_FORMAT_NUMPY in self.format:
                    tileData, _ = _imageToNumpy(tileData)
                    tileFormat = TILE_FORMAT_NUMPY
                elif TILE_FORMAT_PIL in self.format:
                    tileData = pilData
                    tileFormat = TILE_FORMAT_PIL
                elif TILE_FORMAT_IMAGE in self.format:
                    tileData, mimeType = _encodeImage(
                        tileData, **self.imageKwargs)
                    tileFormat = TILE_FORMAT_IMAGE
                if tileFormat not in self.format:
                    raise exceptions.TileSourceError(
                        'Cannot yield tiles in desired format %r' % (
                            self.format, ))
            else:
                tileData = pilData
                tileFormat = TILE_FORMAT_PIL

            self['tile'] = tileData
            self['format'] = tileFormat
        return super().__getitem__(key, *args, **kwargs)
