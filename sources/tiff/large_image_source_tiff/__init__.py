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

import base64
import io
import itertools
import json
import math
import os

import cachetools
import numpy
import PIL.Image
import tifftools

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_NUMPY, TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource, nearPowerOfTwo

from .tiff_reader import (InvalidOperationTiffException, IOTiffException,
                          IOTiffOpenException, TiffException,
                          TiledTiffDirectory, ValidationTiffException)

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


@cachetools.cached(cache=cachetools.LRUCache(maxsize=10))
def _cached_read_tiff(path):
    return tifftools.read_tiff(path)


class TiffFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to TIFF files.
    """

    cacheName = 'tilesource'
    name = 'tiff'
    extensions = {
        None: SourcePriority.MEDIUM,
        'tif': SourcePriority.HIGH,
        'tiff': SourcePriority.HIGH,
        'ptif': SourcePriority.PREFERRED,
        'ptiff': SourcePriority.PREFERRED,
        'qptiff': SourcePriority.PREFERRED,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
        'image/tiff': SourcePriority.HIGH,
        'image/x-tiff': SourcePriority.HIGH,
        'image/x-ptif': SourcePriority.PREFERRED,
    }

    # When getting tiles for otherwise empty directories (missing powers of
    # two), we composite the tile from higher resolution levels.  This can use
    # excessive memory if there are too many missing levels.  For instance, if
    # there are six missing levels and the tile size is 1024 square RGBA, then
    # 16 Gb are needed for the composited tile at a minimum.  By setting
    # _maxSkippedLevels, such large gaps are composited in stages.
    _maxSkippedLevels = 3

    _maxAssociatedImageSize = 8192

    def __init__(self, path, **kwargs):  # noqa
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = str(self._getLargeImagePath())

        try:
            self._initWithTiffTools()
            return
        except Exception as exc:
            config.getConfig('logger').debug('Cannot read with tifftools route; %r', exc)

        try:
            alldir = self._scanDirectories()
        except IOTiffOpenException:
            raise TileSourceError('File cannot be opened via tiff source.')
        except (ValidationTiffException, TiffException) as exc:
            alldir = []
            lastException = exc

        # If there are no tiled images, raise an exception.
        if not len(alldir):
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            msg = "File %s didn't meet requirements for tile source: %s" % (
                self._largeImagePath, lastException)
            config.getConfig('logger').debug(msg)
            raise TileSourceError(msg)
        # Sort the known directories by image area (width * height).  Given
        # equal area, sort by the level.
        alldir.sort()
        # The highest resolution image is our preferred image
        highest = alldir[-1][-1]
        directories = {}
        # Discard any images that use a different tiling scheme than our
        # preferred image
        for tdir in alldir:
            td = tdir[-1]
            level = tdir[2]
            if (td.tileWidth != highest.tileWidth or
                    td.tileHeight != highest.tileHeight):
                if not len(self._associatedImages):
                    self._addAssociatedImage(self._largeImagePath, tdir[-2], True, highest)
                continue
            # If a layer's image is not a multiple of the tile size, it should
            # be near a power of two of the highest resolution image.
            if (((td.imageWidth % td.tileWidth) and
                    not nearPowerOfTwo(td.imageWidth, highest.imageWidth)) or
                    ((td.imageHeight % td.tileHeight) and
                        not nearPowerOfTwo(td.imageHeight, highest.imageHeight))):
                continue
            # If a layer is a multiple of the tile size, the number of tiles
            # should be a power of two rounded up from the primary.
            if (not (td.imageWidth % td.tileWidth) and not (td.imageHeight % td.tileHeight)):
                htw = highest.imageWidth // td.tileWidth
                hth = highest.imageHeight // td.tileHeight
                ttw = td.imageWidth // td.tileWidth
                tth = td.imageHeight // td.tileHeight
                while (htw > ttw and htw > 1) or (hth > tth and hth > 1):
                    htw = (htw + 1) // 2
                    hth = (hth + 1) // 2
                if htw != ttw or hth != tth:
                    continue
            directories[level] = td
        if not len(directories) or (len(directories) < 2 and max(directories.keys()) + 1 > 4):
            raise TileSourceError(
                'Tiff image must have at least two levels.')

        # Sort the directories so that the highest resolution is the last one;
        # if a level is missing, put a None value in its place.
        self._tiffDirectories = [directories.get(key) for key in
                                 range(max(directories.keys()) + 1)]
        self.tileWidth = highest.tileWidth
        self.tileHeight = highest.tileHeight
        self.levels = len(self._tiffDirectories)
        self.sizeX = highest.imageWidth
        self.sizeY = highest.imageHeight
        self._checkForInefficientDirectories()

    def _scanDirectories(self):
        lastException = None
        # Associated images are smallish TIFF images that have an image
        # description and are not tiled.  They have their own TIFF directory.
        # Individual TIFF images can also have images embedded into their
        # directory as tags (this is a vendor-specific method of adding more
        # images into a file) -- those are stored in the individual
        # directories' _embeddedImages field.
        self._associatedImages = {}

        dir = None
        # Query all know directories in the tif file.  Only keep track of
        # directories that contain tiled images.
        alldir = []
        associatedDirs = []
        for directoryNum in itertools.count():  # pragma: no branch
            try:
                if dir is None:
                    dir = TiledTiffDirectory(self._largeImagePath, directoryNum, validate=False)
                else:
                    dir._setDirectory(directoryNum)
                    dir._loadMetadata()
                dir._validate()
            except ValidationTiffException as exc:
                lastException = exc
                associatedDirs.append(directoryNum)
                continue
            except TiffException as exc:
                if not lastException:
                    lastException = exc
                break
            if not dir.tileWidth or not dir.tileHeight:
                continue
            # Calculate the tile level, where 0 is a single tile, 1 is up to a
            # set of 2x2 tiles, 2 is 4x4, etc.
            level = int(math.ceil(math.log(max(
                float(dir.imageWidth) / dir.tileWidth,
                float(dir.imageHeight) / dir.tileHeight)) / math.log(2)))
            if level < 0:
                continue
            td, dir = dir, None
            # Store information for sorting with the directory.
            alldir.append((level > 0, td.tileWidth * td.tileHeight, level,
                           td.imageWidth * td.imageHeight, directoryNum, td))
        if not alldir and lastException:
            raise lastException
        for directoryNum in associatedDirs:
            self._addAssociatedImage(self._largeImagePath, directoryNum)
        return alldir

    def _levelFromIfd(self, ifd, baseifd):
        """
        Get the level based on information in an ifd and on the full-resolution
        0-frame ifd.  An exception is raised if the ifd does not seem to
        represent a possible level.

        :param ifd: an ifd record returned from tifftools.
        :param baseifd: the ifd record of the full-resolution frame 0.
        :returns: the level, where self.levels - 1 is full resolution and 0 is
            the lowest resolution.
        """
        sizeX = ifd['tags'][tifftools.Tag.ImageWidth.value]['data'][0]
        sizeY = ifd['tags'][tifftools.Tag.ImageLength.value]['data'][0]
        tileWidth = baseifd['tags'][tifftools.Tag.TileWidth.value]['data'][0]
        tileHeight = baseifd['tags'][tifftools.Tag.TileLength.value]['data'][0]
        for tag in {
                tifftools.Tag.SamplesPerPixel.value,
                tifftools.Tag.BitsPerSample.value,
                tifftools.Tag.PlanarConfig.value,
                tifftools.Tag.Photometric.value,
                tifftools.Tag.Orientation.value,
                tifftools.Tag.Compression.value,
                tifftools.Tag.TileWidth.value,
                tifftools.Tag.TileLength.value,
        }:
            if ((tag in ifd['tags'] and tag not in baseifd['tags']) or
                    (tag not in ifd['tags'] and tag in baseifd['tags']) or
                    (tag in ifd['tags'] and
                     ifd['tags'][tag]['data'] != baseifd['tags'][tag]['data'])):
                raise TileSourceError('IFD does not match first IFD.')
        sizes = [(self.sizeX, self.sizeY)]
        for level in range(self.levels - 1, -1, -1):
            if (sizeX, sizeY) in sizes:
                return level
            altsizes = []
            for w, h in sizes:
                w2f = int(math.floor(w / 2))
                h2f = int(math.floor(h / 2))
                w2c = int(math.ceil(w / 2))
                h2c = int(math.ceil(h / 2))
                w2t = int(math.floor((w / 2 + tileWidth - 1) / tileWidth)) * tileWidth
                h2t = int(math.floor((h / 2 + tileHeight - 1) / tileHeight)) * tileHeight
                for w2, h2 in [(w2f, h2f), (w2f, h2c), (w2c, h2f), (w2c, h2c), (w2t, h2t)]:
                    if (w2, h2) not in altsizes:
                        altsizes.append((w2, h2))
            sizes = altsizes
        raise TileSourceError('IFD size is not a power of two smaller than first IFD.')

    def _initWithTiffTools(self):  # noqa
        """
        Use tifftools to read all of the tiff directory information.  Check if
        the zeroth directory can be validated as a tiled directory.  If so,
        then check if the remaining directories are either tiled in descending
        size or have subifds with tiles in descending sizes.  All primary tiled
        directories are the same size and format; all non-tiled directories are
        treated as associated images.
        """
        dir0 = TiledTiffDirectory(self._largeImagePath, 0)
        self.tileWidth = dir0.tileWidth
        self.tileHeight = dir0.tileHeight
        self.sizeX = dir0.imageWidth
        self.sizeY = dir0.imageHeight
        self.levels = max(1, int(math.ceil(math.log(max(
            dir0.imageWidth / dir0.tileWidth,
            dir0.imageHeight / dir0.tileHeight)) / math.log(2))) + 1)
        info = _cached_read_tiff(self._largeImagePath)
        frames = []
        associated = []  # for now, a list of directories
        curframe = -1
        for idx, ifd in enumerate(info['ifds']):
            # if not tiles, add to associated images
            if tifftools.Tag.tileWidth.value not in ifd['tags']:
                associated.append(idx)
                continue
            level = self._levelFromIfd(ifd, info['ifds'][0])
            # if the same resolution as the main image, add a frame
            if level == self.levels - 1:
                curframe += 1
                frames.append({'dirs': [None] * self.levels})
                frames[-1]['dirs'][-1] = (idx, 0)
                try:
                    frameMetadata = json.loads(
                        ifd['tags'][tifftools.Tag.ImageDescription.value]['data'])
                    for key in {'channels', 'frame'}:
                        if key in frameMetadata:
                            frames[-1][key] = frameMetadata[key]
                except Exception:
                    pass
            # otherwise, add to the first frame missing that level
            elif level < self.levels - 1 and any(
                    frame for frame in frames if frame['dirs'][level] is None):
                frames[next(
                    idx for idx, frame in enumerate(frames) if frame['dirs'][level] is None
                )]['dirs'][level] = (idx, 0)
            else:
                raise TileSourceError('Tile layers are in a surprising order')
            # if there are sub ifds, add them
            if tifftools.Tag.SubIfd.value in ifd['tags']:
                for subidx, subifds in enumerate(ifd['tags'][tifftools.Tag.SubIfd.value]['ifds']):
                    if len(subifds) != 1:
                        raise TileSourceError(
                            'When stored in subifds, each subifd should be a single ifd.')
                    level = self._levelFromIfd(subifds[0], info['ifds'][0])
                    if level < self.levels - 1 and frames[-1]['dirs'][level] is None:
                        frames[-1]['dirs'][level] = (idx, subidx + 1)
                    else:
                        raise TileSourceError('Tile layers are in a surprising order')
        self._associatedImages = {}
        for dirNum in associated:
            self._addAssociatedImage(self._largeImagePath, dirNum)
        self._frames = frames
        self._tiffDirectories = [
            TiledTiffDirectory(
                self._largeImagePath,
                frames[0]['dirs'][idx][0],
                subDirectoryNum=frames[0]['dirs'][idx][1])
            if frames[0]['dirs'][idx] is not None else None
            for idx in range(self.levels - 1)]
        self._tiffDirectories.append(dir0)
        self._checkForInefficientDirectories()
        return True

    def _checkForInefficientDirectories(self, warn=True):
        """
        Raise a warning for inefficient files.

        :param warn: if True and inefficient, emit a warning.
        """
        missing = [v is None for v in self._tiffDirectories]
        maxMissing = max(0 if not v else missing.index(False, idx) - idx
                         for idx, v in enumerate(missing))
        self._skippedLevels = maxMissing
        if maxMissing >= self._maxSkippedLevels:
            if warn:
                config.getConfig('logger').warning(
                    'Tiff image is missing many lower resolution levels (%d).  '
                    'It will be inefficient to read lower resolution tiles.', maxMissing)
            self._inefficientWarning = True

    def _reorient_numpy_image(self, image, orientation):
        """
        Reorient a numpy image array based on a tiff orientation.

        :param image: the numpy array to reorient.
        :param orientation: one of the tiff orientation constants.
        :returns: an image with top-left orientation.
        """
        if len(image.shape) == 2:
            image = numpy.resize(image, (image.shape[0], image.shape[1], 1))
        if orientation in {
                tifftools.constants.Orientation.LeftTop.value,
                tifftools.constants.Orientation.RightTop.value,
                tifftools.constants.Orientation.LeftBottom.value,
                tifftools.constants.Orientation.RightBottom.value}:
            image = image.transpose(1, 0, 2)
        if orientation in {
                tifftools.constants.Orientation.BottomLeft.value,
                tifftools.constants.Orientation.BottomRight.value,
                tifftools.constants.Orientation.LeftBottom.value,
                tifftools.constants.Orientation.RightBottom.value}:
            image = image[::-1, ::, ::]
        if orientation in {
                tifftools.constants.Orientation.TopRight.value,
                tifftools.constants.Orientation.BottomRight.value,
                tifftools.constants.Orientation.RightTop.value,
                tifftools.constants.Orientation.RightBottom.value}:
            image = image[::, ::-1, ::]
        return image

    def _addAssociatedImage(self, largeImagePath, directoryNum, mustBeTiled=False, topImage=None):
        """
        Check if the specified TIFF directory contains an image with a sensible
        image description that can be used as an ID.  If so, and if the image
        isn't too large, add this image as an associated image.

        :param largeImagePath: path to the TIFF file.
        :param directoryNum: libtiff directory number of the image.
        :param mustBeTiles: if true, use tiled images.  If false, require
           untiled images.
        :param topImage: if specified, add image-embedded metadata to this
           image.
        """
        try:
            associated = TiledTiffDirectory(largeImagePath, directoryNum, mustBeTiled)
            id = ''
            desc = associated._tiffInfo.get('imagedescription')
            if desc:
                id = desc.strip().split(None, 1)[0].lower()
                if b'\n' in desc:
                    id = desc.split(b'\n', 1)[1].strip().split(None, 1)[0].lower() or id
            elif mustBeTiled:
                id = 'dir%d' % directoryNum
                if not len(self._associatedImages):
                    id = 'macro'
            if not isinstance(id, str):
                id = id.decode()
            # Only use this as an associated image if the parsed id is
            # a reasonable length, alphanumeric characters, and the
            # image isn't too large.
            if (id.isalnum() and len(id) > 3 and len(id) <= 20 and
                    associated._pixelInfo['width'] <= self._maxAssociatedImageSize and
                    associated._pixelInfo['height'] <= self._maxAssociatedImageSize):
                image = associated._tiffFile.read_image()
                # Optrascan scanners store xml image descriptions in a "tiled
                # image".  Check if this is the case, and, if so, parse such
                # data
                if image.tobytes()[:6] == b'<?xml ':
                    self._parseImageXml(image.tobytes().rsplit(b'>', 1)[0] + b'>', topImage)
                    return
                image = self._reorient_numpy_image(image, associated._tiffInfo.get('orientation'))
                self._associatedImages[id] = image
        except (TiffException, AttributeError):
            # If we can't validate or read an associated image or it has no
            # useful imagedescription, fail quietly without adding an
            # associated image.
            pass
        except Exception:
            # If we fail for other reasons, don't raise an exception, but log
            # what happened.
            config.getConfig('logger').exception(
                'Could not use non-tiled TIFF image as an associated image.')

    def _parseImageXml(self, xml, topImage):
        """
        Parse metadata stored in arbitrary xml and associate it with a specific
        image.

        :param xml: the xml as a string or bytes object.
        :param topImage: the image to add metadata to.
        """
        if not topImage or topImage.pixelInfo.get('magnificaiton'):
            return
        topImage.parse_image_description(xml)
        if not topImage._description_record:
            return
        try:
            xml = topImage._description_record
            # Optrascan metadata
            scanDetails = xml.get('ScanInfo', xml.get('EncodeInfo'))['ScanDetails']
            mag = float(scanDetails['Magnification'])
            # In microns; convert to mm
            scale = float(scanDetails['PixelResolution']) * 1e-3
            topImage._pixelInfo = {
                'magnification': mag,
                'mm_x': scale,
                'mm_y': scale,
            }
        except Exception:
            pass

    def getNativeMagnification(self):
        """
        Get the magnification at a particular level.

        :return: magnification, width of a pixel in mm, height of a pixel in mm.
        """
        pixelInfo = self._tiffDirectories[-1].pixelInfo
        mm_x = pixelInfo.get('mm_x')
        mm_y = pixelInfo.get('mm_y')
        # Estimate the magnification if we don't have a direct value
        mag = pixelInfo.get('magnification') or 0.01 / mm_x if mm_x else None
        return {
            'magnification': mag,
            'mm_x': mm_x,
            'mm_y': mm_y,
        }

    def _xmlToMetadata(self, xml):
        if not isinstance(xml, dict) or set(xml.keys()) != {'DataObject'}:
            return xml
        values = {}
        try:
            objlist = xml['DataObject']
            if not isinstance(objlist, list):
                objlist = [objlist]
            for obj in objlist:
                attrList = obj['Attribute']
                if not isinstance(attrList, list):
                    attrList = [attrList]
                for attr in attrList:
                    if 'Array' not in attr:
                        values[attr['Name']] = attr.get('text', '')
                    else:
                        if 'DataObject' in attr['Array']:
                            subvalues = self._xmlToMetadata(attr['Array'])
                            for key, subvalue in subvalues.items():
                                if key not in {'PIM_DP_IMAGE_DATA', }:
                                    values[attr['Name'] + '|' + key] = subvalue
        except Exception:
            return xml
        return values

    def getMetadata(self):
        """
        Return a dictionary of metadata containing levels, sizeX, sizeY,
        tileWidth, tileHeight, magnification, mm_x, mm_y, and frames.

        :returns: metadata dictionary.
        """
        result = super().getMetadata()
        if hasattr(self, '_frames') and len(self._frames) > 1:
            result['frames'] = [frame.get('frame', {}) for frame in self._frames]
            self._addMetadataFrameInformation(result, self._frames[0].get('channels', None))
        return result

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        results = {}
        for idx, dir in enumerate(self._tiffDirectories[::-1]):
            if dir:
                if hasattr(dir, '_description_record'):
                    results['xml' + (
                        '' if not results.get('xml') else '_' + str(idx))] = self._xmlToMetadata(
                            dir._description_record)
                for k, v in dir._tiffInfo.items():
                    if k == 'imagedescription' and hasattr(dir, '_description_record'):
                        continue
                    if isinstance(v, (str, bytes)) and k:
                        if isinstance(v, bytes):
                            try:
                                v = v.decode()
                            except UnicodeDecodeError:
                                continue
                        results.setdefault('tiff', {})
                        if not idx and k not in results['tiff']:
                            results['tiff'][k] = v
                        elif k not in results['tiff'] or v != results['tiff'][k]:
                            results['tiff'][k + ':%d' % idx] = v
        return results

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False,
                sparseFallback=False, **kwargs):
        frame = self._getFrame(**kwargs)
        self._xyzInRange(x, y, z, frame, len(self._frames) if hasattr(self, '_frames') else None)
        if frame > 0:
            if hasattr(self, '_frames') and self._frames[frame]['dirs'][z] is not None:
                dir = self._getDirFromCache(*self._frames[frame]['dirs'][z])
            else:
                dir = None
        else:
            dir = self._tiffDirectories[z]
        try:
            allowStyle = True
            if dir is None:
                try:
                    if not kwargs.get('inSparseFallback'):
                        tile = self.getTileFromEmptyDirectory(x, y, z, **kwargs)
                    else:
                        raise IOTiffException('Missing z level %d' % z)
                except Exception:
                    if sparseFallback:
                        raise IOTiffException('Missing z level %d' % z)
                    else:
                        raise
                allowStyle = False
                format = TILE_FORMAT_PIL
            else:
                tile = dir.getTile(x, y)
                format = 'JPEG'
            if isinstance(tile, PIL.Image.Image):
                format = TILE_FORMAT_PIL
            if isinstance(tile, numpy.ndarray):
                format = TILE_FORMAT_NUMPY
            return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                                    numpyAllowed, applyStyle=allowStyle, **kwargs)
        except InvalidOperationTiffException as e:
            raise TileSourceError(e.args[0])
        except IOTiffException as e:
            return self.getTileIOTiffError(
                x, y, z, pilImageAllowed=pilImageAllowed,
                numpyAllowed=numpyAllowed, sparseFallback=sparseFallback,
                exception=e, **kwargs)

    def _getDirFromCache(self, dirnum, subdir=None):
        if not hasattr(self, '_directoryCache'):
            self._directoryCache = {}
            self._directoryCacheMaxSize = max(20, self.levels * 3)
        key = (dirnum, subdir)
        result = self._directoryCache.get(key)
        if result is None:
            if len(self._directoryCache) >= self._directoryCacheMaxSize:
                self._directoryCache = {}
            try:
                result = TiledTiffDirectory(
                    self._largeImagePath, dirnum, mustBeTiled=None, subDirectoryNum=subdir)
            except IOTiffException:
                result = None
            self._directoryCache[key] = result
        return result

    def getTileIOTiffError(self, x, y, z, pilImageAllowed=False,
                           numpyAllowed=False, sparseFallback=False,
                           exception=None, **kwargs):
        if sparseFallback:
            if z:
                noedge = kwargs.copy()
                noedge.pop('edge', None)
                noedge['inSparseFallback'] = True
                image = self.getTile(
                    x // 2, y // 2, z - 1, pilImageAllowed=True, numpyAllowed=False,
                    sparseFallback=sparseFallback, edge=False,
                    **noedge)
                if not isinstance(image, PIL.Image.Image):
                    image = PIL.Image.open(io.BytesIO(image))
                image = image.crop((
                    self.tileWidth / 2 if x % 2 else 0,
                    self.tileHeight / 2 if y % 2 else 0,
                    self.tileWidth if x % 2 else self.tileWidth / 2,
                    self.tileHeight if y % 2 else self.tileHeight / 2))
                image = image.resize((self.tileWidth, self.tileHeight))
            else:
                image = PIL.Image.new('RGBA', (self.tileWidth, self.tileHeight))
            return self._outputTile(image, TILE_FORMAT_PIL, x, y, z, pilImageAllowed,
                                    numpyAllowed, applyStyle=False, **kwargs)
        raise TileSourceError('Internal I/O failure: %s' % exception.args[0])

    def getTileFromEmptyDirectory(self, x, y, z, **kwargs):
        """
        Given the x, y, z tile location in an unpopulated level, get tiles from
        higher resolution levels to make the lower-res tile.

        :param x: location of tile within original level.
        :param y: location of tile within original level.
        :param z: original level.
        :returns: tile in PIL format.
        """
        basez = z
        scale = 1
        dirlist = self._tiffDirectories
        frame = self._getFrame(**kwargs)
        if frame > 0 and hasattr(self, '_frames'):
            dirlist = self._frames[frame]['dirs']
        while dirlist[z] is None:
            scale *= 2
            z += 1
        while z - basez > self._maxSkippedLevels:
            z -= self._maxSkippedLevels
            scale = int(scale / 2 ** self._maxSkippedLevels)
        tile = PIL.Image.new('RGBA', (
            min(self.sizeX, self.tileWidth * scale), min(self.sizeY, self.tileHeight * scale)))
        maxX = 2.0 ** (z + 1 - self.levels) * self.sizeX / self.tileWidth
        maxY = 2.0 ** (z + 1 - self.levels) * self.sizeY / self.tileHeight
        for newX in range(scale):
            for newY in range(scale):
                if ((newX or newY) and ((x * scale + newX) >= maxX or
                                        (y * scale + newY) >= maxY)):
                    continue
                subtile = self.getTile(
                    x * scale + newX, y * scale + newY, z,
                    pilImageAllowed=True, numpyAllowed=False,
                    sparseFallback=True, edge=False, frame=frame)
                if not isinstance(subtile, PIL.Image.Image):
                    subtile = PIL.Image.open(io.BytesIO(subtile))
                tile.paste(subtile, (newX * self.tileWidth,
                                     newY * self.tileHeight))
        return tile.resize((self.tileWidth, self.tileHeight),
                           getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS)

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
            level += 1
        while level - baselevel >= self._maxSkippedLevels:
            level -= self._maxSkippedLevels
        return level

    def getAssociatedImagesList(self):
        """
        Get a list of all associated images.

        :return: the list of image keys.
        """
        imageList = set(self._associatedImages)
        for td in self._tiffDirectories:
            if td is not None:
                imageList |= set(td._embeddedImages)
        return sorted(imageList)

    def _getAssociatedImage(self, imageKey):
        """
        Get an associated image in PIL format.

        :param imageKey: the key of the associated image.
        :return: the image in PIL format or None.
        """
        # The values in _embeddedImages are sometimes duplicated with the
        # _associatedImages.  There are some sample files where libtiff's
        # read_image fails to read the _associatedImage properly because of
        # separated jpeg information.  For the samples we currently have,
        # preferring the _embeddedImages is sufficient, but if find other files
        # with seemingly bad associated images, we may need to read them with a
        # more complex process than read_image.
        for td in self._tiffDirectories:
            if td is not None and imageKey in td._embeddedImages:
                return PIL.Image.open(io.BytesIO(base64.b64decode(td._embeddedImages[imageKey])))
        if imageKey in self._associatedImages:
            return PIL.Image.fromarray(self._associatedImages[imageKey])


def open(*args, **kwargs):
    """
    Create an instance of the module class.
    """
    return TiffFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if an input can be read by the module class.
    """
    return TiffFileTileSource.canRead(*args, **kwargs)
