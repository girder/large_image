import math
import os
import threading
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _importlib_version

import numpy as np
import packaging.version
import zarr

import large_image
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_NUMPY, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource
from large_image.tilesource.utilities import nearPowerOfTwo

try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


class ZarrFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to files that the zarr library can read.
    """

    cacheName = 'tilesource'
    name = 'zarr'
    extensions = {
        None: SourcePriority.LOW,
        'zarr': SourcePriority.PREFERRED,
        'zgroup': SourcePriority.PREFERRED,
        'zattrs': SourcePriority.PREFERRED,
        'db': SourcePriority.MEDIUM,
    }

    _tileSize = 512
    _minTileSize = 128
    _maxTileSize = 1024
    _minAssociatedImageSize = 64
    _maxAssociatedImageSize = 8192

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = str(self._getLargeImagePath())
        self._zarr = None
        if not os.path.isfile(self._largeImagePath) and '//:' not in self._largeImagePath:
            raise TileSourceFileNotFoundError(self._largeImagePath) from None
        try:
            self._zarr = zarr.open(zarr.SQLiteStore(self._largeImagePath), mode='r')
        except Exception:
            try:
                self._zarr = zarr.open(self._largeImagePath, mode='r')
            except Exception:
                if os.path.basename(self._largeImagePath) in {'.zgroup', '.zattrs', '.zarray'}:
                    try:
                        self._zarr = zarr.open(os.path.dirname(self._largeImagePath), mode='r')
                    except Exception:
                        pass
        if self._zarr is None:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            msg = 'File cannot be opened via zarr.'
            raise TileSourceError(msg)
        try:
            self._validateZarr()
        except TileSourceError:
            raise
        except Exception:
            msg = 'File cannot be opened -- not an OME NGFF file or understandable zarr file.'
            raise TileSourceError(msg)
        self._tileLock = threading.RLock()

    def _getGeneralAxes(self, arr):
        """
        Examine a zarr array an guess what the axes are.  We assume the two
        maximal dimensions are y, x.  Then, if there is a dimension that is 3
        or 4 in length, it is channels.  If there is more than one other that
        is not 1, we don't know how it is sorted, so we will fail.

        :param arr: a zarr array.
        :return: a dictionary of axes with the axis as the key and the index
            within the array axes as the value.
        """
        shape = arr.shape
        maxIndex = shape.index(max(shape))
        secondMaxIndex = shape.index(max(x for idx, x in enumerate(shape) if idx != maxIndex))
        axes = {
            'x': max(maxIndex, secondMaxIndex),
            'y': min(maxIndex, secondMaxIndex),
        }
        for idx, val in enumerate(shape):
            if idx not in axes.values() and val == 4 and 'c' not in axes:
                axes['c'] = idx
            if idx not in axes.values() and val == 3:
                axes['c'] = idx
        for idx, val in enumerate(shape):
            if idx not in axes.values() and val > 1:
                if 'f' in axes:
                    msg = 'Too many large axes'
                    raise TileSourceError(msg)
                axes['f'] = idx
        return axes

    def _scanZarrArray(self, group, arr, results):
        """
        Scan a zarr array and determine if is the maximal dimension array we
        can read.  If so, update a results dictionary with the information.  If
        it is the shape as a previous maximum, append it as a multi-series set.
        If not, and it is small enough, add it to a list of possible associated
        images.

        :param group: a zarr group; the parent of the array.
        :param arr: a zarr array.
        :param results: a dictionary to store the results.  'best' contains a
            tuple that is used to find the maximum size array, preferring ome
            arrays, then total pixels, then channels.  'is_ome' is a boolean.
            'series' is a list of the found groups and arrays that match the
            best criteria.  'axes' and 'channels' are from the best array.
            'associated' is a list of all groups and arrays that might be
            associated images.  These have to be culled for the actual groups
            used in the series.
        """
        attrs = group.attrs.asdict() if group is not None else {}
        min_version = packaging.version.Version('0.4')
        is_ome = (
            isinstance(attrs.get('multiscales', None), list) and
            'omero' in attrs and
            isinstance(attrs['omero'], dict) and
            all(isinstance(m, dict) for m in attrs['multiscales']) and
            all(packaging.version.Version(m['version']) >= min_version
                for m in attrs['multiscales'] if 'version' in m))
        channels = None
        if is_ome:
            axes = {axis['name']: idx for idx, axis in enumerate(
                attrs['multiscales'][0]['axes'])}
            if isinstance(attrs['omero'].get('channels'), list):
                channels = [channel['label'] for channel in attrs['omero']['channels']]
                if all(channel.startswith('Channel ') for channel in channels):
                    channels = None
        else:
            try:
                axes = self._getGeneralAxes(arr)
            except TileSourceError:
                return
        if 'x' not in axes or 'y' not in axes:
            return
        check = (is_ome, math.prod(arr.shape), channels is not None,
                 tuple(axes.keys()), tuple(channels) if channels else ())
        if results['best'] is None or check > results['best']:
            results['best'] = check
            results['series'] = [(group, arr)]
            results['is_ome'] = is_ome
            results['axes'] = axes
            results['channels'] = channels
        elif check == results['best']:
            results['series'].append((group, arr))
        if not any(group is g for g, _ in results['associated']):
            axes = {k: v for k, v in axes.items() if arr.shape[axes[k]] > 1}
            if (len(axes) <= 3 and
                    self._minAssociatedImageSize <= arr.shape[axes['x']] <=
                    self._maxAssociatedImageSize and
                    self._minAssociatedImageSize <= arr.shape[axes['y']] <=
                    self._maxAssociatedImageSize and
                    (len(axes) == 2 or ('c' in axes and arr.shape[axes['c']] in {1, 3, 4}))):
                results['associated'].append((group, arr))

    def _scanZarrGroup(self, group, results=None):
        """
        Scan a zarr group for usable arrays.

        :param group: a zarr group
        :param results: a results dicitionary, updated.
        :returns: the results dictionary.
        """
        if results is None:
            results = {'best': None, 'series': [], 'associated': []}
        if isinstance(group, zarr.core.Array):
            self._scanZarrArray(None, group, results)
            return results
        for val in group.values():
            if isinstance(val, zarr.core.Array):
                self._scanZarrArray(group, val, results)
            elif isinstance(val, zarr.hierarchy.Group):
                results = self._scanZarrGroup(val, results)
        return results

    def _zarrFindLevels(self):
        """
        Find usable multi-level images.  This checks that arrays are nearly a
        power of two.  This updates self._levels and self._populatedLevels.
        self._levels is an array the same length as the number of series, each
        entry of which is an array of the number of conceptual tile levels
        where each entry of that is either the zarr array that can be used to
        get pixels or None if it is not populated.
        """
        levels = [[None] * self.levels for _ in self._series]
        baseGroup, baseArray = self._series[0]
        for idx, (_, arr) in enumerate(self._series):
            levels[idx][0] = arr
        arrs = [[arr for _, arr in s.arrays()] if s is not None else [a] for s, a in self._series]
        for idx, arr in enumerate(arrs[0]):
            if any(idx >= len(sarrs) for sarrs in arrs[1:]):
                break
            if any(arr.shape != sarrs[idx].shape for sarrs in arrs[1:]):
                continue
            if (nearPowerOfTwo(self.sizeX, arr.shape[self._axes['x']]) and
                    nearPowerOfTwo(self.sizeY, arr.shape[self._axes['y']])):
                level = int(round(math.log(self.sizeX / arr.shape[self._axes['x']]) / math.log(2)))
                if level < self.levels and levels[0][level] is None:
                    for sidx in range(len(self._series)):
                        levels[sidx][level] = arrs[sidx][idx]
        self._levels = levels
        self._populatedLevels = len([l for l in self._levels[0] if l is not None])
        # TODO: check for inefficient file and raise warning

    def _getScale(self):
        """
        Get the scale values from the ome metadata and populate the class
        values for _mm_x and _mm_y.
        """
        unit = {'micrometer': 1e-3, 'millimeter': 1, 'meter': 1e3}
        self._mm_x = self._mm_y = None
        baseGroup, baseArray = self._series[0]
        try:
            ms = baseGroup.attrs.asdict()['multiscales'][0]
            self._mm_x = ms['datasets'][0]['coordinateTransformations'][0][
                'scale'][self._axes['x']] * unit[ms['axes'][self._axes['x']]['unit']]
            self._mm_y = ms['datasets'][0]['coordinateTransformations'][0][
                'scale'][self._axes['y']] * unit[ms['axes'][self._axes['y']]['unit']]
        except Exception:
            pass

    def _validateZarr(self):
        """
        Validate that we can read tiles from the zarr parent group in
        self._zarr.  Set up the appropriate class variables.
        """
        found = self._scanZarrGroup(self._zarr)
        if found['best'] is None:
            msg = 'No data array that can be used.'
            raise TileSourceError(msg)
        self._series = found['series']
        baseGroup, baseArray = self._series[0]
        self._is_ome = found['is_ome']
        self._axes = {k.lower(): v for k, v in found['axes'].items() if baseArray.shape[v] > 1}
        if len(self._series) > 1 and 'xy' in self._axes:
            msg = 'Conflicting xy axis data.'
            raise TileSourceError(msg)
        self._channels = found['channels']
        self._associatedImages = [
            (g, a) for g, a in found['associated'] if not any(g is gb for gb, _ in self._series)]
        self.sizeX = baseArray.shape[self._axes['x']]
        self.sizeY = baseArray.shape[self._axes['y']]
        self.tileWidth = (
            baseArray.chunks[self._axes['x']]
            if self._minTileSize <= baseArray.chunks[self._axes['x']] <= self._maxTileSize else
            self._tileSize)
        self.tileHeight = (
            baseArray.chunks[self._axes['y']]
            if self._minTileSize <= baseArray.chunks[self._axes['y']] <= self._maxTileSize else
            self._tileSize)
        # If we wanted to require equal tile width and height:
        # self.tileWidth = self.tileHeight = self._tileSize
        # if (baseArray.chunks[self._axes['x']] == baseArray.chunks[self._axes['y']] and
        #         self._minTileSize <= baseArray.chunks[self._axes['x']] <= self._maxTileSize):
        #     self.tileWidth = self.tileHeight = baseArray.chunks[self._axes['x']]
        self.levels = int(max(1, math.ceil(math.log(max(
            self.sizeX / self.tileWidth, self.sizeY / self.tileHeight)) / math.log(2)) + 1))
        self._dtype = baseArray.dtype
        self._bandCount = 1
        if ('c' in self._axes and 's' not in self._axes and not self._channels and
                baseArray.shape[self._axes.get('c')] in {1, 3, 4}):
            self._bandCount = baseArray.shape[self._axes['c']]
            self._axes['s'] = self._axes.pop('c')
        self._zarrFindLevels()
        self._getScale()
        stride = 1
        self._strides = {}
        self._axisCounts = {}
        for _, k in sorted((-'tzc'.index(k) if k in 'tzc' else 1, k)
                           for k in self._axes if k not in 'xys'):
            self._strides[k] = stride
            self._axisCounts[k] = baseArray.shape[self._axes[k]]
            stride *= baseArray.shape[self._axes[k]]
        if len(self._series) > 1:
            self._strides['xy'] = stride
            self._axisCounts['xy'] = len(self._series)
            stride *= len(self._series)
        self._framecount = stride

    def _nonemptyLevelsList(self, frame=0):
        """
        Return a list of one value per level where the value is None if the
        level does not exist in the file and any other value if it does.

        :param frame: the frame number.
        :returns: a list of levels length.
        """
        return [True if l is not None else None for l in self._levels[0][::-1]]

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = self._mm_x
        mm_y = self._mm_y
        # Estimate the magnification; we don't have a direct value
        mag = 0.01 / mm_x if mm_x else None
        return {
            'magnification': getattr(self, '_magnification', mag),
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
        if self._framecount > 1:
            result['frames'] = frames = []
            for idx in range(self._framecount):
                frame = {'Frame': idx}
                for axis in self._strides:
                    frame['Index' + axis.upper()] = (
                        idx // self._strides[axis]) % self._axisCounts[axis]
                frames.append(frame)
            self._addMetadataFrameInformation(result, getattr(self, '_channels', None))
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        result['zarr'] = {
            'base': self._zarr.attrs.asdict(),
            'main': self._series[0][0].attrs.asdict(),
        }
        return result

    def getAssociatedImagesList(self):
        """
        Get a list of all associated images.

        :return: the list of image keys.
        """
        return [f'image_{idx}' for idx in range(len(self._associatedImages))]

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        if not imageKey.startswith('image_'):
            return
        try:
            idx = int(imageKey[6:])
        except Exception:
            return
        if idx < 0 or idx >= len(self._associatedImages):
            return
        group, arr = self._associatedImages[idx]
        axes = self._getGeneralAxes(arr)
        trans = [idx for idx in range(len(arr.shape))
                 if idx not in axes.values()] + [axes['y'], axes['x']]
        if 'c' in axes or 's' in axes:
            trans.append(axes.get('c', axes.get('s')))
        with self._tileLock:
            img = np.transpose(arr, trans).squeeze()
        if len(img.shape) == 2:
            img.expand_dims(axis=2)
        return large_image.tilesource.base._imageToPIL(img)

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        frame = self._getFrame(**kwargs)
        self._xyzInRange(x, y, z, frame, self._framecount)
        x0, y0, x1, y1, step = self._xyzToCorners(x, y, z)
        sidx = 0 if len(self._series) <= 1 else frame // self._strides['xy']
        targlevel = self.levels - 1 - z
        while targlevel and self._levels[sidx][targlevel] is None:
            targlevel -= 1
        arr = self._levels[sidx][targlevel]
        scale = int(2 ** targlevel)
        x0 //= scale
        y0 //= scale
        x1 //= scale
        y1 //= scale
        step //= scale
        if step > 2 ** self._maxSkippedLevels:
            tile = self._getTileFromEmptyLevel(x, y, z, **kwargs)
            tile = large_image.tilesource.base._imageToNumpy(tile)[0]
        else:
            idx = [slice(None) for _ in arr.shape]
            idx[self._axes['x']] = slice(x0, x1, step)
            idx[self._axes['y']] = slice(y0, y1, step)
            for key in self._axes:
                if key in self._strides:
                    pos = (frame // self._strides[key]) % self._axisCounts[key]
                    idx[self._axes[key]] = slice(pos, pos + 1)
            trans = [idx for idx in range(len(arr.shape))
                     if idx not in {self._axes['x'], self._axes['y'],
                                    self._axes.get('s', self._axes['x'])}]
            squeezeCount = len(trans)
            trans += [self._axes['y'], self._axes['x']]
            if 's' in self._axes:
                trans.append(self._axes['s'])
            with self._tileLock:
                tile = arr[tuple(idx)]
                tile = np.transpose(tile, trans)
            for _ in range(squeezeCount):
                tile = tile.squeeze(0)
            if len(tile.shape) == 2:
                tile = np.expand_dims(tile, axis=2)
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return ZarrFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return ZarrFileTileSource.canRead(*args, **kwargs)
