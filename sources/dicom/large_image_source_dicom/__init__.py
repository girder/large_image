import math
import os
import warnings

import numpy

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import _imageToNumpy, _imageToPIL

wsidicom = None

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _importlib_version
except ImportError:
    from importlib_metadata import PackageNotFoundError
    from importlib_metadata import version as _importlib_version
try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


def _lazyImport():
    """
    Import the wsidicom module.  This is done when needed rather than in the
    module initialization because it is slow.
    """
    global wsidicom

    if wsidicom is None:
        try:
            import wsidicom
        except ImportError:
            raise TileSourceError('nd2 module not found.')
        warnings.filterwarnings('ignore', category=UserWarning, module='wsidicom')
        warnings.filterwarnings('ignore', category=UserWarning, module='pydicom')


class DICOMFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to dicom files the dicom or dicomreader library can read.
    """

    cacheName = 'tilesource'
    name = 'dicom'
    extensions = {
        None: SourcePriority.LOW,
        'dcm': SourcePriority.PREFERRED,
        'dic': SourcePriority.PREFERRED,
        'dicom': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'application/dicom': SourcePriority.PREFERRED,
    }

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        # We want to make a list of paths of files in this item, if multiple,
        # or adjacent items in the folder if the item is a single file.  We
        # filter files with names that have a preferred extension.
        path = self._getLargeImagePath()
        if not isinstance(path, list):
            path = str(path)
            if not os.path.isfile(path):
                raise TileSourceFileNotFoundError(path) from None
            root = os.path.dirname(path)
            self._largeImagePath = [
                os.path.join(root, entry) for entry in os.listdir(root)
                if os.path.isfile(os.path.join(root, entry)) and
                os.path.splitext(entry)[-1][1:] in self.extensions]
            if path not in self._largeImagePath:
                self._largeImagePath = [path]
            # TODO: fail if this file is level-(n) and a file that is
            # level-(n-1) exists
        else:
            self._largeImagePath = path
        _lazyImport()
        try:
            self._dicom = wsidicom.WsiDicom.open(self._largeImagePath)
        except Exception:
            raise TileSourceError('File cannot be opened via dicom tile source.')
        self.sizeX = int(self._dicom.image_size.width)
        self.sizeY = int(self._dicom.image_size.height)
        self.tileWidth = int(self._dicom.tile_size.width)
        self.tileHeight = int(self._dicom.tile_size.height)
        self.levels = int(max(1, math.ceil(math.log(
            float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1))

    def __del__(self):
        if getattr(self, '_dicom', None) is not None:
            try:
                self._dicom.close()
            finally:
                self._dicom = None

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = mm_y = None
        try:
            mm_x = self._dicom.base_level.pixel_spacing.width or None
            mm_y = self._dicom.base_level.pixel_spacing.height or None
        except Exception:
            pass
        # Estimate the magnification; we don't have a direct value
        mag = 0.01 / mm_x if mm_x else None
        return {
            'magnification': mag,
            'mm_x': mm_x,
            'mm_y': mm_y,
        }

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        frame = self._getFrame(**kwargs)
        self._xyzInRange(x, y, z, frame)
        x0, y0, x1, y1, step = self._xyzToCorners(x, y, z)
        bw = self.tileWidth * step
        bh = self.tileHeight * step
        level = 0
        levelfactor = 1
        basefactor = self._dicom.base_level.pixel_spacing.width
        for checklevel in range(1, len(self._dicom.levels)):
            factor = round(self._dicom.levels[checklevel].pixel_spacing.width / basefactor)
            if factor <= step:
                level = checklevel
                levelfactor = factor
            else:
                break
        x0f = int(x0 // levelfactor)
        y0f = int(y0 // levelfactor)
        x1f = min(int(math.ceil(x1 / levelfactor)), self._dicom.levels[level].size.width)
        y1f = min(int(math.ceil(y1 / levelfactor)), self._dicom.levels[level].size.height)
        bw = int(bw // levelfactor)
        bh = int(bh // levelfactor)
        tile = self._dicom.read_region(
            (x0f, y0f), self._dicom.levels[level].level, (x1f - x0f, y1f - y0f))
        format = TILE_FORMAT_PIL
        if tile.width < bw or tile.height < bh:
            tile = _imageToNumpy(tile)[0]
            tile = numpy.pad(
                tile,
                ((0, bh - tile.shape[0]), (0, bw - tile.shape[1]), (0, 0)),
                'constant', constant_values=0)
            tile = _imageToPIL(tile)
        if bw > self.tileWidth or bh > self.tileHeight:
            tile = tile.resize((self.tileWidth, self.tileHeight))
        return self._outputTile(tile, format, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)

    def getAssociatedImagesList(self):
        """
        Return a list of associated images.

        :return: the list of image keys.
        """
        return [key for key in ['label', 'macro'] if self._getAssociatedImage(key)]

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        keyMap = {
            'label': 'read_label',
            'macro': 'read_overview',
        }
        try:
            return getattr(self._dicom, keyMap[imageKey])()
        except Exception:
            return None


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return DICOMFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return DICOMFileTileSource.canRead(*args, **kwargs)
