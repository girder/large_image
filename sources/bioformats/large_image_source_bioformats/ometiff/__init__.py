# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################
import six

from large_image.constants import SourcePriority
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.exceptions import TileSourceException

from ..base import BioFormatsFileTileSource

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
class OMETiffBioFormatsFileTileSource(BioFormatsFileTileSource):
    """
    Provides tile access to via Bio Formats for OME Tiff files
    """

    cacheName = 'tilesource'
    name = 'ometiff-bioformats'
    extensions = {
        None: SourcePriority.LOW,
        'ome.tif': SourcePriority.HIGH,
        'tif': SourcePriority.HIGH,
        'tiff': SourcePriority.HIGH,
        'ome': SourcePriority.PREFERRED,
    }

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictonary.
        """
        result = super(OMETiffBioFormatsFileTileSource, self).getMetadata()
        # We may want to reformat the frames to standardize this across sources
        result['frames'] = self._metadata.get('Plane', self._omebase['TiffData'])
        result['omeinfo'] = self._metadata
        return result

    def getNativeMagnification(self):
        """
        Get the magnification for the highest-resolution level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        result = super(OMETiffBioFormatsFileTileSource, self).getNativeMagnification()
        if result['mm_x'] is None and 'PhysicalSizeX' in self._metadata:
            result['mm_x'] = (
                float(self._metadata['PhysicalSizeX']) * 1e3 *
                _omeUnitsToMeters[self._metadata.get('PhysicalSizeXUnit', '\u00b5m')])
        if result['mm_y'] is None and 'PhysicalSizeY' in self._metadata:
            result['mm_y'] = (
                float(self._metadata['PhysicalSizeY']) * 1e3 *
                _omeUnitsToMeters[self._metadata.get('PhysicalSizeYUnit', '\u00b5m')])
        if not result.get('magnification') and result.get('mm_x'):
            result['magnification'] = 0.01 / result['mm_x']
        return result

    def computeTiles(self):
        self.tileWidth = int(self._metadata.get('TileWidth', min(self.sizeX, 256)))
        self.tileHeight = int(self._metadata.get('TileLength', min(self.sizeY, 256)))

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, mayRedirect=False, **kwargs):
        frame = int(kwargs['frame'])
        if frame < 0 or frame >= len(self._metadata['TiffData']):
            raise TileSourceException('Frame does not exist')

        return super(OMETiffBioFormatsFileTileSource, self).getTile(x, y, z, pilImageAllowed=False,
                                                                    mayRedirect=False, **kwargs)
