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

import copy
import math
import os
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _importlib_version

import numpy as np
import PIL.Image
from large_image_source_tiff import TiffFileTileSource
from large_image_source_tiff.exceptions import InvalidOperationTiffError, IOTiffError, TiffError

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_NUMPY, TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError

try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


_omeUnitsToMeters = {
    'Ym': 1e24,
    'Zm': 1e21,
    'Em': 1e18,
    'Pm': 1e15,
    'Tm': 1e12,
    'Gm': 1e9,
    'Mm': 1e6,
    'km': 1e3,
    'hm': 1e2,
    'dam': 1e1,
    'm': 1,
    'dm': 1e-1,
    'cm': 1e-2,
    'mm': 1e-3,
    '\u00b5m': 1e-6,
    'nm': 1e-9,
    'pm': 1e-12,
    'fm': 1e-15,
    'am': 1e-18,
    'zm': 1e-21,
    'ym': 1e-24,
    '\u00c5': 1e-10,
}


class OMETiffFileTileSource(TiffFileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to TIFF files.
    """

    cacheName = 'tilesource'
    name = 'ometiff'
    extensions = {
        None: SourcePriority.LOW,
        'tif': SourcePriority.MEDIUM,
        'tiff': SourcePriority.MEDIUM,
        'ome': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        'image/tiff': SourcePriority.MEDIUM,
        'image/x-tiff': SourcePriority.MEDIUM,
    }

    # The expect number of pixels that would need to be read to read the worst-
    # case tile.
    _maxUntiledChunk = 512 * 1024 * 1024

    def __init__(self, path, **kwargs):  # noqa
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        # Note this is the super of the parent class, not of this class.
        super(TiffFileTileSource, self).__init__(path, **kwargs)

        self._largeImagePath = str(self._getLargeImagePath())

        try:
            base = self.getTiffDir(0, mustBeTiled=None)
        except TiffError:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            msg = 'Not a recognized OME Tiff'
            raise TileSourceError(msg)
        info = getattr(base, '_description_record', None)
        self._associatedImages = {}
        if not info or not info.get('OME'):
            msg = 'Not an OME Tiff'
            raise TileSourceError(msg)
        self._omeinfo = info['OME']
        self._checkForOMEZLoop()
        try:
            self._parseOMEInfo()
        except KeyError:
            msg = 'Not a recognized OME Tiff'
            raise TileSourceError(msg)
        usesSubIfds = self._checkForSubIfds(base)
        omeimages = [
            entry['Pixels'] for entry in self._omeinfo['Image'] if
            len(entry['Pixels']['TiffData']) == len(self._omebase['TiffData'])]
        levels = [max(0, int(math.ceil(math.log(max(
            float(entry['SizeX']) / base.tileWidth,
            float(entry['SizeY']) / base.tileHeight)) / math.log(2))))
            for entry in omeimages]
        omebylevel = dict(zip(levels, omeimages, strict=False))
        self._omeLevels = [omebylevel.get(key) for key in range(max(omebylevel.keys()) + 1)]
        if base._tiffInfo.get('istiled'):
            if usesSubIfds:
                self._omeLevels = [None] * max(usesSubIfds) + [self._omeLevels[-1]]
            try:
                self._tiffDirectories = [
                    self.getTiffDir(int(entry['TiffData'][0].get('IFD', 0)))
                    if entry else None
                    for entry in self._omeLevels]
            except Exception as exc:
                msg = f'Cannot process OME tiff file: {exc}'
                raise TileSourceError(msg)
            if usesSubIfds:
                for lvl in usesSubIfds:
                    if self._tiffDirectories[lvl] is None:
                        self._tiffDirectories[lvl] = False
        else:
            try:
                self._tiffDirectories = [
                    self.getTiffDir(0, mustBeTiled=None)
                    if entry else None
                    for entry in self._omeLevels]
            except Exception as exc:
                msg = f'Cannot process OME tiff file: {exc}'
                raise TileSourceError(msg)
            self._checkForInefficientDirectories(warn=False)
            _maxChunk = min(base.imageWidth, base.tileWidth * self._skippedLevels ** 2) * \
                min(base.imageHeight, base.tileHeight * self._skippedLevels ** 2)
            if _maxChunk > self._maxUntiledChunk:
                msg = 'Untiled image is too large to access with the OME Tiff source'
                raise TileSourceError(msg)
        self.tileWidth = base.tileWidth
        self.tileHeight = base.tileHeight
        self.levels = len(self._tiffDirectories)
        self.sizeX = base.imageWidth
        self.sizeY = base.imageHeight

        # We can get the embedded images, but we don't currently use non-tiled
        # images as associated images.  This would require enumerating tiff
        # directories not mentioned by the ome list.
        self._checkForInefficientDirectories()

    def _checkForOMEZLoop(self):
        """
        Check if the OME description lists a Z-loop that isn't referenced by
        the frames or TiffData list and is present based on the number of tiff
        directories.  This can modify self._omeinfo.
        """
        info = self._omeinfo
        try:
            zloopinfo = info['Image']['Description'].split('Z Stack Loop: ')[1]
            zloop = int(zloopinfo.split()[0])
            stepinfo = zloopinfo.split('Step: ')[1].split()
            stepmm = float(stepinfo[0])
            stepmm *= {'mm': 1, '\xb5m': 0.001}[stepinfo[1]]
            planes = len(info['Image']['Pixels']['Plane'])
            for plane in info['Image']['Pixels']['Plane']:
                if int(plane.get('TheZ', 0)) != 0:
                    return
            if int(info['Image']['Pixels']['SizeZ']) != 1:
                return
        except Exception:
            return
        if zloop <= 1 or not stepmm or not planes:
            return
        if len(info['Image']['Pixels'].get('TiffData', {})):
            return
        expecteddir = planes * zloop
        try:
            lastdir = self.getTiffDir(expecteddir - 1, mustBeTiled=None)
            if not lastdir._tiffInfo.get('lastdirectory'):
                return
        except Exception:
            return
        tiffdata = []
        for z in range(zloop):
            for plane in info['Image']['Pixels']['Plane']:
                td = plane.copy()
                td['TheZ'] = str(z)
                # This position is probably wrong -- it seems like the
                # listed position is likely to be the center of the stack, not
                # the bottom, but we'd have to confirm it.
                td['PositionZ'] = str(float(td.get('PositionZ', 0)) + z * stepmm * 1000)
                tiffdata.append(td)
        info['Image']['Pixels']['TiffData'] = tiffdata
        info['Image']['Pixels']['Plane'] = tiffdata
        info['Image']['Pixels']['PlanesFromZloop'] = 'true'
        info['Image']['Pixels']['SizeZ'] = str(zloop)

    def _checkForSubIfds(self, base):
        """
        Check if the first ifd has sub-ifds.  If so, expect lower resolutions
        to be in subifds, not in primary ifds.

        :param base: base tiff directory
        :returns: either False if no subifds are lower resolution, or a
            dictionary of levels (keys) and values that are subifd numbers.
        """
        try:
            levels = int(max(0, math.ceil(max(
                math.log(float(base.imageWidth) / base.tileWidth),
                math.log(float(base.imageHeight) / base.tileHeight)) / math.log(2))) + 1)
            filled = {}
            for z in range(levels - 2, -1, -1):
                subdir = levels - 1 - z
                scale = int(2 ** subdir)
                try:
                    dir = self.getTiffDir(0, mustBeTiled=True, subDirectoryNum=subdir)
                except Exception:
                    continue
                if (dir is not None and
                        (dir.tileWidth in {base.tileWidth, dir.imageWidth}) and
                        (dir.tileHeight in {base.tileHeight, dir.imageHeight}) and
                        abs(dir.imageWidth * scale - base.imageWidth) <= scale and
                        abs(dir.imageHeight * scale - base.imageHeight) <= scale):
                    filled[z] = subdir
            if not len(filled):
                return False
            filled[levels - 1] = 0
            return filled
        except TiffError:
            return False

    def _parseOMEInfo(self):  # noqa
        if isinstance(self._omeinfo['Image'], dict):
            self._omeinfo['Image'] = [self._omeinfo['Image']]
        for img in self._omeinfo['Image']:
            if isinstance(img['Pixels'], list):
                msg = 'OME Tiff has multiple pixels'
                raise TileSourceError(msg)
            if isinstance(img['Pixels'].get('TiffData'), dict):
                img['Pixels']['TiffData'] = [img['Pixels']['TiffData']]
            if isinstance(img['Pixels'].get('Plane'), dict):
                img['Pixels']['Plane'] = [img['Pixels']['Plane']]
            if isinstance(img['Pixels'].get('Channels'), dict):
                img['Pixels']['Channels'] = [img['Pixels']['Channels']]
        try:
            self._omebase = self._omeinfo['Image'][0]['Pixels']
            if isinstance(self._omebase.get('Plane'), dict):
                self._omebase['Plane'] = [self._omebase['Plane']]
            if ((not len(self._omebase['TiffData']) or
                    len(self._omebase['TiffData']) == 1) and
                    (len(self._omebase.get('Plane', [])) or
                     len(self._omebase.get('Channel', [])))):
                if (not len(self._omebase['TiffData']) or
                        self._omebase['TiffData'][0] == {} or
                        int(self._omebase['TiffData'][0].get('PlaneCount', 0)) == 1):
                    planes = copy.deepcopy(self._omebase.get(
                        'Plane', self._omebase.get('Channel')))
                    if isinstance(planes, dict):
                        planes = [planes]
                        self._omebase['SizeC'] = 1
                    for idx, plane in enumerate(planes):
                        plane['IndexC'] = idx
                    self._omebase['TiffData'] = planes
                elif (int(self._omebase['TiffData'][0].get('PlaneCount', 0)) ==
                        len(self._omebase.get('Plane', self._omebase.get('Channel', [])))):
                    planes = copy.deepcopy(self._omebase.get('Plane', self._omebase.get('Channel')))
                    for idx, plane in enumerate(planes):
                        plane['IFD'] = plane.get(
                            'IFD', int(self._omebase['TiffData'][0].get('IFD', 0)) + idx)
                    self._omebase['TiffData'] = planes
            if isinstance(self._omebase['TiffData'], dict):
                self._omebase['TiffData'] = [self._omebase['TiffData']]
            if len({entry.get('UUID', {}).get('FileName', '')
                    for entry in self._omebase['TiffData']}) > 1:
                msg = 'OME Tiff references multiple files'
                raise TileSourceError(msg)
            if (len(self._omebase['TiffData']) ==
                    int(self._omebase['SizeT']) * int(self._omebase['SizeZ'])):
                self._omebase['SizeC'] = 1
                for img in self._omeinfo['Image'][1:]:
                    try:
                        if img['Name'] and img['Pixels']['TiffData'][0]['IFD']:
                            self._addAssociatedImage(
                                int(img['Pixels']['TiffData'][0]['IFD']),
                                None, None, img['Name'].split()[0])
                    except Exception:
                        pass
            elif len(self._omeinfo['Image']) > 1:
                multiple = False
                for img in self._omeinfo['Image'][1:]:
                    try:
                        bpix = self._omeinfo['Image'][0]['Pixels']
                        imgpix = img['Pixels']
                        if imgpix['SizeX'] == bpix['SizeX'] and imgpix['SizeY'] == bpix['SizeY']:
                            multiple = True
                            break
                    except Exception:
                        multiple = True
                if multiple:
                    # We should handle this as SizeXY
                    msg = 'OME Tiff references multiple images'
                    raise TileSourceError(msg)
            if (len(self._omebase['TiffData']) != int(self._omebase['SizeC']) *
                    int(self._omebase['SizeT']) * int(self._omebase['SizeZ']) or
                    len(self._omebase['TiffData']) != len(
                        self._omebase.get('Plane', self._omebase['TiffData']))):
                msg = 'OME Tiff contains frames that contain multiple planes'
                raise TileSourceError(msg)
        except (KeyError, ValueError, IndexError, TypeError):
            msg = 'OME Tiff does not contain an expected record'
            raise TileSourceError(msg)

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        result['frames'] = copy.deepcopy(self._omebase.get('Plane', self._omebase['TiffData']))
        channels = []
        for img in self._omeinfo['Image']:
            try:
                channels = [channel['Name'] for channel in img['Pixels']['Channel']]
                if len(channels) > 1:
                    break
            except Exception:
                pass
        if len(set(channels)) != len(channels) and (
                len(channels) <= 1 or len(channels) > len(result['frames'])):
            channels = []
        for k in {'C', 'Z', 'T'}:
            if (str(len(result['frames'])) == str(self._omebase.get('Size%s' % k)) and
                    len(result['frames']) > 1 and
                    result['frames'][0].get('Index%s' % k) is None):
                for idx in range(len(result['frames'])):
                    result['frames'][idx]['Index%s' % k] = idx
        # Standardize "TheX" to "IndexX" values
        reftbl = OrderedDict([
            ('TheC', 'IndexC'), ('TheZ', 'IndexZ'), ('TheT', 'IndexT'),
            ('FirstC', 'IndexC'), ('FirstZ', 'IndexZ'), ('FirstT', 'IndexT'),
        ])
        for frame in result['frames']:
            for key in reftbl:
                if key in frame and reftbl[key] not in frame:
                    if int(frame[key]) < len(result['frames']):
                        frame[reftbl[key]] = int(frame[key])
                frame.pop(key, None)
        self._addMetadataFrameInformation(result, channels)
        return result

    def _reduceInternalMetadata(self, result, entry, prefix='', refs=None):  # noqa
        starts = ['StructuredAnnotations:OriginalMetadata:Series 0 ',
                  'StructuredAnnotations:OriginalMetadata:']
        for start in starts:
            if prefix.startswith(start):
                prefix = prefix[len(start):]
        if isinstance(entry, dict):
            for key, val in entry.items():
                pkey = f'{prefix}:{key}'.strip(':')
                if pkey in starts or (pkey + ':') in starts:
                    pkey = ''
                if isinstance(val, dict):
                    if 'ID' in val and 'Value' in val:
                        self._reduceInternalMetadata(result, val['Value'], prefix, refs)
                    elif 'Key' in val and 'Value' in val:
                        rkey = f'{pkey}:{val["Key"]}'.strip(':')
                        result[rkey] = val['Value']
                        if refs is not None:
                            refs[rkey] = (entry, key, None, 'Value')
                    else:
                        self._reduceInternalMetadata(result, val, pkey, refs)
                elif isinstance(val, list):
                    for subidx, subval in enumerate(val):
                        if isinstance(subval, dict):
                            if 'ID' in subval and 'Value' in subval:
                                self._reduceInternalMetadata(result, subval['Value'], prefix, refs)
                            elif 'Key' in subval and 'Value' in subval:
                                rkey = f'{pkey}:{subval["Key"]}'
                                result[rkey] = subval['Value']
                                if refs is not None:
                                    refs[rkey] = (entry, key, subidx, 'Value')
                            else:
                                self._reduceInternalMetadata(
                                    result, subval, f'{pkey}:{subidx}'.strip(':'), refs)
                        elif not isinstance(subval, list):
                            rkey = f'{pkey}:{subidx}'.strip(':')
                            result[rkey] = subval
                            if refs is not None:
                                refs[rkey] = (entry, key, subidx, None)
                elif key == 'ID' and str(val).split(':')[0] in prefix:
                    continue
                elif val != '' and pkey:
                    result[pkey] = val
                    if refs is not None:
                        refs[pkey] = (entry, key, None, None)

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {'omeinfo': self._omeinfo}
        try:
            result['omereduced'] = {}
            self._reduceInternalMetadata(result['omereduced'], self._omeinfo)
        except Exception:
            pass
        return result

    def getNativeMagnification(self):
        """
        Get the magnification for the highest-resolution level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        result = super().getNativeMagnification()
        if result['mm_x'] is None and 'PhysicalSizeX' in self._omebase:
            result['mm_x'] = (
                float(self._omebase['PhysicalSizeX']) * 1e3 *
                _omeUnitsToMeters[self._omebase.get('PhysicalSizeXUnit', '\u00b5m')])
        if result['mm_y'] is None and 'PhysicalSizeY' in self._omebase:
            result['mm_y'] = (
                float(self._omebase['PhysicalSizeY']) * 1e3 *
                _omeUnitsToMeters[self._omebase.get('PhysicalSizeYUnit', '\u00b5m')])
        if not result.get('magnification') and result.get('mm_x'):
            result['magnification'] = 0.01 / result['mm_x']
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                sparseFallback=False, **kwargs):
        if ((z < 0 or z >= len(self._omeLevels) or (
                self._omeLevels[z] is not None and kwargs.get('frame') in (None, 0, '0', ''))) and
                not getattr(self, '_style', None)):
            return super().getTile(
                x, y, z, pilImageAllowed=pilImageAllowed,
                numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                **kwargs)
        frame = self._getFrame(**kwargs)
        if frame < 0 or frame >= len(self._omebase['TiffData']):
            msg = 'Frame does not exist'
            raise TileSourceError(msg)
        subdir = None
        if self._omeLevels[z] is not None:
            dirnum = int(self._omeLevels[z]['TiffData'][frame].get('IFD', frame))
        else:
            dirnum = int(self._omeLevels[-1]['TiffData'][frame].get('IFD', frame))
            subdir = self.levels - 1 - z
        dir = self._getDirFromCache(dirnum, subdir)
        if subdir:
            scale = int(2 ** subdir)
            if (dir is None or
                    (dir.tileWidth not in {self.tileWidth, dir.imageWidth}) or
                    (dir.tileHeight not in {self.tileHeight, dir.imageHeight}) or
                    abs(dir.imageWidth * scale - self.sizeX) > scale or
                    abs(dir.imageHeight * scale - self.sizeY) > scale):
                return super().getTile(
                    x, y, z, pilImageAllowed=pilImageAllowed,
                    numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                    **kwargs)
        try:
            tile = dir.getTile(x, y, asarray=numpyAllowed == 'always')
            format = 'JPEG'
            if isinstance(tile, PIL.Image.Image):
                format = TILE_FORMAT_PIL
            if isinstance(tile, np.ndarray):
                format = TILE_FORMAT_NUMPY
            return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                                    numpyAllowed, **kwargs)
        except InvalidOperationTiffError as e:
            raise TileSourceError(e.args[0])
        except IOTiffError as e:
            return self.getTileIOTiffError(
                x, y, z, pilImageAllowed=pilImageAllowed,
                numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                exception=e, **kwargs)

    def getPreferredLevel(self, level):
        """
        Given a desired level (0 is minimum resolution, self.levels - 1 is max
        resolution), return the level that contains actual data that is no
        lower resolution.

        :param level: desired level
        :returns level: a level with actual data that is no lower resolution.
        """
        level = max(0, min(level, self.levels - 1))
        baselevel = level
        while self._tiffDirectories[level] is None and level < self.levels - 1:
            try:
                dirnum = int(self._omeLevels[-1]['TiffData'][0].get('IFD', 0))
                subdir = self.levels - 1 - level
                if self._getDirFromCache(dirnum, subdir):
                    break
            except Exception:
                pass
            level += 1
        while level - baselevel > self._maxSkippedLevels:
            level -= self._maxSkippedLevels
        return level


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return OMETiffFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return OMETiffFileTileSource.canRead(*args, **kwargs)
