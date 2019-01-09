# -*- coding: utf-8 -*-

###############################################################################
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
###############################################################################

import ctypes
import PIL.Image
import os
import six

from functools import partial
from xml.etree import cElementTree

from large_image.cache_util import LRUCache, strhash, methodcache
from large_image import config

try:
    from libtiff import libtiff_ctypes
except ValueError as exc:
    # If the python libtiff module doesn't contain a pregenerated module for
    # the appropriate version of libtiff, it tries to generate a module from
    # the libtiff header file.  If it can't find this file (possibly because it
    # is in a virtual environment), it raises a ValueError instead of an
    # ImportError.  We convert this to an ImportError, so that we will print a
    # more lucid error message and just fail to load this one tile source
    # instead of failing to load the whole plugin.
    config.getConfig('logger').warn(
        'Failed to import libtiff; try upgrading the python module (%s)' % exc)
    raise ImportError(str(exc))

# This suppress warnings about unknown tags
libtiff_ctypes.suppress_warnings()


def patchLibtiff():
    libtiff_ctypes.libtiff.TIFFFieldWithTag.restype = \
        ctypes.POINTER(libtiff_ctypes.TIFFFieldInfo)
    libtiff_ctypes.libtiff.TIFFFieldWithTag.argtypes = \
        (libtiff_ctypes.TIFF, libtiff_ctypes.c_ttag_t)

    # BigTIFF 64-bit unsigned integer
    libtiff_ctypes.TIFFDataType.TIFF_LONG8 = 16
    # BigTIFF 64-bit signed integer
    libtiff_ctypes.TIFFDataType.TIFF_SLONG8 = 17
    # BigTIFF 64-bit unsigned integer (offset)
    libtiff_ctypes.TIFFDataType.TIFF_IFD8 = 18


patchLibtiff()


class TiffException(Exception):
    pass


class InvalidOperationTiffException(TiffException):
    """
    An exception caused by the user making an invalid request of a TIFF file.
    """
    pass


class IOTiffException(TiffException):
    """
    An exception caused by an internal failure, due to an invalid file or other
    error.
    """
    pass


class ValidationTiffException(TiffException):
    """
    An exception caused by the TIFF reader not being able to support a given
    file.
    """
    pass


