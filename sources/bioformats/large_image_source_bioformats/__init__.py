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

# This tile sources uses javabridge to communicate between python and java.  It
# requires some version of java's jvm to be available (see
# https://jdk.java.net/archive/).  It uses the python-bioformats wheel to get
# the bioformats JAR file.  A later version may be desirable (see
# https://www.openmicroscopy.org/bio-formats/downloads/).  See
# https://downloads.openmicroscopy.org/bio-formats/5.1.5/api/loci/formats/
#   IFormatReader.html for interface details.

import atexit
import bioformats
import bioformats.log4j
import javabridge
import math
import numpy
import os
import threading
import types

from pkg_resources import DistributionNotFound, get_distribution

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority, TILE_FORMAT_NUMPY
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource, nearPowerOfTwo
import large_image.tilesource.base


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


_javabridgeStarted = None
_openImages = []


config.ConfigValues['source_bioformats_ignored_extensions'] = '.jpg,.jpeg,.jpe,.png,.tif,.tiff'


def _monitor_thread():
    main_thread = threading.main_thread()
    main_thread.join()
    if len(_openImages):
        try:
            javabridge.attach()
            while len(_openImages):
                source = _openImages.pop()
                try:
                    source._bioimage.close()
                except Exception:
                    pass
                source._bioimage = None
        finally:
            if javabridge.get_env():
                javabridge.detach()
    _stopJavabridge()


def _startJavabridge(logger):
    global _javabridgeStarted

    if _javabridgeStarted is None:
        # We need something to wake up at exit and shut things down
        monitor = threading.Thread(target=_monitor_thread)
        monitor.daemon = True
        monitor.start()
        try:
            javabridge.start_vm(class_path=bioformats.JARS, run_headless=True)
            # As of bioformat 4.0.0, org.apache.log4j isn't in the bundled
            # jar file, so setting log levels just produces needless warnings.
            # bioformats.log4j.basic_config()
            # javabridge.JClassWrapper('loci.common.Log4jTools').setRootLevel(
            #     logging.getLevelName(logger.level))
            atexit.register(_stopJavabridge)
            logger.info('Started JVM for Bioformats tile source.')
            _javabridgeStarted = True
        except RuntimeError as exc:
            logger.exception('Cannot start JVM for Bioformats tile source.', exc)
            _javabridgeStarted = False
    return _javabridgeStarted


def _stopJavabridge(*args, **kwargs):
    global _javabridgeStarted

    javabridge.kill_vm()
    _javabridgeStarted = None


class BioformatsFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to via Bioformats.
    """

    cacheName = 'tilesource'
    name = 'bioformats'
    extensions = {
        None: SourcePriority.FALLBACK,
        'czi': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/czi': SourcePriority.PREFERRED,
    }

    # If frames are smaller than this they are served as single tiles, which
    # can be more efficient than handling multiple tiles.
    _singleTileThreshold = 2048
    _tileSize = 512
    _associatedImageMaxSize = 8192

    def __init__(self, path, **kwargs):  # noqa
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: the associated file path.
        :param maxSize: either a number or an object with {'width': (width),
            'height': height} in pixels.  If None, the default max size is
            used.
        """
        super().__init__(path, **kwargs)

        largeImagePath = self._getLargeImagePath()

        ext = os.path.splitext(largeImagePath)[1]
        if not ext:
            raise TileSourceException(
                'File cannot be opened via bioformats because it has no '
                'extension to specify the file type (%s).' % largeImagePath)
        if ext.lower() in (config.getConfig(
                'source_bioformats_ignored_extensions') or '.png').split(','):
            raise TileSourceException('File will not be opened by bioformats reader')

        if not _startJavabridge(self.logger):
            raise TileSourceException(
                'File cannot be opened by bioformats reader because javabridge failed to start')

        self._tileLock = threading.RLock()

        try:
            javabridge.attach()
            try:
                self._bioimage = bioformats.ImageReader(largeImagePath)
            except AttributeError as exc:
                self.logger.debug('File cannot be opened via Bioformats. (%r)' % exc)
                raise TileSourceException('File cannot be opened via Bioformats. (%r)' % exc)
            _openImages.append(self)

            rdr = self._bioimage.rdr
            # Bind additional functions not done by bioformats module.
            # Functions are listed at https://downloads.openmicroscopy.org
            # //bio-formats/5.1.5/api/loci/formats/IFormatReader.html
            for (name, params, desc) in [
                ('getBitsPerPixel', '()I', 'Get the number of bits per pixel'),
                ('getEffectiveSizeC', '()I', 'effectiveC * Z * T = imageCount'),
                ('isNormalized', '()Z', 'Is float data normalized'),
                ('isMetadataComplete', '()Z', 'True if metadata is completely parsed'),
                ('getDomains', '()[Ljava/lang/String;', 'Get a list of domains'),
                ('getZCTCoords', '(I)[I', 'Gets the Z, C and T coordinates '
                 '(real sizes) corresponding to the given rasterized index value.'),
                ('getOptimalTileWidth', '()I', 'the optimal sub-image width '
                 'for use with openBytes'),
                ('getOptimalTileHeight', '()I', 'the optimal sub-image height '
                 'for use with openBytes'),
                ('getResolutionCount', '()I', 'The number of resolutions for '
                 'the current series'),
                ('setResolution', '(I)V', 'Set the resolution level'),
                ('getResolution', '()I', 'The current resolution level'),
                ('hasFlattenedResolutions', '()Z', 'True if resolutions have been flattened'),
                ('setFlattenedResolutions', '(Z)V', 'Set if resolution should be flattened'),
            ]:
                setattr(rdr, name, types.MethodType(
                    javabridge.jutil.make_method(name, params, desc), rdr))
            # rdr.setFlattenedResolutions(False)
            self._metadata = {
                'dimensionOrder': rdr.getDimensionOrder(),
                'metadata': javabridge.jdictionary_to_string_dictionary(
                    rdr.getMetadata()),
                'seriesMetadata': javabridge.jdictionary_to_string_dictionary(
                    rdr.getSeriesMetadata()),
                'seriesCount': rdr.getSeriesCount(),
                'imageCount': rdr.getImageCount(),
                'rgbChannelCount': rdr.getRGBChannelCount(),
                'sizeColorPlanes': rdr.getSizeC(),
                'sizeT': rdr.getSizeT(),
                'sizeZ': rdr.getSizeZ(),
                'sizeX': rdr.getSizeX(),
                'sizeY': rdr.getSizeY(),
                'pixelType': rdr.getPixelType(),
                'isLittleEndian': rdr.isLittleEndian(),
                'isRGB': rdr.isRGB(),
                'isInterleaved': rdr.isInterleaved(),
                'isIndexed': rdr.isIndexed(),
                'bitsPerPixel': rdr.getBitsPerPixel(),
                'sizeC': rdr.getEffectiveSizeC(),
                'normalized': rdr.isNormalized(),
                'metadataComplete': rdr.isMetadataComplete(),
                # 'domains': rdr.getDomains(),
                'optimalTileWidth': rdr.getOptimalTileWidth(),
                'optimalTileHeight': rdr.getOptimalTileHeight(),
                'resolutionCount': rdr.getResolutionCount(),
                'flattenedResolutions': rdr.hasFlattenedResolutions(),
            }
            self._checkSeries(rdr)
            bmd = bioformats.metadatatools.MetadataRetrieve(self._bioimage.metadata)
            try:
                self._metadata['channelNames'] = [
                    bmd.getChannelName(0, c) or bmd.getChannelID(0, c)
                    for c in range(self._metadata['sizeColorPlanes'])]
            except Exception:
                self._metadata['channelNames'] = []
            for key in ['sizeXY', 'sizeC', 'sizeZ', 'sizeT']:
                if not isinstance(self._metadata[key], int) or self._metadata[key] < 1:
                    self._metadata[key] = 1
            self.sizeX = self._metadata['sizeX']
            self.sizeY = self._metadata['sizeY']
            self._computeTiles()
            self._computeLevels()
            self._computeMagnification()
        except javabridge.JavaException as exc:
            es = javabridge.to_string(exc.throwable)
            self.logger.debug('File cannot be opened via Bioformats. (%s)' % es)
            raise TileSourceException('File cannot be opened via Bioformats. (%s)' % es)
        except AttributeError:
            self.logger.exception('The bioformats reader threw an unhandled exception.')
            raise TileSourceException('The bioformats reader threw an unhandled exception.')
        finally:
            if javabridge.get_env():
                javabridge.detach()

        if self.levels < 1:
            raise TileSourceException(
                'OpenSlide image must have at least one level.')

        if self.sizeX <= 0 or self.sizeY <= 0:
            raise TileSourceException('Bioformats tile size is invalid.')

    def __del__(self):
        if getattr(self, '_bioimage', None) is not None:
            try:
                javabridge.attach()
                self._bioimage.close()
                _openImages.remove(self)
            finally:
                if javabridge.get_env():
                    javabridge.detach()

    def _getSeriesStarts(self, rdr):
        self._metadata['frameSeries'] = [{
            'series': [0],
            'sizeX': self._metadata['sizeX'],
            'sizeY': self._metadata['sizeY'],
        }]
        if self._metadata['seriesCount'] <= 1:
            return 1
        seriesMetadata = {}
        for idx in range(self._metadata['seriesCount']):
            rdr.setSeries(idx)
            seriesMetadata.update(
                javabridge.jdictionary_to_string_dictionary(rdr.getSeriesMetadata()))
        frameList = []
        nextSeriesNum = 0
        try:
            for key, value in seriesMetadata.items():
                frameNum = int(value)
                seriesNum = int(key.split('Series ')[1].split('|')[0]) - 1
                if seriesNum >= 0 and seriesNum < self._metadata['seriesCount']:
                    while len(frameList) <= frameNum:
                        frameList.append([])
                    if seriesNum not in frameList[frameNum]:
                        frameList[frameNum].append(seriesNum)
                        frameList[frameNum].sort()
                    nextSeriesNum = max(nextSeriesNum, seriesNum + 1)
        except Exception as exc:
            self.logger.debug('Failed to parse series information: %s', exc)
            rdr.setSeries(0)
            return 1
        if not len(seriesMetadata):
            frameList = [[0]]
            nextSeriesNum = 1
            for idx in range(1, self._metadata['seriesCount']):
                rdr.setSeries(idx)
                if rdr.getSizeX() == self.sizeX and rdr.getSizeY == self.sizeY:
                    frameList.append([idx])
                    if nextSeriesNum == idx:
                        nextSeriesNum = idx + 1
        frameList = [fl for fl in frameList if len(fl)]
        self._metadata['frameSeries'] = [{
            'series': fl,
        } for fl in frameList]
        rdr.setSeries(0)
        return nextSeriesNum

    def _checkSeries(self, rdr):
        firstPossibleAssoc = self._getSeriesStarts(rdr)
        self._metadata['seriesAssociatedImages'] = {}
        for seriesNum in range(firstPossibleAssoc, self._metadata['seriesCount']):
            if any((seriesNum in series['series']) for series in self._metadata['frameSeries']):
                continue
            rdr.setSeries(seriesNum)
            info = {
                'sizeX': rdr.getSizeX(),
                'sizeY': rdr.getSizeY(),
            }
            if (info['sizeX'] < self._associatedImageMaxSize and
                    info['sizeY'] < self._associatedImageMaxSize):
                # TODO: Figure out better names for associated images.  Can
                # we tell if any of them are the macro or label image?
                info['seriesNum'] = seriesNum
                self._metadata['seriesAssociatedImages'][
                    'image%d' % seriesNum] = info
        validate = None
        for frame in self._metadata['frameSeries']:
            for level in range(len(frame['series'])):
                rdr.setSeries(frame['series'][level])
                info = {
                    'sizeX': rdr.getSizeX(),
                    'sizeY': rdr.getSizeY(),
                }
                if not level:
                    frame.update(info)
                    self._metadata['sizeX'] = max(self._metadata['sizeX'], frame['sizeX'])
                    self._metadata['sizeY'] = max(self._metadata['sizeY'], frame['sizeY'])
                elif validate is not False:
                    if (not nearPowerOfTwo(frame['sizeX'], info['sizeX']) or
                            not nearPowerOfTwo(frame['sizeY'], info['sizeY'])):
                        frame['series'] = frame['series'][:level]
                        validate = True
            if validate is None:
                validate = False
        rdr.setSeries(0)
        self._metadata['sizeXY'] = len(self._metadata['frameSeries'])

    def _computeTiles(self):
        if (self._metadata['resolutionCount'] <= 1 and
                self.sizeX <= self._singleTileThreshold and
                self.sizeY <= self._singleTileThreshold):
            self.tileWidth = self.sizeX
            self.tileHeight = self.sizeY
        elif (128 <= self._metadata['optimalTileWidth'] <= self._singleTileThreshold and
              128 <= self._metadata['optimalTileHeight'] <= self._singleTileThreshold):
            self.tileWidth = self._metadata['optimalTileWidth']
            self.tileHeight = self._metadata['optimalTileHeight']
        else:
            self.tileWidth = self.tileHeight = self._tileSize

    def _computeLevels(self):
        self.levels = int(math.ceil(max(
            math.log(float(self.sizeX) / self.tileWidth),
            math.log(float(self.sizeY) / self.tileHeight)) / math.log(2))) + 1

    def _computeMagnification(self):
        self._magnification = {}
        metadata = self._metadata['metadata']
        valuekeys = {
            'x': ['Scaling|Distance|Value #1'],
            'y': ['Scaling|Distance|Value #2'],
        }
        magkeys = ['Information|Instrument|Objective|NominalMagnification #1']
        units = 1e3
        for axis in {'x', 'y'}:
            for key in valuekeys[axis]:
                if metadata.get(key):
                    self._magnification['mm_' + axis] = float(metadata[key]) * units
        for key in magkeys:
            if metadata.get(key):
                self._magnification['magnification'] = float(metadata[key])
                break

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        mm_x = self._magnification.get('mm_x')
        mm_y = self._magnification.get('mm_y', mm_x)
        # Estimate the magnification if we don't have a direct value
        mag = self._magnification.get('magnification') or 0.01 / mm_x if mm_x else None
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
        result = super().getMetadata()
        # sizeC, sizeZ, sizeT, sizeXY
        frames = []
        for xy in range(self._metadata['sizeXY']):
            for t in range(self._metadata['sizeT']):
                for z in range(self._metadata['sizeZ']):
                    for c in range(self._metadata['sizeC']):
                        frames.append({
                            'IndexC': c,
                            'IndexZ': z,
                            'IndexT': t,
                            'IndexXY': xy,
                        })
        if len(self._metadata['frameSeries']) == len(frames):
            for idx, frame in enumerate(frames):
                frame['sizeX'] = self._metadata['frameSeries'][idx]['sizeX']
                frame['sizeY'] = self._metadata['frameSeries'][idx]['sizeY']
                frame['levels'] = len(self._metadata['frameSeries'][idx]['series'])
        if len(frames) > 1:
            result['frames'] = frames
            self._addMetadataFrameInformation(result, self._metadata['channelNames'])
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        return self._metadata

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        self._xyzInRange(x, y, z)
        ft = fc = fz = 0
        fseries = self._metadata['frameSeries'][0]
        if kwargs.get('frame') is not None:
            frame = int(kwargs.get('frame'))
            fc = frame % self._metadata['sizeC']
            fz = (frame // self._metadata['sizeC']) % self._metadata['sizeZ']
            ft = (frame // self._metadata['sizeC'] //
                  self._metadata['sizeZ']) % self._metadata['sizeT']
            fxy = (frame // self._metadata['sizeC'] //
                   self._metadata['sizeZ'] // self._metadata['sizeT'])
            if frame < 0 or fxy > self._metadata['sizeXY']:
                raise TileSourceException('Frame does not exist')
            fseries = self._metadata['frameSeries'][fxy]
        seriesLevel = self.levels - 1 - z
        scale = 1
        while seriesLevel >= len(fseries['series']):
            seriesLevel -= 1
            scale *= 2
        offsetx = x * self.tileWidth * scale
        offsety = y * self.tileHeight * scale
        width = min(self.tileWidth * scale, self.sizeX // 2 ** seriesLevel - offsetx)
        height = min(self.tileHeight * scale, self.sizeY // 2 ** seriesLevel - offsety)
        sizeXAtScale = fseries['sizeX'] // (2 ** seriesLevel)
        sizeYAtScale = fseries['sizeY'] // (2 ** seriesLevel)
        finalWidth = width // scale
        finalHeight = height // scale
        width = min(width, sizeXAtScale - offsetx)
        height = min(height, sizeYAtScale - offsety)

        with self._tileLock:
            try:
                javabridge.attach()
                if width > 0 and height > 0:
                    tile = self._bioimage.read(
                        c=fc, z=fz, t=ft, series=fseries['series'][seriesLevel],
                        rescale=False,  # return internal data types
                        XYWH=(offsetx, offsety, width, height))
                else:
                    # We need the same dtype, so read 1x1 at 0x0
                    tile = self._bioimage.read(
                        c=fc, z=fz, t=ft, series=fseries['series'][seriesLevel],
                        rescale=False,  # return internal data types
                        XYWH=(0, 0, 1, 1))
                    tile = numpy.zeros(tuple([0, 0] + list(tile.shape[2:])), dtype=tile.dtype)
                format = TILE_FORMAT_NUMPY
            except javabridge.JavaException as exc:
                es = javabridge.to_string(exc.throwable)
                raise TileSourceException('Failed to get Bioformat region (%s, %r).' % (es, (
                    fc, fz, ft, fseries, self.sizeX, self.sizeY, offsetx, offsety, width, height)))
            finally:
                if javabridge.get_env():
                    javabridge.detach()
        if scale > 1:
            tile = tile[::scale, ::scale]
        if tile.shape[:2] != (finalHeight, finalWidth):
            fillValue = 0
            if tile.dtype == numpy.uint16:
                fillValue = 65535
            elif tile.dtype == numpy.uint8:
                fillValue = 255
            elif tile.dtype.kind == 'f':
                fillValue = 1
            retile = numpy.full(
                tuple([finalHeight, finalWidth] + list(tile.shape[2:])),
                fillValue,
                dtype=tile.dtype)
            retile[0:min(tile.shape[0], finalHeight), 0:min(tile.shape[1], finalWidth)] = tile[
                0:min(tile.shape[0], finalHeight), 0:min(tile.shape[1], finalWidth)]
            tile = retile
        return self._outputTile(tile, format, x, y, z, pilImageAllowed, numpyAllowed, **kwargs)

    def getAssociatedImagesList(self):
        """
        Return a list of associated images.

        :return: the list of image keys.
        """
        return sorted(self._metadata['seriesAssociatedImages'].keys())

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        info = self._metadata['seriesAssociatedImages'].get(imageKey)
        if info is None:
            return
        series = info['seriesNum']
        with self._tileLock:
            try:
                javabridge.attach()
                image = self._bioimage.read(
                    series=series,
                    rescale=False,  # return internal data types
                    XYWH=(0, 0, info['sizeX'], info['sizeY']))
            except javabridge.JavaException as exc:
                es = javabridge.to_string(exc.throwable)
                raise TileSourceException('Failed to get Bioformat series (%s, %r).' % (es, (
                    series, info['sizeX'], info['sizeY'])))
            finally:
                if javabridge.get_env():
                    javabridge.detach()
        return large_image.tilesource.base._imageToPIL(image)


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return BioformatsFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return BioformatsFileTileSource.canRead(*args, **kwargs)
