##############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
##############################################################################

import math
import os
import threading

import numpy

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_NUMPY, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource

nd2 = None

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
    Import the nd2 module.  This is done when needed rather than in the module
    initialization because it is slow.
    """
    global nd2

    if nd2 is None:
        try:
            import nd2
        except ImportError:
            raise TileSourceError('nd2 module not found.')


def namedtupleToDict(obj):
    """
    Convert a namedtuple to a plain dictionary.

    :param obj: the object to convert
    :returns: a dictionary or the original object.
    """
    if hasattr(obj, '__dict__') and not isinstance(obj, dict):
        obj = obj.__dict__
    if isinstance(obj, dict):
        obj = {
            k: namedtupleToDict(v) for k, v in obj.items()
            if not k.startswith('_')}
        return {k: v for k, v in obj.items() if v is not None and v != {} and v != ''}
    if isinstance(obj, (tuple, list)):
        obj = [namedtupleToDict(v) for v in obj]
        if not any(v is not None and v != {} and v != '' for v in obj):
            return None
    return obj


def diffObj(obj1, obj2):
    """
    Given two objects, report the differences that exist in the first object
    that are not in the second object.

    :param obj1: the first object to compare.  Only values present in this
        object are returned.
    :param obj2: the second object to compare.
    :returns: a subset of obj1.
    """
    if obj1 == obj2:
        return None
    if type(obj1) != type(obj2):
        return obj1
    if isinstance(obj1, (list, tuple)):
        return [diffObj(obj1[idx], obj2[idx]) for idx in range(len(obj1))]
    if isinstance(obj1, dict):
        diff = {k: diffObj(v, obj2.get(k)) for k, v in obj1.items()}
        diff = {k: v for k, v in diff.items() if v is not None}
        return diff
    return obj1


class ND2FileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to nd2 files the nd2 or nd2reader library can read.
    """

    cacheName = 'tilesource'
    name = 'nd2'
    extensions = {
        None: SourcePriority.LOW,
        'nd2': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/nd2': SourcePriority.PREFERRED,
    }

    # If frames are smaller than this they are served as single tiles, which
    # can be more efficient than handling multiple tiles.
    _singleTileThreshold = 2048
    _tileSize = 512

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = str(self._getLargeImagePath())

        self._pixelInfo = {}

        _lazyImport()
        try:
            self._nd2 = nd2.ND2File(self._largeImagePath, validate_frames=True)
        except Exception:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            raise TileSourceError('File cannot be opened via nd2reader.')
        # We use dask to allow lazy reading of large images
        self._nd2array = self._nd2.to_dask(copy=False)
        arrayOrder = list(self._nd2.sizes)
        # Reorder this so that it is XY (P), T, Z, C, Y, X, S (or at least end
        # in Y, X[, S]).
        newOrder = [k for k in arrayOrder if k not in {'C', 'X', 'Y', 'S'}] + (
            ['C'] if 'C' in arrayOrder else []) + ['Y', 'X'] + (
            ['S'] if 'S' in arrayOrder else [])
        if newOrder != arrayOrder:
            self._nd2array = numpy.moveaxis(
                self._nd2array,
                list(range(len(arrayOrder))),
                [newOrder.index(k) for k in arrayOrder])
        self._nd2order = newOrder
        self._nd2origindex = {}
        basis = 1
        for k in arrayOrder:
            if k not in {'C', 'X', 'Y', 'S'}:
                self._nd2origindex[k] = basis
                basis *= self._nd2.sizes[k]
        self.sizeX = self._nd2.sizes['X']
        self.sizeY = self._nd2.sizes['Y']
        self.tileWidth = self.tileHeight = self._tileSize
        if self.sizeX <= self._singleTileThreshold and self.sizeY <= self._singleTileThreshold:
            self.tileWidth = self.sizeX
            self.tileHeight = self.sizeY
        self.levels = int(max(1, math.ceil(math.log(
            float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1))
        self._framecount = (
            self._nd2.metadata.contents.channelCount * self._nd2.metadata.contents.frameCount)
        self._bandnames = {
            chan.channel.name.lower(): idx for idx, chan in enumerate(self._nd2.metadata.channels)}
        self._channels = [chan.channel.name for chan in self._nd2.metadata.channels]
        self._tileLock = threading.RLock()

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = mm_y = None
        microns = None
        try:
            microns = self._nd2.voxel_size()
            mm_x = microns.x * 1000
            mm_y = microns.y * 1000
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

        sizes = self._nd2.sizes
        axes = self._nd2order[:self._nd2order.index('Y')][::-1]
        sizes = self._nd2.sizes
        result['frames'] = frames = []
        for idx in range(self._framecount):
            frame = {'Frame': idx}
            basis = 1
            ref = {}
            for axis in axes:
                ref[axis] = (idx // basis) % sizes[axis]
                frame['Index' + (axis.upper() if axis.upper() != 'P' else 'XY')] = (
                    idx // basis) % sizes[axis]
                basis *= sizes.get(axis, 1)
            frames.append(frame)
        self._addMetadataFrameInformation(result, self._channels)
        for frame in result['frames']:
            frame['OriginalIndex'] = sum(
                frame[k] * self._nd2origindex.get(
                    k.split('Index')[1] if k != 'IndexXY' else 'P', 1)
                for k in frame if k.startswith('Index') and k != 'Index')
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        result['nd2'] = namedtupleToDict(self._nd2.metadata)
        result['nd2_sizes'] = self._nd2.sizes
        result['nd2_text'] = self._nd2.text_info
        result['nd2_custom'] = self._nd2.custom_data
        result['nd2_experiment'] = namedtupleToDict(self._nd2.experiment)
        result['nd2_legacy'] = self._nd2.is_legacy
        result['nd2_rgb'] = self._nd2.is_rgb
        result['nd2_frame_metadata'] = [
            diffObj(namedtupleToDict(self._nd2.frame_metadata(idx)), result['nd2'])
            for idx in range(self._nd2.metadata.contents.frameCount)]
        if (len(result['nd2_frame_metadata']) and
                list(result['nd2_frame_metadata'][0].keys()) == ['channels']):
            result['nd2_frame_metadata'] = [
                fm['channels'][0] for fm in result['nd2_frame_metadata']]
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        frame = int(kwargs.get('frame') or 0)
        self._xyzInRange(x, y, z, frame, self._framecount)
        x0, y0, x1, y1, step = self._xyzToCorners(x, y, z)
        tileframe = self._nd2array
        fc = self._framecount
        fp = frame
        for axis in self._nd2order[:self._nd2order.index('Y')]:
            fc //= self._nd2.sizes[axis]
            tileframe = tileframe[fp // fc]
            fp = fp % fc
        with self._tileLock:
            tile = tileframe[y0:y1:step, x0:x1:step].compute().copy()
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return ND2FileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return ND2FileTileSource.canRead(*args, **kwargs)
