# -*- coding: utf-8 -*-

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

import array
import cachetools
import math
import nd2reader
import numpy
import six
import threading
import types
import warnings

from six.moves import range

from pkg_resources import DistributionNotFound, get_distribution

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority, TILE_FORMAT_NUMPY
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


warnings.filterwarnings('ignore', category=UserWarning, module='nd2reader')


@six.add_metaclass(LruCacheMetaclass)
class ND2FileTileSource(FileTileSource):
    """
    Provides tile access to nd2 files and other files the nd2reader library can
    read.
    """

    cacheName = 'tilesource'
    name = 'nd2file'
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
        super(ND2FileTileSource, self).__init__(path, **kwargs)

        self._largeImagePath = self._getLargeImagePath()

        self._pixelInfo = {}
        try:
            self._nd2 = nd2reader.ND2Reader(self._largeImagePath)
        except (UnicodeDecodeError,
                nd2reader.exceptions.InvalidVersionError,
                nd2reader.exceptions.EmptyFileError):
            raise TileSourceException('File cannot be opened via nd2reader.')
        self._logger = config.getConfig('logger')
        self._tileLock = threading.RLock()
        self._recentFrames = cachetools.LRUCache(maxsize=6)
        self.sizeX = self._nd2.metadata['width']
        self.sizeY = self._nd2.metadata['height']
        self.tileWidth = self.tileHeight = self._tileSize
        if self.sizeX <= self._singleTileThreshold and self.sizeY <= self._singleTileThreshold:
            self.tileWidth = self.sizeX
            self.tileHeight = self.sizeY
        self.levels = int(max(1, math.ceil(math.log(
            float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1))
        # There is one file that throws a warning 'Z-levels details missing in
        # metadata'.  In this instance, there should be no z-levels.
        try:
            if (self._nd2.sizes.get('z') and
                    self._nd2.sizes.get('z') == self._nd2.sizes.get('v') and
                    not len(self._nd2._parser._raw_metadata._parse_dimension(
                        r""".*?Z\((\d+)\).*?""")) and
                    self._nd2.sizes['v'] * self._nd2.sizes.get('t', 1) ==
                    self._nd2.metadata.get('total_images_per_channel')):
                self._nd2._parser._raw_metadata._metadata_parsed['z_levels'] = []
                self._nd2.sizes['z'] = 1
        except Exception:
            pass
        frames = self._nd2.sizes.get('c', 1) * self._nd2.metadata.get(
            'total_images_per_channel', 0)
        self._framecount = frames if frames else None
        self._nd2.iter_axes = sorted(
            [a for a in self._nd2.axes if a not in {'x', 'y', 'v'}], reverse=True)
        if frames and len(self._nd2) != frames and 'v' in self._nd2.axes:
            self._nd2.iter_axes = ['v'] + self._nd2.iter_axes
        if 'c' in self._nd2.iter_axes and len(self._nd2.metadata.get('channels', [])):
            self._bandnames = {
                name.lower(): idx for idx, name in enumerate(self._nd2.metadata['channels'])}

        # self._nd2.metadata
        # {'channels': ['CY3', 'A594', 'CY5', 'DAPI'],
        #  'date': datetime.datetime(2019, 7, 21, 15, 13, 45),
        #  'events': [],
        #  'experiment': {'description': '',
        #                 'loops': [{'duration': 0,
        #                            'sampling_interval': 0.0,
        #                            'start': 0,
        #                            'stimulation': False}]},
        #  'fields_of_view': range(0, 2500),         # v
        #  'frames': [0],
        #  'height': 1022,
        #  'num_frames': 1,
        #  'pixel_microns': 0.219080212825376,
        #  'total_images_per_channel': 2500,
        #  'width': 1024,
        #  'z_coordinates': [1890.8000000000002,
        #                    1891.025,
        #                    1891.1750000000002,
        # ...
        #                    1905.2250000000001,
        #                    1905.125,
        #                    1905.1000000000001],
        #  'z_levels': range(0, 2500)}

        # self._nd2.axes   ['x', 'y', 'c', 't', 'z', 'v']
        # self._nd2.ndim   6
        # self._nd2.pixel_type   numpy.float64
        # self._nd2.sizes  {'x': 1024, 'y': 1022, 'c': 4, 't': 1, 'z': 2500, 'v': 2500}
        self._getND2Metadata()

    def _getND2MetadataCleanDict(self, olddict):
        newdict = {}
        for key, value in olddict.items():
            if value not in (None, b'', ''):
                if isinstance(key, six.binary_type):
                    key = key.decode('utf8')
                if (isinstance(value, dict) and len(value) == 1 and
                        list(value.keys())[0] in (b'', '')):
                    value = list(value.values())[0]
                if isinstance(value, six.binary_type):
                    value = value.decode('utf8')
                if isinstance(value, dict):
                    value = self._getND2MetadataCleanDict(value)
                    if not len(value):
                        continue
                if (isinstance(value, types.GeneratorType) or
                        isinstance(value, (numpy.ndarray, array.array, range))):
                    value = list(value)
                if isinstance(value, list):
                    if not len(value):
                        continue
                    for idx, entry in enumerate(value):
                        if isinstance(entry, six.binary_type):
                            entry = entry.decode('utf8')
                        if isinstance(entry, dict):
                            entry = self._getND2MetadataCleanDict(entry)
                        value[idx] = entry
                newdict[key] = value
        return newdict

    def _getND2Metadata(self):
        self._metadata = self._nd2.metadata.copy()
        for key, value in self._metadata.items():
            if (isinstance(value, types.GeneratorType) or
                    isinstance(value, (numpy.ndarray, array.array, range))):
                value = list(value)
            self._metadata[key] = value
        for key in {
                'acquisition_times', 'app_info', 'camera_exposure_time',
                'camera_temp', 'channels', 'custom_data', 'date', 'events',
                'experiment', 'fields_of_view', 'frames', 'height',
                'image_attributes', 'image_calibration', 'image_events',
                'image_metadata', 'image_metadata_sequence', 'image_text_info',
                'num_frames', 'pfs_offset', 'pfs_status', 'pixel_microns',
                'roi_metadata', 'total_images_per_channel', 'width', 'x_data',
                'y_data', 'z_coordinates', 'z_data', 'z_levels'}:
            if key in self._metadata:
                continue
            try:
                value = getattr(self._nd2.parser._raw_metadata, key, None)
            except AttributeError:
                continue
            if (isinstance(value, types.GeneratorType) or
                    isinstance(value, (numpy.ndarray, array.array, range))):
                value = list(value)
            if isinstance(value, dict):
                value = self._getND2MetadataCleanDict(value)
            if value is not None and value != [] and value != {}:
                self._metadata[key] = value

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = mm_y = None
        microns = None
        try:
            microns = float(self._nd2.metadata.get('pixel_microns', 0))
            if microns and microns > 0:
                mm_x = mm_y = microns * 0.001
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

        :returns: metadata dictonary.
        """
        result = super(ND2FileTileSource, self).getMetadata()

        sizes = self._nd2.sizes
        # We may want to reformat the frames to standardize this across sources
        # An example of frames from OMETiff: {
        #   "DeltaT": "3532.529541",
        #   "ExposureTime": "3100.000000",
        #   "PositionX": "27808.039063",
        #   "PositionY": "38605.839844",
        #   "PositionZ": "1905.524976",
        #   "TheC": "0",
        #   "TheT": "0",
        #   "TheZ": "1",
        # }
        axes = self._nd2.iter_axes[::-1]
        result['frames'] = frames = []
        for idx in range(len(self._nd2)):
            frame = {'Frame': idx, 'IndexZ': 0, 'IndexXY': 0}
            basis = 1
            ref = {}
            for axis in axes:
                ref[axis] = (idx // basis) % sizes[axis]
                frame['Index' + (axis.upper() if axis != 'v' else 'XY')] = (
                    idx // basis) % sizes[axis]
                basis *= sizes.get(axis, 1)
            if 'z_coordinates' in self._metadata:
                frame['PositionZ'] = self._metadata['z_coordinates'][ref.get('z', 0)]
            frames.append(frame)
            if self._framecount and len(frames) == self._framecount:
                break
        self._addMetadataFrameInformation(result, self._metadata.get('channels'))
        for frame in result['frames']:
            index = frame['Index']
            for mkey, fkey in [
                ('x_data', 'PositionX'),
                ('y_data', 'PositionY'),
                ('z_data', 'PositionZ'),
                ('acquisition_times', 'DeltaT'),
                ('camera_exposure_time', 'ExposureTime'),
            ]:
                if mkey in self._metadata:
                    frame[fkey] = self._metadata[mkey][index % len(self._metadata[mkey])]
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        result['nd2'] = self._metadata
        # result['nd2'].pop('custom_data', None)
        # result['nd2'].pop('image_metadata', None)
        # result['nd2'].pop('image_metadata_sequence', None)
        result['nd2_sizes'] = self._nd2.sizes
        result['nd2_axes'] = self._nd2.axes
        result['nd2_iter_axes'] = self._nd2.iter_axes
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        self._xyzInRange(x, y, z)
        step = int(2 ** (self.levels - 1 - z))
        x0 = x * step * self.tileWidth
        x1 = min((x + 1) * step * self.tileWidth, self.sizeX)
        y0 = y * step * self.tileHeight
        y1 = min((y + 1) * step * self.tileHeight, self.sizeY)
        frame = kwargs.get('frame')
        frame = int(frame) if frame else 0
        if frame < 0 or frame >= len(self._nd2):
            raise TileSourceException('Frame does not exist')
        with self._tileLock:
            if frame in self._recentFrames:
                tileframe = self._recentFrames[frame]
            else:
                tileframe = self._nd2[frame]
                self._recentFrames[frame] = tileframe
            tile = tileframe[y0:y1:step, x0:x1:step].copy()
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)
