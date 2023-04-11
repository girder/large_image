import math
import os
import re
import warnings
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _importlib_version

import numpy

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import _imageToNumpy, _imageToPIL

pydicom = None
wsidicom = None

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
    global pydicom

    if wsidicom is None:
        try:
            import pydicom
            import wsidicom
        except ImportError:
            raise TileSourceError('dicom modules not found.')
        warnings.filterwarnings('ignore', category=UserWarning, module='wsidicom')
        warnings.filterwarnings('ignore', category=UserWarning, module='pydicom')


def dicom_to_dict(ds, base=None):
    """
    Convert a pydicom dataset to a fairly flat python dictionary for purposes
    of reporting.  This is not invertable without extra work.

    :param ds: a pydicom dataset.
    :param base: a base dataset entry within the dataset.
    :returns: a dictionary of values.
    """
    if base is None:
        base = ds.to_json_dict(
            bulk_data_threshold=0,
            bulk_data_element_handler=lambda x: '<%s bytes>' % len(x.value))
    info = {}
    for k, v in base.items():
        key = k
        try:
            key = pydicom.datadict.keyword_for_tag(k)
        except Exception:
            pass
        if v.get('vr') in {None, 'OB'}:
            continue
        if not len(v.get('Value', [])):
            continue
        if isinstance(v['Value'][0], dict):
            val = [dicom_to_dict(ds, entry) for entry in v['Value']]
        elif len(v['Value']) == 1:
            val = v['Value'][0]
        else:
            val = v['Value']
        info[key] = val
    return info


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

    _minTileSize = 64
    _maxTileSize = 4096

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
                self._pathMightBeDicom(entry)]
            if path not in self._largeImagePath:
                self._largeImagePath = [path]
        else:
            self._largeImagePath = path
        _lazyImport()
        try:
            self._dicom = wsidicom.WsiDicom.open(self._largeImagePath)
        except Exception:
            raise TileSourceError('File cannot be opened via dicom tile source.')
        self.sizeX = int(self._dicom.size.width)
        self.sizeY = int(self._dicom.size.height)
        self.tileWidth = int(self._dicom.tile_size.width)
        self.tileHeight = int(self._dicom.tile_size.height)
        self.tileWidth = min(max(self.tileWidth, self._minTileSize), self._maxTileSize)
        self.tileHeight = min(max(self.tileHeight, self._minTileSize), self._maxTileSize)
        self.levels = int(max(1, math.ceil(math.log(
            max(self.sizeX / self.tileWidth, self.sizeY / self.tileHeight)) / math.log(2)) + 1))

    def __del__(self):
        if getattr(self, '_dicom', None) is not None:
            try:
                self._dicom.close()
            finally:
                self._dicom = None

    def _pathMightBeDicom(self, path):
        """
        Return True if the path looks like it might be a dicom file based on
        its name or extension.

        :param path: the path to check.
        :returns: True if this might be a dicom, False otherwise.
        """
        path = os.path.basename(path)
        if os.path.splitext(path)[-1][1:] in self.extensions:
            return True
        if re.match(r'^([1-9][0-9]*|0)(\.([1-9][0-9]*|0))+$', path) and len(path) <= 64:
            return True
        return False

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = mm_y = None
        try:
            mm_x = self._dicom.levels[0].pixel_spacing.width or None
            mm_y = self._dicom.levels[0].pixel_spacing.height or None
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
        idx = 0
        for level in self._dicom.levels:
            for ds in level.datasets:
                result.setdefault('dicom', {})
                info = dicom_to_dict(ds)
                if not idx:
                    result['dicom'] = info
                else:
                    for k, v in info.items():
                        if k not in result['dicom'] or v != result['dicom'][k]:
                            result['dicom']['%s:%d' % (k, idx)] = v
                idx += 1
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
        basefactor = self._dicom.levels[0].pixel_spacing.width
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
