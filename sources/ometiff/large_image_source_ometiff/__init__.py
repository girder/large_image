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

import copy
import math
import numpy
import PIL.Image
import six
from collections import OrderedDict
from pkg_resources import DistributionNotFound, get_distribution
from six.moves import range

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority, TILE_FORMAT_PIL, TILE_FORMAT_NUMPY
from large_image.exceptions import TileSourceException

from large_image_source_tiff import TiffFileTileSource
from large_image_source_tiff.tiff_reader import TiledTiffDirectory, \
    InvalidOperationTiffException, TiffException, IOTiffException


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
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
    u'\u00b5m': 1e-6,
    'nm': 1e-9,
    'pm': 1e-12,
    'fm': 1e-15,
    'am': 1e-18,
    'zm': 1e-21,
    'ym': 1e-24,
    u'\u00c5': 1e-10,
}


@six.add_metaclass(LruCacheMetaclass)
class OMETiffFileTileSource(TiffFileTileSource):
    """
    Provides tile access to TIFF files.
    """

    cacheName = 'tilesource'
    name = 'ometifffile'
    extensions = {
        None: SourcePriority.LOW,
        'tif': SourcePriority.MEDIUM,
        'tiff': SourcePriority.MEDIUM,
        'ome': SourcePriority.PREFERRED,
    }

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super(TiffFileTileSource, self).__init__(path, **kwargs)

        largeImagePath = self._getLargeImagePath()

        try:
            base = TiledTiffDirectory(largeImagePath, 0, mustBeTiled=None)
        except TiffException:
            raise TileSourceException('Not a recognized OME Tiff')
        info = getattr(base, '_description_record', None)
        if not info or not info.get('OME'):
            raise TileSourceException('Not an OME Tiff')
        self._omeinfo = info['OME']
        self._checkForOMEZLoop(largeImagePath)
        self._parseOMEInfo()
        omeimages = [
            entry['Pixels'] for entry in self._omeinfo['Image'] if
            len(entry['Pixels']['TiffData']) == len(self._omebase['TiffData'])]
        levels = [max(0, int(math.ceil(math.log(max(
            float(entry['SizeX']) / base.tileWidth,
            float(entry['SizeY']) / base.tileHeight)) / math.log(2))))
            for entry in omeimages]
        omebylevel = dict(zip(levels, omeimages))
        self._omeLevels = [omebylevel.get(key) for key in range(max(omebylevel.keys()) + 1)]
        if base._tiffInfo.get('istiled'):
            self._tiffDirectories = [
                TiledTiffDirectory(largeImagePath, int(entry['TiffData'][0]['IFD']))
                if entry else None
                for entry in self._omeLevels]
        else:
            self._tiffDirectories = [
                TiledTiffDirectory(largeImagePath, 0, mustBeTiled=None)
                if entry else None
                for entry in self._omeLevels]
        self._directoryCache = {}
        self._directoryCacheMaxSize = max(20, len(self._omebase['TiffData']) * 3)
        self.tileWidth = base.tileWidth
        self.tileHeight = base.tileHeight
        self.levels = len(self._tiffDirectories)
        self.sizeX = base.imageWidth
        self.sizeY = base.imageHeight

        # We can get the embedded images, but we don't currently use non-tiled
        # images as associated images.  This would require enumerating tiff
        # directories not mentioned by the ome list.
        self._associatedImages = {}

    def _checkForOMEZLoop(self, largeImagePath):
        """
        Check if the OME description lists a Z-loop that isn't referenced by
        the frames or TiffData list and is present based on the number of tiff
        directories.  This can modify self._omeinfo.

        :param largeImagePath: used for checking for the maximum directory.
        """
        info = self._omeinfo
        try:
            zloopinfo = info['Image']['Description'].split('Z Stack Loop: ')[1]
            zloop = int(zloopinfo.split()[0])
            stepinfo = zloopinfo.split('Step: ')[1].split()
            stepmm = float(stepinfo[0])
            stepmm *= {u'mm': 1, u'\xb5m': 0.001}[stepinfo[1]]
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
            lastdir = TiledTiffDirectory(largeImagePath, expecteddir - 1, mustBeTiled=None)
            if not lastdir._tiffFile.lastdirectory():
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

    def _parseOMEInfo(self):
        if isinstance(self._omeinfo['Image'], dict):
            self._omeinfo['Image'] = [self._omeinfo['Image']]
        for img in self._omeinfo['Image']:
            if isinstance(img['Pixels'].get('TiffData'), dict):
                img['Pixels']['TiffData'] = [img['Pixels']['TiffData']]
            if isinstance(img['Pixels'].get('Plane'), dict):
                img['Pixels']['Plane'] = [img['Pixels']['Plane']]
        try:
            self._omebase = self._omeinfo['Image'][0]['Pixels']
            if ((not len(self._omebase['TiffData']) or
                    len(self._omebase['TiffData']) == 1) and
                    len(self._omebase['Plane'])):
                if not len(self._omebase['TiffData']) or self._omebase['TiffData'][0] == {}:
                    self._omebase['TiffData'] = self._omebase['Plane']
                elif (int(self._omebase['TiffData'][0].get('PlaneCount', 0)) ==
                        len(self._omebase['Plane'])):
                    planes = copy.deepcopy(self._omebase['Plane'])
                    for idx, plane in enumerate(planes):
                        plane['IFD'] = plane.get(
                            'IFD', int(self._omebase['TiffData'][0].get('IFD', 0)) + idx)
                    self._omebase['TiffData'] = planes
            if len({entry.get('UUID', {}).get('FileName', '')
                    for entry in self._omebase['TiffData']}) > 1:
                raise TileSourceException('OME Tiff references multiple files')
            if (len(self._omebase['TiffData']) != int(self._omebase['SizeC']) *
                    int(self._omebase['SizeT']) * int(self._omebase['SizeZ']) or
                    len(self._omebase['TiffData']) != len(
                        self._omebase.get('Plane', self._omebase['TiffData']))):
                raise TileSourceException('OME Tiff contains frames that contain multiple planes')
        except (KeyError, ValueError, IndexError):
            raise TileSourceException('OME Tiff does not contain an expected record')

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictonary.
        """
        result = super(OMETiffFileTileSource, self).getMetadata()
        result['frames'] = copy.deepcopy(self._omebase.get('Plane', self._omebase['TiffData']))
        channels = []
        for img in self._omeinfo['Image']:
            try:
                channels = [channel['Name'] for channel in img['Pixels']['Channel']]
                if len(channels) > 1:
                    break
            except Exception:
                pass
        if len(set(channels)) != len(channels):
            channels = []
        # Standardize "TheX" to "IndexX" values
        reftbl = OrderedDict([
            ('TheC', 'IndexC'), ('TheZ', 'IndexZ'), ('TheT', 'IndexT'),
            ('FirstC', 'IndexC'), ('FirstZ', 'IndexZ'), ('FirstT', 'IndexT'),
        ])
        for frame in result['frames']:
            for key in reftbl:
                if key in frame and not reftbl[key] in frame:
                    frame[reftbl[key]] = int(frame[key])
        self._addMetadataFrameInformation(result, channels)
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        result['omeinfo'] = self._omeinfo
        return result

    def getNativeMagnification(self):
        """
        Get the magnification for the highest-resolution level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        result = super(OMETiffFileTileSource, self).getNativeMagnification()
        if result['mm_x'] is None and 'PhysicalSizeX' in self._omebase:
            result['mm_x'] = (
                float(self._omebase['PhysicalSizeX']) * 1e3 *
                _omeUnitsToMeters[self._omebase.get('PhysicalSizeXUnit', u'\u00b5m')])
        if result['mm_y'] is None and 'PhysicalSizeY' in self._omebase:
            result['mm_y'] = (
                float(self._omebase['PhysicalSizeY']) * 1e3 *
                _omeUnitsToMeters[self._omebase.get('PhysicalSizeYUnit', u'\u00b5m')])
        if not result.get('magnification') and result.get('mm_x'):
            result['magnification'] = 0.01 / result['mm_x']
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                sparseFallback=False, **kwargs):
        if (z < 0 or z >= len(self._omeLevels) or self._omeLevels[z] is None or
                kwargs.get('frame') in (None, 0, '0', '')):
            return super(OMETiffFileTileSource, self).getTile(
                x, y, z, pilImageAllowed=pilImageAllowed,
                numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                **kwargs)
        frame = int(kwargs['frame'])
        if frame < 0 or frame >= len(self._omebase['TiffData']):
            raise TileSourceException('Frame does not exist')
        dirnum = int(self._omeLevels[z]['TiffData'][frame].get('IFD', frame))
        if dirnum in self._directoryCache:
            dir = self._directoryCache[dirnum]
        else:
            if len(self._directoryCache) >= self._directoryCacheMaxSize:
                self._directoryCache = {}
            dir = TiledTiffDirectory(self._getLargeImagePath(), dirnum, mustBeTiled=None)
            self._directoryCache[dirnum] = dir
        try:
            tile = dir.getTile(x, y)
            format = 'JPEG'
            if isinstance(tile, PIL.Image.Image):
                format = TILE_FORMAT_PIL
            if isinstance(tile, numpy.ndarray):
                format = TILE_FORMAT_NUMPY
            return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                                    numpyAllowed, **kwargs)
        except InvalidOperationTiffException as e:
            raise TileSourceException(e.args[0])
        except IOTiffException as e:
            return self.getTileIOTiffException(
                x, y, z, pilImageAllowed=pilImageAllowed,
                numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                exception=e, **kwargs)