class TiledTiffDirectory(object):

    CoreFunctions = [
        'SetDirectory', 'GetField', 'LastDirectory', 'GetMode', 'IsTiled',
        'IsByteSwapped', 'IsUpSampled', 'IsMSB2LSB', 'NumberOfStrips'
    ]

    def __init__(self, filePath, directoryNum, mustBeTiled=True):
        """
        Create a new reader for a tiled image file directory in a TIFF file.

        :param filePath: A path to a TIFF file on disk.
        :type filePath: str
        :param directoryNum: The number of the TIFF image file directory to
        open.
        :type directoryNum: int
        :param mustBeTiled: if True, only tiled images validate.  If False,
            only non-tiled images validate.  None validates both.
        :raises: InvalidOperationTiffException or IOTiffException or
        ValidationTiffException
        """
        # TODO how many to keep in the cache
        # create local cache to store Jpeg tables and
        # getTileByteCountsType

        self.cache = LRUCache(10)
        self._mustBeTiled = mustBeTiled

        self._tiffFile = None

        self._open(filePath, directoryNum)
        self._loadMetadata()
        config.getConfig('logger').debug(
            'TiffDirectory %d Information %r', directoryNum, self._tiffInfo)
        try:
            self._validate()
        except ValidationTiffException:
            self._close()
            raise

    def __del__(self):
        self._close()

    def _open(self, filePath, directoryNum):
        """
        Open a TIFF file to a given file and IFD number.

        :param filePath: A path to a TIFF file on disk.
        :type filePath: str
        :param directoryNum: The number of the TIFF IFD to be used.
        :type directoryNum: int
        :raises: InvalidOperationTiffException or IOTiffException
        """
        self._close()
        if not os.path.isfile(filePath):
            raise InvalidOperationTiffException(
                'TIFF file does not exist: %s' % filePath)
        try:
            bytePath = filePath
            if not isinstance(bytePath, six.binary_type):
                bytePath = filePath.encode('utf8')
            self._tiffFile = libtiff_ctypes.TIFF.open(bytePath)
        except TypeError:
            raise IOTiffException(
                'Could not open TIFF file: %s' % filePath)
        # pylibtiff changed the case of some functions between version 0.4 and
        # the version that supports libtiff 4.0.6.  To support both, ensure
        # that the cased functions exist.
        for func in self.CoreFunctions:
            if (not hasattr(self._tiffFile, func) and
                    hasattr(self._tiffFile, func.lower())):
                setattr(self._tiffFile, func, getattr(
                    self._tiffFile, func.lower()))

        self._directoryNum = directoryNum
        if self._tiffFile.SetDirectory(self._directoryNum) != 1:
            self._tiffFile.close()
            raise IOTiffException(
                'Could not set TIFF directory to %d' % directoryNum)

    def _close(self):
        if self._tiffFile:
            self._tiffFile.close()
            self._tiffFile = None

    def _validate(self):
        """
        Validate that this TIFF file and directory are suitable for reading.

        :raises: ValidationTiffException
        """
        if not self._mustBeTiled:
            if self._mustBeTiled is not None and self._tiffInfo.get('istiled'):
                raise ValidationTiffException('Expected a non-tiled TIFF file')
            return
        # For any non-supported file, we probably can add a conversion task in
        # the create_image.py script, such as flatten or colourspace.  These
        # should only be done if necessary, which would require the conversion
        # job to check output and perform subsequent processing as needed.
        if (not self._tiffInfo.get('samplesperpixel') or
                (self._tiffInfo.get('samplesperpixel') != 1 and
                 self._tiffInfo.get('samplesperpixel') < 3)):
            raise ValidationTiffException(
                'Only RGB and greyscale TIFF files are supported')

        if self._tiffInfo.get('bitspersample') != 8:
            raise ValidationTiffException(
                'Only single-byte sampled TIFF files are supported')

        if self._tiffInfo.get('sampleformat') not in (
                None,  # default is still SAMPLEFORMAT_UINT
                libtiff_ctypes.SAMPLEFORMAT_UINT):
            raise ValidationTiffException(
                'Only unsigned int sampled TIFF files are supported')

        if self._tiffInfo.get('planarconfig') != libtiff_ctypes.PLANARCONFIG_CONTIG:
            raise ValidationTiffException(
                'Only contiguous planar configuration TIFF files are supported')

        if self._tiffInfo.get('photometric') not in (
                libtiff_ctypes.PHOTOMETRIC_MINISBLACK,
                libtiff_ctypes.PHOTOMETRIC_RGB,
                libtiff_ctypes.PHOTOMETRIC_YCBCR):
            raise ValidationTiffException(
                'Only greyscale (black is 0), RGB, and YCbCr photometric '
                'interpretation TIFF files are supported')

        if self._tiffInfo.get('orientation') != libtiff_ctypes.ORIENTATION_TOPLEFT:
            raise ValidationTiffException(
                'Only top-left orientation TIFF files are supported')

        if self._tiffInfo.get('compression') not in (
                libtiff_ctypes.COMPRESSION_JPEG, 33003, 33005):
            raise ValidationTiffException(
                'Only JPEG compression TIFF files are supported')
        if (not self._tiffInfo.get('istiled') or
                not self._tiffInfo.get('tilewidth') or
                not self._tiffInfo.get('tilelength')):
            raise ValidationTiffException('Only tiled TIFF files are supported')

        if (self._tiffInfo.get('compression') == libtiff_ctypes.COMPRESSION_JPEG and
                self._tiffInfo.get('jpegtablesmode') !=
                libtiff_ctypes.JPEGTABLESMODE_QUANT |
                libtiff_ctypes.JPEGTABLESMODE_HUFF):
            raise ValidationTiffException(
                'Only TIFF files with separate Huffman and quantization '
                'tables are supported')

    def _loadMetadata(self):
        fields = [key.split('_', 1)[1].lower() for key in
                  dir(libtiff_ctypes.tiff_h) if key.startswith('TIFFTAG_')]
        info = {}
        for field in fields:
            try:
                value = self._tiffFile.GetField(field)
                if value is not None:
                    info[field] = value
            except TypeError as err:
                config.getConfig('logger').debug(
                    'Loading field "%s" in directory number %d resulted in TypeError - "%s"',
                    field, self._directoryNum, err)

        for func in self.CoreFunctions[2:]:
            if hasattr(self._tiffFile, func):
                value = getattr(self._tiffFile, func)()
                if value:
                    info[func.lower()] = value
        self._tiffInfo = info
        self._tileWidth = info.get('tilewidth')
        self._tileHeight = info.get('tilelength')
        self._imageWidth = info.get('imagewidth')
        self._imageHeight = info.get('imagelength')
        self.parse_image_description(info.get('imagedescription', ''))
        # From TIFF specification, tag 0x128, 2 is inches, 3 is centimeters.
        units = {2: 25.4, 3: 10}
        # If the resolution value is less than a threshold (100), don't use it,
        # as it is probably just an inaccurate default.  Values like 72dpi and
        # 96dpi are common defaults, but so are small metric values, too.
        if (not self._pixelInfo.get('mm_x') and info.get('xresolution') and
                units.get(info.get('resolutionunit')) and
                info.get('xresolution') >= 100):
            self._pixelInfo['mm_x'] = units[info['resolutionunit']] / info['xresolution']
        if (not self._pixelInfo.get('mm_y') and info.get('yresolution') and
                units.get(info.get('resolutionunit')) and
                info.get('yresolution') >= 100):
            self._pixelInfo['mm_y'] = units[info['resolutionunit']] / info['yresolution']
        if not self._pixelInfo.get('width') and info.get('imagewidth'):
            self._pixelInfo['width'] = info['imagewidth']
        if not self._pixelInfo.get('height') and info.get('imagelength'):
            self._pixelInfo['height'] = info['imagelength']

    @methodcache(key=partial(strhash, '_getJpegTables'))
    def _getJpegTables(self):
        """
        Get the common JPEG Huffman-coding and quantization tables.

        See http://www.awaresystems.be/imaging/tiff/tifftags/jpegtables.html
        for more information.

        :return: All Huffman and quantization tables, with JPEG table start
        markers.
        :rtype: bytes
        :raises: Exception
        """
        # TIFFTAG_JPEGTABLES uses (uint32*, void**) output arguments
        # http://www.remotesensing.org/libtiff/man/TIFFGetField.3tiff.html

        tableSize = ctypes.c_uint32()
        tableBuffer = ctypes.c_voidp()

        # Some versions of pylibtiff set an explicit list of argtypes for
        # TIFFGetField.  When this is done, we need to adjust them to match
        # what is needed for our specific call.  Other versions do not set
        # argtypes, allowing any types to be passed without validation, in
        # which case we do not need to alter the list.
        if libtiff_ctypes.libtiff.TIFFGetField.argtypes:
            libtiff_ctypes.libtiff.TIFFGetField.argtypes = \
                libtiff_ctypes.libtiff.TIFFGetField.argtypes[:2] + \
                [ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_void_p)]
        if libtiff_ctypes.libtiff.TIFFGetField(
                self._tiffFile,
                libtiff_ctypes.TIFFTAG_JPEGTABLES,
                ctypes.byref(tableSize),
                ctypes.byref(tableBuffer)) != 1:
            raise IOTiffException(
                'Could not get JPEG Huffman / quantization tables')

        tableSize = tableSize.value
        tableBuffer = ctypes.cast(tableBuffer, ctypes.POINTER(ctypes.c_char))

        if tableBuffer[:2] != b'\xff\xd8':
            raise IOTiffException(
                'Missing JPEG Start Of Image marker in tables')
        if tableBuffer[tableSize - 2:tableSize] != b'\xff\xd9':
            raise IOTiffException('Missing JPEG End Of Image marker in tables')
        if tableBuffer[2:4] not in (b'\xff\xc4', b'\xff\xdb'):
            raise IOTiffException(
                'Missing JPEG Huffman or Quantization Table marker')

        # Strip the Start / End Of Image markers
        tableData = tableBuffer[2:tableSize - 2]
        return tableData

    def _toTileNum(self, x, y):
        """
        Get the internal tile number of a tile, from its row and column index.

        :param x: The column index of the desired tile.
        :type x: int
        :param y: The row index of the desired tile.
        :type y: int
        :return: The internal tile number of the desired tile.
        :rtype int
        :raises: InvalidOperationTiffException
        """
        # TIFFCheckTile and TIFFComputeTile require pixel coordinates
        pixelX = int(x * self._tileWidth)
        pixelY = int(y * self._tileHeight)

        if pixelX >= self._imageWidth or pixelY >= self._imageHeight:
            raise InvalidOperationTiffException(
                'Tile x=%d, y=%d does not exist' % (x, y))
        if libtiff_ctypes.libtiff.TIFFCheckTile(
                self._tiffFile, pixelX, pixelY, 0, 0) == 0:
            raise InvalidOperationTiffException(
                'Tile x=%d, y=%d does not exist' % (x, y))

        tileNum = libtiff_ctypes.libtiff.TIFFComputeTile(
            self._tiffFile, pixelX, pixelY, 0, 0).value
        return tileNum

    @methodcache(key=partial(strhash, '_getTileByteCountsType'))
    def _getTileByteCountsType(self):
        """
        Get data type of the elements in the TIFFTAG_TILEBYTECOUNTS array.

        :return: The element type in TIFFTAG_TILEBYTECOUNTS.
        :rtype: ctypes.c_uint64 or ctypes.c_uint16
        :raises: IOTiffException
        """
        tileByteCountsFieldInfo = libtiff_ctypes.libtiff.TIFFFieldWithTag(
            self._tiffFile, libtiff_ctypes.TIFFTAG_TILEBYTECOUNTS).contents
        tileByteCountsLibtiffType = tileByteCountsFieldInfo.field_type

        if tileByteCountsLibtiffType == libtiff_ctypes.TIFFDataType.TIFF_LONG8:
            return ctypes.c_uint64
        elif tileByteCountsLibtiffType == \
                libtiff_ctypes.TIFFDataType.TIFF_SHORT:
            return ctypes.c_uint16
        else:
            raise IOTiffException(
                'Invalid type for TIFFTAG_TILEBYTECOUNTS: %s' % tileByteCountsLibtiffType)

    def _getJpegFrameSize(self, tileNum):
        """
        Get the file size in bytes of the raw encoded JPEG frame for a tile.

        :param tileNum: The internal tile number of the desired tile.
        :type tileNum: int
        :return: The size in bytes of the raw tile data for the desired tile.
        :rtype: int
        :raises: InvalidOperationTiffException or IOTiffException
        """
        # TODO: is it worth it to memoize this?

        # TODO: remove this check, for additional speed
        totalTileCount = libtiff_ctypes.libtiff.TIFFNumberOfTiles(
            self._tiffFile).value
        if tileNum >= totalTileCount:
            raise InvalidOperationTiffException('Tile number out of range')

        # pylibtiff treats the output of TIFFTAG_TILEBYTECOUNTS as a scalar
        # uint32; libtiff's documentation specifies that the output will be an
        # array of uint32; in reality and per the TIFF spec, the output is an
        # array of either uint64 or unit16, so we need to call the ctypes
        # interface directly to get this tag
        # http://www.awaresystems.be/imaging/tiff/tifftags/tilebytecounts.html

        rawTileSizesType = self._getTileByteCountsType()
        rawTileSizes = ctypes.POINTER(rawTileSizesType)()

        # Some versions of pylibtiff set an explicit list of argtypes for
        # TIFFGetField.  When this is done, we need to adjust them to match
        # what is needed for our specific call.  Other versions do not set
        # argtypes, allowing any types to be passed without validation, in
        # which case we do not need to alter the list.
        if libtiff_ctypes.libtiff.TIFFGetField.argtypes:
            libtiff_ctypes.libtiff.TIFFGetField.argtypes = \
                libtiff_ctypes.libtiff.TIFFGetField.argtypes[:2] + \
                [ctypes.POINTER(ctypes.POINTER(rawTileSizesType))]
        if libtiff_ctypes.libtiff.TIFFGetField(
                self._tiffFile,
                libtiff_ctypes.TIFFTAG_TILEBYTECOUNTS,
                ctypes.byref(rawTileSizes)) != 1:
            raise IOTiffException('Could not get raw tile size')

        # In practice, this will never overflow, and it's simpler to convert the
        # long to an int
        return int(rawTileSizes[tileNum])

    def _getJpegFrame(self, tileNum, entire=False):
        """
        Get the raw encoded JPEG image frame from a tile.

        :param tileNum: The internal tile number of the desired tile.
        :type tileNum: int
        :param entire: True to return the entire frame.  False to strip off
            container information.
        :return: The JPEG image frame, including a JPEG Start Of Frame marker.
        :rtype: bytes
        :raises: InvalidOperationTiffException or IOTiffException
        """
        # This raises an InvalidOperationTiffException if the tile doesn't exist
        rawTileSize = self._getJpegFrameSize(tileNum)

        frameBuffer = ctypes.create_string_buffer(rawTileSize)

        bytesRead = libtiff_ctypes.libtiff.TIFFReadRawTile(
            self._tiffFile, tileNum,
            frameBuffer, rawTileSize).value
        if bytesRead == -1:
            raise IOTiffException('Failed to read raw tile')
        elif bytesRead < rawTileSize:
            raise IOTiffException('Buffer underflow when reading tile')
        elif bytesRead > rawTileSize:
            # It's unlikely that this will ever occur, but incomplete reads will
            # be checked for by looking for the JPEG end marker
            raise IOTiffException('Buffer overflow when reading tile')
        if entire:
            return frameBuffer.raw[:]

        if frameBuffer.raw[:2] != b'\xff\xd8':
            raise IOTiffException('Missing JPEG Start Of Image marker in frame')
        if frameBuffer.raw[-2:] != b'\xff\xd9':
            raise IOTiffException('Missing JPEG End Of Image marker in frame')
        if frameBuffer.raw[2:4] in (b'\xff\xc0', b'\xff\xc2'):
            frameStartPos = 2
        else:
            # VIPS may encode TIFFs with the quantization (but not Huffman)
            # tables also at the start of every frame, so locate them for
            # removal
            # VIPS seems to prefer Baseline DCT, so search for that first
            frameStartPos = frameBuffer.raw.find(b'\xff\xc0', 2, -2)
            if frameStartPos == -1:
                frameStartPos = frameBuffer.raw.find(b'\xff\xc2', 2, -2)
                if frameStartPos == -1:
                    raise IOTiffException('Missing JPEG Start Of Frame marker')

        # Strip the Start / End Of Image markers
        tileData = frameBuffer.raw[frameStartPos:-2]
        return tileData

    @property
    def tileWidth(self):
        """
        Get the pixel width of tiles.

        :return: The tile width in pixels.
        :rtype: int
        """
        return self._tileWidth

    @property
    def tileHeight(self):
        """
        Get the pixel height of tiles.

        :return: The tile height in pixels.
        :rtype: int
        """
        return self._tileHeight

    @property
    def imageWidth(self):
        return self._imageWidth

    @property
    def imageHeight(self):
        return self._imageHeight

    @property
    def pixelInfo(self):
        return self._pixelInfo

    def getTile(self, x, y):
        """
        Get the complete JPEG image from a tile.

        :param x: The column index of the desired tile.
        :type x: int
        :param y: The row index of the desired tile.
        :type y: int
        :return: either a buffer with a JPEG or a PIL image.
        :rtype: bytes
        :raises: InvalidOperationTiffException or IOTiffException
        """
        # This raises an InvalidOperationTiffException if the tile doesn't exist
        tileNum = self._toTileNum(x, y)

        imageBuffer = six.BytesIO()

        if self._tiffInfo.get('compression') == libtiff_ctypes.COMPRESSION_JPEG:
            # Write JPEG Start Of Image marker
            imageBuffer.write(b'\xff\xd8')
            imageBuffer.write(self._getJpegTables())
            imageBuffer.write(self._getJpegFrame(tileNum))
            # Write JPEG End Of Image marker
            imageBuffer.write(b'\xff\xd9')
            return imageBuffer.getvalue()

        if self._tiffInfo.get('compression') in (33003, 33005):
            # Get the whole frame, which is JPEG 2000 format, and convert it to
            # a PIL image
            imageBuffer.write(self._getJpegFrame(tileNum, True))
            image = PIL.Image.open(imageBuffer)
            # Converting the image mode ensures that it gets loaded once and is
            # in a form we expect.  IF this isn't done, then PIL can load the
            # image multiple times, which sometimes throws an exception in
            # PIL's JPEG 2000 module.
            image = image.convert('RGB')
            return image

    def parse_image_description(self, meta=None):

        self._pixelInfo = {}
        self._embeddedImages = {}

        if not meta:
            return
        if not isinstance(meta, six.string_types):
            meta = meta.decode('utf8', 'ignore')
        try:
            xml = cElementTree.fromstring(meta)
        except Exception:
            if 'AppMag = ' in meta:
                try:
                    self._pixelInfo = {
                        'magnification': float(meta.split('AppMag = ')[1])
                    }
                except Exception:
                    pass
            return
        try:
            image = xml.find(
                ".//DataObject[@ObjectType='DPScannedImage']")
            columns = int(image.find(".//*[@Name='PIM_DP_IMAGE_COLUMNS']").text)
            rows = int(image.find(".//*[@Name='PIM_DP_IMAGE_ROWS']").text)
            spacing = [float(val.strip('"')) for val in image.find(
                ".//*[@Name='DICOM_PIXEL_SPACING']").text.split()]
            self._pixelInfo = {
                'width': columns,
                'height': rows,
                'mm_x': spacing[0],
                'mm_y': spacing[1]
            }
        except Exception:
            pass
        # Extract macro and label images
        for image in xml.findall(".//*[@ObjectType='DPScannedImage']"):
            try:
                typestr = image.find(".//*[@Name='PIM_DP_IMAGE_TYPE']").text
                datastr = image.find(".//*[@Name='PIM_DP_IMAGE_DATA']").text
            except Exception:
                continue
            if not typestr or not datastr:
                continue
            typemap = {
                'LABELIMAGE': 'label',
                'MACROIMAGE': 'macro',
                'WSI': 'thumbnail',
            }
            self._embeddedImages[typemap.get(typestr, typestr.lower())] = datastr
        return True
