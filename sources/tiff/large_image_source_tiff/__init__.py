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

import base64
import itertools
import math
import numpy
import PIL.Image
import six
from pkg_resources import DistributionNotFound, get_distribution
from six import BytesIO
from six.moves import range

from large_image import config
from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import SourcePriority, TILE_FORMAT_PIL, TILE_FORMAT_NUMPY
from large_image.exceptions import TileSourceException
from large_image.tilesource import FileTileSource, nearPowerOfTwo

from .tiff_reader import TiledTiffDirectory, TiffException, \
    InvalidOperationTiffException, IOTiffException, ValidationTiffException


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


@six.add_metaclass(LruCacheMetaclass)
class TiffFileTileSource(FileTileSource):
    """
    Provides tile access to TIFF files.
    """

    cacheName = 'tilesource'
    name = 'tifffile'
    extensions = {
        None: SourcePriority.MEDIUM,
        'tif': SourcePriority.HIGH,
        'tiff': SourcePriority.HIGH,
        'ptif': SourcePriority.PREFERRED,
        'ptiff': SourcePriority.PREFERRED,
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

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super(TiffFileTileSource, self).__init__(path, **kwargs)

        largeImagePath = self._getLargeImagePath()
        self._largeImagePath = largeImagePath
        try:
            alldir = self._scanDirectories()
        except (ValidationTiffException, TiffException) as exc:
            alldir = []
            lastException = exc

        # If there are no tiled images, raise an exception.
        if not len(alldir):
            msg = "File %s didn't meet requirements for tile source: %s" % (
                largeImagePath, lastException)
            config.getConfig('logger').debug(msg)
            raise TileSourceException(msg)
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
                    self._addAssociatedImage(largeImagePath, tdir[-2], True, highest)
                continue
            # If a layer's image is not a multiple of the tile size, it should
            # be near a power of two of the highest resolution image.
            if (((td.imageWidth % td.tileWidth) and
                    not nearPowerOfTwo(td.imageWidth, highest.imageWidth)) or
                    ((td.imageHeight % td.tileHeight) and
                        not nearPowerOfTwo(td.imageHeight, highest.imageHeight))):
                continue
            directories[level] = td
        if not len(directories) or (len(directories) < 2 and max(directories.keys()) + 1 > 4):
            raise TileSourceException(
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

    def _scanDirectories(self):
        largeImagePath = self._largeImagePath
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
                    dir = TiledTiffDirectory(largeImagePath, directoryNum, validate=False)
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
            self._addAssociatedImage(largeImagePath, directoryNum)
        return alldir

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
            if associated._tiffInfo.get('imagedescription'):
                id = associated._tiffInfo.get(
                    'imagedescription').strip().split(None, 1)[0].lower()
            elif mustBeTiled:
                id = 'dir%d' % directoryNum
                if not len(self._associatedImages):
                    id = 'macro'
            if not isinstance(id, six.text_type):
                id = id.decode('utf8')
            # Only use this as an associated image if the parsed id is
            # a reasonable length, alphanumeric characters, and the
            # image isn't too large.
            if (id.isalnum() and len(id) > 3 and len(id) <= 20 and
                    associated._pixelInfo['width'] <= 8192 and
                    associated._pixelInfo['height'] <= 8192):
                image = associated._tiffFile.read_image()
                # Optrascan scanners store xml image descriptions in a "tiled
                # image".  Check if this is the case, and, if so, parse such
                # data
                if image.tobytes()[:6] == b'<?xml ':
                    self._parseImageXml(image.tobytes().rsplit(b'>', 1)[0] + b'>', topImage)
                    return
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

        :params xml: the xml as a string or bytes object.
        :params topImage: the image to add metadata to.
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
                            for key, subvalue in six.iteritems(subvalues):
                                if key not in {'PIM_DP_IMAGE_DATA', }:
                                    values[attr['Name'] + '|' + key] = subvalue
        except Exception:
            config.getConfig('logger').exception('Here')
            return xml
        return values

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
                for k, v in six.iteritems(dir._tiffInfo):
                    if k == 'imagedescription' and hasattr(dir, '_description_record'):
                        continue
                    if isinstance(v, (str, bytes)) and k:
                        if isinstance(v, bytes):
                            try:
                                v = v.decode('utf8')
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
        self._xyzInRange(x, y, z)
        try:
            allowStyle = True
            if self._tiffDirectories[z] is None:
                try:
                    tile = self.getTileFromEmptyDirectory(x, y, z, **kwargs)
                except Exception:
                    if sparseFallback:
                        raise IOTiffException('Missing z level %d' % z)
                    else:
                        raise
                allowStyle = False
                format = TILE_FORMAT_PIL
            else:
                tile = self._tiffDirectories[z].getTile(x, y)
                format = 'JPEG'
            if isinstance(tile, PIL.Image.Image):
                format = TILE_FORMAT_PIL
            if isinstance(tile, numpy.ndarray):
                format = TILE_FORMAT_NUMPY
            return self._outputTile(tile, format, x, y, z, pilImageAllowed,
                                    numpyAllowed, applyStyle=allowStyle, **kwargs)
        except IndexError:
            raise TileSourceException('z layer does not exist')
        except InvalidOperationTiffException as e:
            raise TileSourceException(e.args[0])
        except IOTiffException as e:
            return self.getTileIOTiffException(
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

    def getTileIOTiffException(self, x, y, z, pilImageAllowed=False,
                               numpyAllowed=False, sparseFallback=False,
                               exception=None, **kwargs):
        if sparseFallback and z:
            noedge = kwargs.copy()
            noedge.pop('edge', None)
            image = self.getTile(
                x / 2, y / 2, z - 1, pilImageAllowed=True, numpyAllowed=False,
                sparseFallback=sparseFallback, edge=False, **noedge)
            if not isinstance(image, PIL.Image.Image):
                image = PIL.Image.open(BytesIO(image))
            image = image.crop((
                self.tileWidth / 2 if x % 2 else 0,
                self.tileHeight / 2 if y % 2 else 0,
                self.tileWidth if x % 2 else self.tileWidth / 2,
                self.tileHeight if y % 2 else self.tileHeight / 2))
            image = image.resize((self.tileWidth, self.tileHeight))
            return self._outputTile(image, TILE_FORMAT_PIL, x, y, z, pilImageAllowed,
                                    numpyAllowed, applyStyle=False, **kwargs)
        raise TileSourceException('Internal I/O failure: %s' % exception.args[0])

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
        while self._tiffDirectories[z] is None:
            scale *= 2
            z += 1
        while z - basez > self._maxSkippedLevels:
            z -= self._maxSkippedLevels
            scale = int(scale / 2 ** self._maxSkippedLevels)
        tile = PIL.Image.new(
            'RGBA', (self.tileWidth * scale, self.tileHeight * scale))
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
                    sparseFallback=True, edge=False, frame=kwargs.get('frame'))
                if not isinstance(subtile, PIL.Image.Image):
                    subtile = PIL.Image.open(BytesIO(subtile))
                tile.paste(subtile, (newX * self.tileWidth,
                                     newY * self.tileHeight))
        return tile.resize((self.tileWidth, self.tileHeight),
                           PIL.Image.LANCZOS)

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
        while level - baselevel > self._maxSkippedLevels:
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
                image = PIL.Image.open(BytesIO(base64.b64decode(td._embeddedImages[imageKey])))
                return image
        if imageKey in self._associatedImages:
            return PIL.Image.fromarray(self._associatedImages[imageKey])
        return None
