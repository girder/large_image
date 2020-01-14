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

import math
import nd2reader
import os
import six
import struct
import threading
import warnings

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
                nd2reader.exceptions.EmotyFileError):
            raise TileSourceException('File cannot be opened via nd2reader.')
        self._logger = config.getConfig('logger')
        self._tileLock = threading.RLock()
        self.sizeX = self._nd2.metadata['width']
        self.sizeY = self._nd2.metadata['height']
        self.tileWidth = self.tileHeight = 256
        self.levels = max(1, math.ceil(math.log(
            float(max(self.sizeX, self.sizeY)) / self.tileWidth) / math.log(2)) + 1)
        frames = self._nd2.sizes.get('c', 0) * self._nd2.metadata.get(
            'total_images_per_channel', 0)
        self._nd2.iter_axes = sorted(a for a in self._nd2.axes if a not in {'x', 'y', 'v'})
        if frames and len(self._nd2) != frames and 'v' in self._nd2.axes:
            self._nd2.iter_axes = self._nd2.iter_axes + ['v']
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
        self._metadata = self._getND2Metadata()

    def _getND2Chunk_CustomData(self, chunk, data):
        if len(chunk['parts']) == 2 and chunk['parts'][1] in {
                b'X', b'Y', b'Z', b'Z1',
                b'Camera_ExposureTime1',
                b'AcqTimesCache'}:
            if len(data) % 8:
                return
            chunk['data'] = struct.unpack('<%dd' % (len(data) / 8), data)
        # Other CustomData could be processed here

    def _getND2Chunk_process_lv(self, chunk, data):
        origdata = data
        chunk['data'] = results = {}
        while len(data) > 2:
            dtype, keylen = struct.unpack('BB', data[:2])
            if dtype < 1 or dtype > 11 or keylen == 0:
                self._logger.debug(
                    'Stopped reading LV record (%r), unknown dtype %d, %d bytes into record',
                    chunk, dtype, len(origdata) - len(data))
                break
            if data[keylen * 2:keylen * 2 + 2] != b'\x00\x00':
                self._logger.debug(
                    'Stopped reading LV record (%r), unterminated key, %d bytes into record',
                    chunk, len(origdata) - len(data))
                break
            key = data[2:keylen * 2].decode('utf16')
            data = data[keylen * 2 + 2:]
            if dtype in {1, 2, 3, 4, 5, 6, 7}:
                dlen = {1: 1, 2: 4, 3: 4, 4: 8, 5: 8, 6: 8, 7: 8}[dtype]
                value = struct.unpack('<%s' % {
                    1: 'B', 2: 'l', 3: 'L', 4: 'q', 5: 'Q', 6: 'd', 7: 'Q',
                }[dtype], data[:dlen])[0]
                data = data[dlen:]
            elif dtype == 8:
                value = None
                for idx in range(0, len(data), 2):
                    if data[idx:idx + 2] == b'\x00\x00':
                        value = data[:idx].decode('utf16')
                        data = data[idx + 2:]
                        break
                if value is None:
                    return
            elif dtype == 9:
                dlen = struct.unpack('<Q', data[:8])[0]
                value = data[8:8 + dlen]
                data = data[8 + dlen:]
            elif dtype in {10, 11}:
                value = None
                count = struct.unpack('<L', data[:4])[0]
                if count:
                    # pos = struct.unpack('<LQ', data[4:12])[0]
                    data = data[12:]
                    # This isn't generally correct
                    # value = struct.unpack(
                    #     '<%dQ' % count, origdata[pos:pos + count * 8]) if dtype == 11 else None
                else:
                    self._logger.debug(
                        'Stopped reading LV record (%r), levels record has no '
                        'count, %d bytes into record',
                        chunk, len(origdata) - len(data))
                    break
            if value not in {None, b'', ''}:
                results[key] = value

    def _getND2Chunk_ImageMetadataLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Chunk_ImageEventsLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Chunk_ImageAttributesLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Chunk_ImageCalibrationLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Chunk_ImageMetadataSeqLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Chunk_ImageTextInfoLV(self, chunk, data):
        self._getND2Chunk_process_lv(chunk, data)

    def _getND2Metadata(self):
        chunkMapSig = b'ND2 CHUNK MAP SIGNATURE 0000001'
        fileMapSig = b'ND2 FILEMAP SIGNATURE NAME 0001'
        with open(self._largeImagePath, 'rb') as fptr:
            fptr.seek(-40, os.SEEK_END)
            data = fptr.read(40)
            if len(data) != 40 or not data.startswith(chunkMapSig):
                return
            pos = struct.unpack('<Q', data[len(chunkMapSig) + 1:])[0]
            fptr.seek(pos, os.SEEK_SET)
            data = fptr.read(48)
            if len(data) != 48 or not data[16:].startswith(fileMapSig):
                return
            headerlen, datalen = struct.unpack('<LQ', data[4:16])
            fptr.seek(pos + headerlen + 16, os.SEEK_SET)
            data = fptr.read(datalen)
            chunks = {}
            while b'!' in data:
                chunkname, data = data.split(b'!', 1)
                if len(data) < 16:
                    break
                chunkpos, chunklen = struct.unpack('<QQ', data[:16])
                data = data[16:]
                chunks[chunkname] = {
                    'pos': chunkpos,
                    'len': chunklen,
                    'name': chunkname,
                    'parts': chunkname.split(b'|'),
                }
            self._logger.debug('Chunks: %r' % [key.decode() for key in sorted(chunks.keys())])
            for chunkname, chunk in chunks.items():
                func = None
                for partidx in range(len(chunk['parts']), 0, -1):
                    funcname = '_getND2Chunk_' + (
                        b'_'.join(chunk['parts'][:partidx])).decode().replace(' ', '_')
                    func = getattr(self, funcname, None)
                    if func:
                        break
                if func and chunk['len'] <= 16 * 1024 * 1024:
                    fptr.seek(chunk['pos'])
                    data = fptr.read(16 + len(chunkname) + 1)
                    if data[16:-1] != chunkname or data[-1:] != b'!':
                        continue
                    headerlen, datalen = struct.unpack('<LQ', data[4:16])
                    if datalen != chunk['len']:
                        continue
                    fptr.seek(chunk['pos'] + 16 + headerlen)
                    data = fptr.read(datalen)
                    func(chunk, data)
        return chunks

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
        result['nd2'] = self._nd2.metadata
        result['nd2_sizes'] = sizes = self._nd2.sizes
        result['nd2_axes'] = baseaxes = self._nd2.axes
        result['nd2_iter_axes'] = self._nd2.iter_axes
        result['nd2_file_metadata'] = {}
        for chunkname, chunk in self._metadata.items():
            if 'data' in chunk:
                result['nd2_file_metadata'][chunkname.decode()] = chunk['data']
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
        axes = self._nd2.iter_axes
        result['frames'] = frames = []
        for idx in range(len(self._nd2)):
            frame = {}
            basis = 1
            ref = {}
            for axis in axes:
                ref[axis] = (idx // basis) % sizes[axis]
                frame['The' + axis.upper()] = (idx // basis) % sizes[axis]
                basis *= sizes.get(axis, 1)
            if 'z_coordinates' in self._nd2.metadata:
                frame['PositionZ'] = self._nd2.metadata['z_coordinates'][ref.get('z', 0)]
            cdidx = 0
            basis = 1
            for axis in baseaxes:
                if axis not in {'x', 'y', 'c'}:
                    cdidx += ref[axis] * basis
                    basis *= sizes[axis]
            for mkey, fkey in [
                (b'CustomData|X', 'PositionX'),
                (b'CustomData|Y', 'PositionY'),
                (b'CustomData|Z1', 'PositionZ'),
                (b'CustomData|Z', 'PositionZ'),
                (b'CustomData|AcqTimesCache', 'DeltaT'),
                (b'CustomData|Camera_ExposureTime1', 'ExposureTime'),
            ]:
                if self._metadata.get(mkey, {}).get('data'):
                    frame[fkey] = self._metadata[mkey]['data'][
                        cdidx % len(self._metadata[mkey]['data'])]
            frames.append(frame)
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        if z < 0 or z >= self.levels:
            raise TileSourceException('z layer does not exist')
        step = int(2 ** (self.levels - 1 - z))
        x0 = x * step * self.tileWidth
        x1 = min((x + 1) * step * self.tileWidth, self.sizeX)
        y0 = y * step * self.tileHeight
        y1 = min((y + 1) * step * self.tileHeight, self.sizeY)
        if x < 0 or x0 >= self.sizeX:
            raise TileSourceException('x is outside layer')
        if y < 0 or y0 >= self.sizeY:
            raise TileSourceException('y is outside layer')
        frame = kwargs.get('frame')
        frame = int(frame) if frame else 0
        if frame < 0 or frame >= len(self._nd2):
            raise TileSourceException('Frame does not exist')
        with self._tileLock:
            tile = self._nd2[frame][y0:y1:step, x0:x1:step].copy()
        return self._outputTile(tile, TILE_FORMAT_NUMPY, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)
