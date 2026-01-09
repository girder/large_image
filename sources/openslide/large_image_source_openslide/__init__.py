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

import contextlib
import importlib.metadata
import io
import math
import os

import numpy as np
import openslide
import PIL
import tifftools

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource, nearPowerOfTwo

with contextlib.suppress(importlib.metadata.PackageNotFoundError):
    __version__ = importlib.metadata.version(__name__)


class OpenslideFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to SVS files and other files the openslide library can
    read.
    """

    cacheName = 'tilesource'
    name = 'openslide'
    extensions = {
        None: SourcePriority.MEDIUM,
        'bif': SourcePriority.LOW,  # Ventana
        'czi': SourcePriority.PREFERRED,
        'dcm': SourcePriority.MEDIUM,  # DICOM
        'ini': SourcePriority.LOW,  # Part of mrxs
        'mrxs': SourcePriority.PREFERRED,  # MIRAX
        'ndpi': SourcePriority.PREFERRED,  # Hamamatsu
        'scn': SourcePriority.LOW,  # Leica
        'svs': SourcePriority.HIGH,
        'svslide': SourcePriority.PREFERRED,
        'tif': SourcePriority.MEDIUM,
        'tiff': SourcePriority.MEDIUM,
        'vms': SourcePriority.HIGH,  # Hamamatsu
        'vmu': SourcePriority.HIGH,  # Hamamatsu
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/czi': SourcePriority.PREFERRED,
        'application/dicom': SourcePriority.MEDIUM,
        'image/mirax': SourcePriority.PREFERRED,  # MIRAX
        'image/tiff': SourcePriority.MEDIUM,
        'image/x-tiff': SourcePriority.MEDIUM,
    }

    def __init__(self, path, **kwargs):  # noqa
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = str(self._getLargeImagePath())

        try:
            self._openslide = openslide.OpenSlide(self._largeImagePath)
        except openslide.lowlevel.OpenSlideUnsupportedFormatError:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            msg = 'File cannot be opened via OpenSlide.'
            raise TileSourceError(msg)
        except openslide.lowlevel.OpenSlideError:
            msg = 'File will not be opened via OpenSlide.'
            raise TileSourceError(msg)
        try:
            self._tiffinfo = tifftools.read_tiff(self._largeImagePath)
            if tifftools.Tag.ICCProfile.value in self._tiffinfo['ifds'][0]['tags']:
                self._iccprofiles = [self._tiffinfo['ifds'][0]['tags'][
                    tifftools.Tag.ICCProfile.value]['data']]
        except Exception:
            pass
        if hasattr(self, '_tiffinfo'):
            for ifd in self._tiffinfo['ifds']:
                if (tifftools.Tag.NDPI_FOCAL_PLANE.value in ifd['tags'] and
                        ifd['tags'][tifftools.Tag.NDPI_FOCAL_PLANE.value]['data'][0] != 0):
                    msg = ('File will not be opened via OpenSlide; '
                           'non-zero focal planes would be missed.')
                    raise TileSourceError(msg)

        svsAvailableLevels = self._getAvailableLevels(self._largeImagePath)
        if not len(svsAvailableLevels):
            msg = 'OpenSlide image size is invalid.'
            raise TileSourceError(msg)
        self.sizeX = svsAvailableLevels[0]['width']
        self.sizeY = svsAvailableLevels[0]['height']
        if (self.sizeX != self._openslide.dimensions[0] or
                self.sizeY != self._openslide.dimensions[1]):
            msg = ('OpenSlide reports a dimension of %d x %d, but base layer '
                   'has a dimension of %d x %d -- using base layer '
                   'dimensions.' % (
                       self._openslide.dimensions[0],
                       self._openslide.dimensions[1], self.sizeX, self.sizeY))
            self.logger.info(msg)

        self._getTileSize()

        self.levels = int(math.ceil(max(
            math.log(float(self.sizeX) / self.tileWidth),
            math.log(float(self.sizeY) / self.tileHeight)) / math.log(2))) + 1
        if self.levels < 1:
            msg = 'OpenSlide image must have at least one level.'
            raise TileSourceError(msg)
        self._svslevels = []
        # Precompute which SVS level should be used for our tile levels.  SVS
        # level 0 is the maximum resolution.  The SVS levels are in descending
        # resolution and, we assume, are powers of two in scale.  For each of
        # our levels (where 0 is the minimum resolution), find the lowest
        # resolution SVS level that contains at least as many pixels.  If this
        # is not the same scale as we expect, note the scale factor so we can
        # load an appropriate area and scale it to the tile size later.
        maxSize = 16384   # This should probably be based on available memory
        for level in range(self.levels):
            levelpow = 2 ** (self.levels - 1 - level)
            levelW = max(1, self.sizeX / levelpow)
            levelH = max(1, self.sizeY / levelpow)
            # bestlevel and scale will be the picked svs level and the scale
            # between that level and what we really wanted.  We expect scale to
            # always be a positive integer power of two.
            bestlevel = svsAvailableLevels[0]['level']
            scale = 1
            svsscale = 0
            for svslevel in range(len(svsAvailableLevels)):
                if (svsAvailableLevels[svslevel]['width'] < levelW - 1 or
                        svsAvailableLevels[svslevel]['height'] < levelH - 1):
                    break
                bestlevel = svsAvailableLevels[svslevel]['level']
                scale = int(round(svsAvailableLevels[svslevel]['width'] / levelW))
                svsscale = svsAvailableLevels[svslevel].get('downsample', 0)
            # If there are no tiles at a particular level, we have to read a
            # larger area of a higher resolution level.  If such an area would
            # be excessively large, we could have memory issues, so raise an
            # error.
            if (self.tileWidth * scale > maxSize or
                    self.tileHeight * scale > maxSize):
                msg = ('OpenSlide has no small-scale tiles (level %d is at %d '
                       'scale)' % (level, scale))
                self.logger.info(msg)
                raise TileSourceError(msg)
            self._svslevels.append({
                'svslevel': bestlevel,
                'scale': scale,
                'svsscale': ((svsscale / levelpow) if svsscale else 1) * scale,
            })
        self._bounds = None
        try:
            bounds = {
                'x': int(self._openslide.properties[openslide.PROPERTY_NAME_BOUNDS_X]),
                'y': int(self._openslide.properties[openslide.PROPERTY_NAME_BOUNDS_Y]),
                'width': int(self._openslide.properties[openslide.PROPERTY_NAME_BOUNDS_WIDTH]),
                'height': int(self._openslide.properties[openslide.PROPERTY_NAME_BOUNDS_HEIGHT]),
            }
            if (
                bounds['x'] >= 0 and bounds['width'] > 0 and
                bounds['x'] + bounds['width'] <= self.sizeX and
                bounds['y'] >= 0 and bounds['height'] > 0 and
                bounds['y'] + bounds['height'] <= self.sizeY and
                (bounds['width'] < self.sizeX or bounds['height'] < self.sizeY)
            ):
                self._bounds = bounds
                self.sizeX, self.sizeY = bounds['width'], bounds['height']
                prevlevels = self.levels
                self.levels = int(math.ceil(max(
                    math.log(float(self.sizeX) / self.tileWidth),
                    math.log(float(self.sizeY) / self.tileHeight)) / math.log(2))) + 1
                self._svslevels = self._svslevels[prevlevels - self.levels:]
        except Exception:
            pass
        try:
            self._background = tuple(int(
                self._openslide.properties['openslide.background-color']
                [i * 2:i * 2 + 2], 16) for i in range(3))
        except Exception:
            self._background = None
        self._populatedLevels = len({l['svslevel'] for l in self._svslevels})

    def _getTileSize(self):
        """
        Get the tile size.  The tile size isn't in the official openslide
        interface documentation, but every example has the tile size in the
        properties.  If the tile size has an excessive aspect ratio or isn't
        set, fall back to a default of 256 x 256.  The read_region function
        abstracts reading the tiles, so this may be less efficient, but will
        still work.
        """
        # Try to read it, but fall back to 256 if it isn't set.
        width = height = 256
        with contextlib.suppress(ValueError, KeyError):
            width = int(self._openslide.properties[
                'openslide.level[0].tile-width'])
        with contextlib.suppress(ValueError, KeyError):
            height = int(self._openslide.properties[
                'openslide.level[0].tile-height'])
        # If the tile size is too small (<4) or wrong (<=0), use a default value
        if width < 4:
            width = 256
        if height < 4:
            height = 256
        # If the tile has an excessive aspect ratio, use default values
        if max(width, height) / min(width, height) >= 4:
            width = height = 256
        # Don't let tiles be bigger than the whole image.
        self.tileWidth = min(width, self.sizeX)
        self.tileHeight = min(height, self.sizeY)

    def _getAvailableLevels(self, path):
        """
        Some SVS files (notably some NDPI variants) have levels that cannot be
        read.  Get a list of levels, check that each is at least potentially
        readable, and return a list of these sorted highest-resolution first.

        :param path: the path of the SVS file.  After a failure, the file is
            reopened to reset the error state.
        :returns: levels.  A list of valid levels, each of which is a
            dictionary of level (the internal 0-based level number), width, and
            height.
        """
        levels = []
        svsLevelDimensions = self._openslide.level_dimensions

        for svslevel in range(len(svsLevelDimensions)):
            try:
                self._openslide.read_region((0, 0), svslevel, (1, 1))
                level = {
                    'level': svslevel,
                    'width': svsLevelDimensions[svslevel][0],
                    'height': svsLevelDimensions[svslevel][1],
                }
                with contextlib.suppress(Exception):
                    level['downsample'] = self._openslide.level_downsamples[svslevel]
                if level['width'] > 0 and level['height'] > 0:
                    # add to the list so that we can sort by resolution and
                    # then by earlier entries
                    levels.append((level['width'] * level['height'], -len(levels), level))
            except openslide.lowlevel.OpenSlideError:
                self._openslide = openslide.OpenSlide(path)
        # sort highest resolution first.
        levels = [entry[-1] for entry in sorted(levels, reverse=True, key=lambda x: x[:-1])]
        # Discard levels that are not a power-of-two compared to the highest
        # resolution level.
        levels = [entry for entry in levels if
                  nearPowerOfTwo(levels[0]['width'], entry['width']) and
                  nearPowerOfTwo(levels[0]['height'], entry['height'])]
        return levels

    def _nonemptyLevelsList(self, frame=0):
        """
        Return a list of one value per level where the value is None if the
        level does not exist in the file and any other value if it does.

        :param frame: the frame number.
        :returns: a list of levels length.
        """
        return [True if l['scale'] == 1 else None for l in self._svslevels]

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        try:
            mag = self._openslide.properties[
                openslide.PROPERTY_NAME_OBJECTIVE_POWER]
            mag = float(mag) if mag else None
        except (KeyError, ValueError, openslide.lowlevel.OpenSlideError):
            mag = None
        try:
            mm_x = float(self._openslide.properties[
                openslide.PROPERTY_NAME_MPP_X]) * 0.001
            mm_y = float(self._openslide.properties[
                openslide.PROPERTY_NAME_MPP_Y]) * 0.001
        except Exception:
            mm_x = mm_y = None
        # Estimate the magnification if we don't have a direct value
        if mag is None and mm_x is not None:
            mag = 0.01 / mm_x
        return {
            'magnification': mag,
            'mm_x': mm_x,
            'mm_y': mm_y,
        }

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        results = {'openslide': {}}
        for key in self._openslide.properties:
            results['openslide'][key] = self._openslide.properties[key]
            if key == 'openslide.comment':
                leader = self._openslide.properties[key].split('\n', 1)[0].strip()
                if 'aperio' in leader.lower():
                    results['aperio_version'] = leader
        return results

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        self._xyzInRange(x, y, z)
        svslevel = self._svslevels[z]
        # When we read a region from the SVS, we have to ask for it in the
        # SVS level 0 coordinate system.  Our x and y is in tile space at the
        # specified z level, so the offset in SVS level 0 coordinates has to be
        # scaled by the tile size and by the z level.
        scale = 2 ** (self.levels - 1 - z)
        offsetx = x * self.tileWidth * scale
        offsety = y * self.tileHeight * scale
        if self._bounds is not None:
            offsetx += self._bounds['x'] // svslevel['scale']
            offsety += self._bounds['y'] // svslevel['scale']
        # We ask to read an area that will cover the tile at the z level.  The
        # scale we computed in the __init__ process for this svs level tells
        # how much larger a region we need to read.
        if svslevel['scale'] > 2 ** self._maxSkippedLevels:
            tile, format = self._getTileFromEmptyLevel(x, y, z, **kwargs)
        else:
            retries = 3
            svsTileWidth = self.tileWidth * svslevel['scale']
            svsTileHeight = self.tileHeight * svslevel['scale']
            # Peculiarly, openslide has a "downsample" factor which isn't the
            # power of 2 one would expect.  This is computed based on the
            # actual dimensions of levels, but since higher-resolution levels
            # are not fully populated at the right and bottom, this ends up
            # with not the actual downsampling, but some slightly higher number
            # (e.g., 16.0018 rather than 16).  Internally, when asking for a
            # region for anything other than the maximum resolution lever, the
            # openslide library is passed coordinates in what _seems_ to be
            # base image coordinates, but is actually inflated by the ratio of
            # their downsample value and the actual downsample value (e.g.,
            # 16.0018 / 16).  We multiple our values by this ratio so when
            # openslide misapplies its downsampling we get the region we
            # actually want
            if svslevel['svsscale'] != 1:
                offsetx = int(round(offsetx * svslevel['svsscale']))
                offsety = int(round(offsety * svslevel['svsscale']))
                svsTileWidth = int(round(svsTileWidth * svslevel['svsscale']))
                svsTileHeight = int(round(svsTileHeight * svslevel['svsscale']))
            while retries > 0:
                try:
                    tile = self._openslide.read_region(
                        (offsetx, offsety), svslevel['svslevel'],
                        (svsTileWidth, svsTileHeight))
                    format = TILE_FORMAT_PIL
                    break
                except openslide.lowlevel.OpenSlideError as exc:
                    self._largeImagePath = str(self._getLargeImagePath())
                    msg = (
                        'Failed to get OpenSlide region '
                        f'({exc} on {self._largeImagePath}: {self}).')
                    self.logger.info(msg)
                    # Reopen handle after a lowlevel error
                    try:
                        self._openslide = openslide.OpenSlide(self._largeImagePath)
                    except Exception:
                        raise TileSourceError(msg)
                    retries -= 1
                    if retries <= 0:
                        raise TileSourceError(msg)
            if tile.mode == 'RGBA' and self._background:
                tile = np.array(tile)
                tile[tile[:, :, -1] == 0, :3] = self._background
                tile = PIL.Image.fromarray(tile, 'RGBA')
            # Always scale to the svs level 0 tile size.
            if svslevel['scale'] != 1:
                tile = tile.resize((self.tileWidth, self.tileHeight),
                                   getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)
        return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                                numpyAllowed, **kwargs)

    def getPreferredLevel(self, level):
        """
        Given a desired level (0 is minimum resolution, self.levels - 1 is max
        resolution), return the level that contains actual data that is no
        lower resolution.

        :param level: desired level
        :returns level: a level with actual data that is no lower resolution.
        """
        level = max(0, min(level, self.levels - 1))
        scale = self._svslevels[level]['scale']
        while scale > 1:
            level += 1
            scale /= 2
        return level

    def _getAssociatedImagesDict(self):
        images = {}
        try:
            for key in self._openslide.associated_images:
                images[key] = 'openslide'
        except openslide.lowlevel.OpenSlideError:
            pass
        if hasattr(self, '_tiffinfo'):
            vendor = self._openslide.properties['openslide.vendor']
            for ifdidx, ifd in enumerate(self._tiffinfo['ifds']):
                key = None
                if vendor == 'hamamatsu':
                    if tifftools.Tag.NDPI_SOURCELENS.value in ifd['tags']:
                        lens = ifd['tags'][tifftools.Tag.NDPI_SOURCELENS.value]['data'][0]
                        key = {-1: 'macro', -2: 'nonempty'}.get(lens)
                elif vendor == 'aperio':
                    if (ifd['tags'].get(tifftools.Tag.NewSubfileType.value) and
                            ifd['tags'][tifftools.Tag.NewSubfileType.value]['data'][0] &
                            tifftools.Tag.NewSubfileType.bitfield.ReducedImage.value):
                        key = ('label' if ifd['tags'][
                               tifftools.Tag.NewSubfileType.value]['data'][0] ==
                               tifftools.Tag.NewSubfileType.bitfield.ReducedImage.value
                               else 'macro')
                if key and key not in images:
                    images[key] = ifdidx
        return images

    def getAssociatedImagesList(self):
        """
        Get a list of all associated images.

        :return: the list of image keys.
        """
        return sorted(self._getAssociatedImagesDict().keys())

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        images = self._getAssociatedImagesDict()
        if imageKey not in images:
            return None
        if images[imageKey] == 'openslide':
            try:
                return self._openslide.associated_images[imageKey]
            except openslide.lowlevel.OpenSlideError:
                # Reopen handle after a lowlevel error
                self._openslide = openslide.OpenSlide(self._largeImagePath)
                return None
        tiff_buffer = io.BytesIO()
        ifd = self._tiffinfo['ifds'][images[imageKey]]
        if (tifftools.Tag.Photometric.value in ifd['tags'] and
                ifd['tags'][tifftools.Tag.Photometric.value]['data'][0] ==
                tifftools.constants.Photometric.RGB and
                tifftools.Tag.SamplesPerPixel.value in ifd['tags'] and
                ifd['tags'][tifftools.Tag.SamplesPerPixel.value]['data'][0] == 1):
            ifd['tags'][tifftools.Tag.Photometric.value]['data'][
                0] = tifftools.constants.Photometric.MinIsBlack
        tifftools.write_tiff(ifd, tiff_buffer)
        return PIL.Image.open(tiff_buffer)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return OpenslideFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return OpenslideFileTileSource.canRead(*args, **kwargs)
