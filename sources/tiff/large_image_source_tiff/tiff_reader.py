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
import io
import json
import math
import os
import threading
from functools import partial
from xml.etree import ElementTree

import cachetools
import numpy
import PIL.Image

from large_image import config
from large_image.cache_util import methodcache, strhash
from large_image.tilesource import etreeToDict

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
    config.getConfig('logger').warning(
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


class TiledTiffDirectory:

    CoreFunctions = [
        'SetDirectory', 'SetSubDirectory', 'GetField',
        'LastDirectory', 'GetMode', 'IsTiled', 'IsByteSwapped', 'IsUpSampled',
        'IsMSB2LSB', 'NumberOfStrips',
    ]

    def __init__(self, filePath, directoryNum, mustBeTiled=True, subDirectoryNum=0, validate=True):
        """
        Create a new reader for a tiled image file directory in a TIFF file.

        :param filePath: A path to a TIFF file on disk.
        :type filePath: str
        :param directoryNum: The number of the TIFF image file directory to
            open.
        :type directoryNum: int
        :param mustBeTiled: if True, only tiled images validate.  If False,
            only non-tiled images validate.  None validates both.
        :type mustBeTiled: bool
        :param subDirectoryNum: if set, the number of the TIFF subdirectory.
        :type subDirectoryNum: int
        :param validate: if False, don't validate that images can be read.
        :type mustBeTiled: bool
        :raises: InvalidOperationTiffException or IOTiffException or
            ValidationTiffException
        """
        self.logger = config.getConfig('logger')
        # create local cache to store Jpeg tables and getTileByteCountsType
        self.cache = cachetools.LRUCache(10)
        self._mustBeTiled = mustBeTiled

        self._tiffFile = None
        self._tileLock = threading.RLock()

        self._open(filePath, directoryNum, subDirectoryNum)
        self._loadMetadata()
        self.logger.debug(
            'TiffDirectory %d:%d Information %r',
            directoryNum, subDirectoryNum or 0, self._tiffInfo)
        try:
            if validate:
                self._validate()
        except ValidationTiffException:
            self._close()
            raise

    def __del__(self):
        self._close()

    def _open(self, filePath, directoryNum, subDirectoryNum=0):
        """
        Open a TIFF file to a given file and IFD number.

        :param filePath: A path to a TIFF file on disk.
        :type filePath: str
        :param directoryNum: The number of the TIFF IFD to be used.
        :type directoryNum: int
        :param subDirectoryNum: The number of the TIFF sub-IFD to be used.
        :type subDirectoryNum: int
        :raises: InvalidOperationTiffException or IOTiffException
        """
        self._close()
        if not os.path.isfile(filePath):
            raise InvalidOperationTiffException(
                'TIFF file does not exist: %s' % filePath)
        try:
            bytePath = filePath
            if not isinstance(bytePath, bytes):
                bytePath = filePath.encode()
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
        self._setDirectory(directoryNum, subDirectoryNum)

    def _setDirectory(self, directoryNum, subDirectoryNum=0):
        self._directoryNum = directoryNum
        if self._tiffFile.SetDirectory(self._directoryNum) != 1:
            self._tiffFile.close()
            raise IOTiffException(
                'Could not set TIFF directory to %d' % directoryNum)
        self._subDirectoryNum = subDirectoryNum
        if self._subDirectoryNum:
            subifds = self._tiffFile.GetField('subifd')
            if (subifds is None or self._subDirectoryNum < 1 or
                    self._subDirectoryNum > len(subifds)):
                raise IOTiffException(
                    'Could not set TIFF subdirectory to %d' % subDirectoryNum)
            subifd = subifds[self._subDirectoryNum - 1]
            if self._tiffFile.SetSubDirectory(subifd) != 1:
                self._tiffFile.close()
                raise IOTiffException(
                    'Could not set TIFF subdirectory to %d' % subDirectoryNum)

    def _close(self):
        if self._tiffFile:
            self._tiffFile.close()
            self._tiffFile = None

    def _validate(self):  # noqa
        """
        Validate that this TIFF file and directory are suitable for reading.

        :raises: ValidationTiffException
        """
        if not self._mustBeTiled:
            if self._mustBeTiled is not None and self._tiffInfo.get('istiled'):
                raise ValidationTiffException('Expected a non-tiled TIFF file')
        # For any non-supported file, we probably can add a conversion task in
        # the create_image.py script, such as flatten or colourspace.  These
        # should only be done if necessary, which would require the conversion
        # job to check output and perform subsequent processing as needed.
        if (not self._tiffInfo.get('samplesperpixel') or
                (self._tiffInfo.get('samplesperpixel') != 1 and
                 self._tiffInfo.get('samplesperpixel') < 3)):
            raise ValidationTiffException(
                'Only RGB and greyscale TIFF files are supported')

        if self._tiffInfo.get('bitspersample') not in (8, 16, 32, 64):
            raise ValidationTiffException(
                'Only 8 and 16 bits-per-sample TIFF files are supported')

        if self._tiffInfo.get('sampleformat') not in {
                None,  # default is still SAMPLEFORMAT_UINT
                libtiff_ctypes.SAMPLEFORMAT_UINT,
                libtiff_ctypes.SAMPLEFORMAT_INT,
                libtiff_ctypes.SAMPLEFORMAT_IEEEFP}:
            raise ValidationTiffException(
                'Only unsigned int sampled TIFF files are supported')

        if (self._tiffInfo.get('planarconfig') != libtiff_ctypes.PLANARCONFIG_CONTIG and
                self._tiffInfo.get('photometric') not in {
                    libtiff_ctypes.PHOTOMETRIC_MINISBLACK}):
            raise ValidationTiffException(
                'Only contiguous planar configuration TIFF files are supported')

        if self._tiffInfo.get('photometric') not in {
                libtiff_ctypes.PHOTOMETRIC_MINISBLACK,
                libtiff_ctypes.PHOTOMETRIC_RGB,
                libtiff_ctypes.PHOTOMETRIC_YCBCR}:
            raise ValidationTiffException(
                'Only greyscale (black is 0), RGB, and YCbCr photometric '
                'interpretation TIFF files are supported')

        if self._tiffInfo.get('orientation') not in {
                libtiff_ctypes.ORIENTATION_TOPLEFT,
                libtiff_ctypes.ORIENTATION_TOPRIGHT,
                libtiff_ctypes.ORIENTATION_BOTRIGHT,
                libtiff_ctypes.ORIENTATION_BOTLEFT,
                libtiff_ctypes.ORIENTATION_LEFTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT,
                None}:
            raise ValidationTiffException(
                'Unsupported TIFF orientation')

        if self._mustBeTiled and (
                not self._tiffInfo.get('istiled') or
                not self._tiffInfo.get('tilewidth') or
                not self._tiffInfo.get('tilelength')):
            raise ValidationTiffException('A tiled TIFF is required.')

        if self._mustBeTiled is False and (
                self._tiffInfo.get('istiled') or
                not self._tiffInfo.get('rowsperstrip')):
            raise ValidationTiffException('A non-tiled TIFF with strips is required.')

        if (self._tiffInfo.get('compression') == libtiff_ctypes.COMPRESSION_JPEG and
                self._tiffInfo.get('jpegtablesmode') !=
                libtiff_ctypes.JPEGTABLESMODE_QUANT |
                libtiff_ctypes.JPEGTABLESMODE_HUFF):
            raise ValidationTiffException(
                'Only TIFF files with separate Huffman and quantization '
                'tables are supported')

        if self._tiffInfo.get('compression') == libtiff_ctypes.COMPRESSION_JPEG:
            try:
                self._getJpegTables()
            except IOTiffException:
                self._completeJpeg = True

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
                self.logger.debug(
                    'Loading field "%s" in directory number %d resulted in TypeError - "%s"',
                    field, self._directoryNum, err)

        for func in self.CoreFunctions[3:]:
            if hasattr(self._tiffFile, func):
                value = getattr(self._tiffFile, func)()
                if value:
                    info[func.lower()] = value
        self._tiffInfo = info
        self._tileWidth = info.get('tilewidth') or info.get('imagewidth')
        self._tileHeight = info.get('tilelength') or info.get('rowsperstrip')
        self._imageWidth = info.get('imagewidth')
        self._imageHeight = info.get('imagelength')
        if not info.get('tilelength'):
            self._stripsPerTile = int(max(1, math.ceil(256.0 / self._tileHeight)))
            self._stripHeight = self._tileHeight
            self._tileHeight = self._stripHeight * self._stripsPerTile
            self._stripCount = int(math.ceil(float(self._imageHeight) / self._stripHeight))
        if info.get('orientation') in {
                libtiff_ctypes.ORIENTATION_LEFTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            self._imageWidth, self._imageHeight = self._imageHeight, self._imageWidth
            self._tileWidth, self._tileHeight = self._tileHeight, self._tileWidth
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
        if not self._pixelInfo.get('width') and self._imageWidth:
            self._pixelInfo['width'] = self._imageWidth
        if not self._pixelInfo.get('height') and self._imageHeight:
            self._pixelInfo['height'] = self._imageHeight

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
            raise IOTiffException('Could not get JPEG Huffman / quantization tables')

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

    def _toTileNum(self, x, y, transpose=False):
        """
        Get the internal tile number of a tile, from its row and column index.

        :param x: The column index of the desired tile.
        :type x: int
        :param y: The row index of the desired tile.
        :type y: int
        :param transpose: If true, transpose width and height
        :type tranpose: boolean
        :return: The internal tile number of the desired tile.
        :rtype int
        :raises: InvalidOperationTiffException
        """
        # TIFFCheckTile and TIFFComputeTile require pixel coordinates
        if not transpose:
            pixelX = int(x * self._tileWidth)
            pixelY = int(y * self._tileHeight)
            if x < 0 or y < 0 or pixelX >= self._imageWidth or pixelY >= self._imageHeight:
                raise InvalidOperationTiffException(
                    'Tile x=%d, y=%d does not exist' % (x, y))
        else:
            pixelX = int(x * self._tileHeight)
            pixelY = int(y * self._tileWidth)
            if x < 0 or y < 0 or pixelX >= self._imageHeight or pixelY >= self._imageWidth:
                raise InvalidOperationTiffException(
                    'Tile x=%d, y=%d does not exist' % (x, y))
        # We had been using TIFFCheckTile, but with z=0 and sample=0, this is
        # just a check that x, y is within the image
        # if libtiff_ctypes.libtiff.TIFFCheckTile(
        #         self._tiffFile, pixelX, pixelY, 0, 0) == 0:
        #     raise InvalidOperationTiffException(
        #         'Tile x=%d, y=%d does not exist' % (x, y))
        if self._tiffInfo.get('istiled'):
            tileNum = libtiff_ctypes.libtiff.TIFFComputeTile(
                self._tiffFile, pixelX, pixelY, 0, 0).value
        else:
            # TIFFComputeStrip with sample=0 is just the row divided by the
            # strip height
            tileNum = int(pixelY // self._stripHeight)
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

    def _getJpegFrame(self, tileNum, entire=False):  # noqa
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
        if rawTileSize <= 0:
            raise IOTiffException('No raw tile data')

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
        # If the photometric value is RGB and the JPEG component ids are just
        # 0, 1, 2, change the component ids to R, G, B to ensure color space
        # information is preserved.
        if self._tiffInfo.get('photometric') == libtiff_ctypes.PHOTOMETRIC_RGB:
            sof = frameBuffer.raw.find(b'\xff\xc0')
            if sof == -1:
                sof = frameBuffer.raw.find(b'\xff\xc2')
            sos = frameBuffer.raw.find(b'\xff\xda')
            if (sof >= frameStartPos and sos >= frameStartPos and
                    frameBuffer[sof + 2:sof + 4] == b'\x00\x11' and
                    frameBuffer[sof + 10:sof + 19:3] == b'\x00\x01\x02' and
                    frameBuffer[sos + 5:sos + 11:2] == b'\x00\x01\x02'):
                for idx, val in enumerate(b'RGB'):
                    frameBuffer[sof + 10 + idx * 3] = val
                    frameBuffer[sos + 5 + idx * 2] = val
        # Strip the Start / End Of Image markers
        tileData = frameBuffer.raw[frameStartPos:-2]
        return tileData

    def _getUncompressedTile(self, tileNum):
        """
        Get an uncompressed tile or strip.

        :param tileNum: The internal tile or strip number of the desired tile
            or strip.
        :type tileNum: int
        :return: the tile as a PIL 8-bit-per-channel images.
        :rtype: PIL.Image
        :raises: IOTiffException
        """
        with self._tileLock:
            if self._tiffInfo.get('istiled'):
                tileSize = libtiff_ctypes.libtiff.TIFFTileSize(self._tiffFile).value
            else:
                stripSize = libtiff_ctypes.libtiff.TIFFStripSize(
                    self._tiffFile).value
                stripsCount = min(self._stripsPerTile, self._stripCount - tileNum)
                tileSize = stripSize * self._stripsPerTile
        imageBuffer = ctypes.create_string_buffer(tileSize)
        with self._tileLock:
            if self._tiffInfo.get('istiled'):
                readSize = libtiff_ctypes.libtiff.TIFFReadEncodedTile(
                    self._tiffFile, tileNum, imageBuffer, tileSize)
            else:
                readSize = 0
                for stripNum in range(stripsCount):
                    chunkSize = libtiff_ctypes.libtiff.TIFFReadEncodedStrip(
                        self._tiffFile,
                        tileNum + stripNum,
                        ctypes.byref(imageBuffer, stripSize * stripNum),
                        stripSize).value
                    if chunkSize <= 0:
                        raise IOTiffException(
                            'Read an unexpected number of bytes from an encoded strip')
                    readSize += chunkSize
                if readSize < tileSize:
                    ctypes.memset(ctypes.byref(imageBuffer, readSize), 0, tileSize - readSize)
                    readSize = tileSize
        if readSize < tileSize:
            raise IOTiffException(
                'Read an unexpected number of bytes from an encoded tile' if readSize >= 0 else
                'Failed to read from an encoded tile')
        tw, th = self._tileWidth, self._tileHeight
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_LEFTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            tw, th = th, tw
        format = (
            self._tiffInfo.get('bitspersample'),
            self._tiffInfo.get('sampleformat') if self._tiffInfo.get(
                'sampleformat') is not None else libtiff_ctypes.SAMPLEFORMAT_UINT)
        formattbl = {
            (8, libtiff_ctypes.SAMPLEFORMAT_UINT): numpy.uint8,
            (8, libtiff_ctypes.SAMPLEFORMAT_INT): numpy.int8,
            (16, libtiff_ctypes.SAMPLEFORMAT_UINT): numpy.uint16,
            (16, libtiff_ctypes.SAMPLEFORMAT_INT): numpy.int16,
            (16, libtiff_ctypes.SAMPLEFORMAT_IEEEFP): numpy.float16,
            (32, libtiff_ctypes.SAMPLEFORMAT_UINT): numpy.uint32,
            (32, libtiff_ctypes.SAMPLEFORMAT_INT): numpy.int32,
            (32, libtiff_ctypes.SAMPLEFORMAT_IEEEFP): numpy.float32,
            (64, libtiff_ctypes.SAMPLEFORMAT_UINT): numpy.uint64,
            (64, libtiff_ctypes.SAMPLEFORMAT_INT): numpy.int64,
            (64, libtiff_ctypes.SAMPLEFORMAT_IEEEFP): numpy.float64,
        }
        image = numpy.ctypeslib.as_array(ctypes.cast(
            imageBuffer, ctypes.POINTER(ctypes.c_uint8)), (tileSize, )).view(
                formattbl[format]).reshape(
                    (th, tw, self._tiffInfo.get('samplesperpixel')))
        if (self._tiffInfo.get('samplesperpixel') == 3 and
                self._tiffInfo.get('photometric') == libtiff_ctypes.PHOTOMETRIC_YCBCR):
            if self._tiffInfo.get('bitspersample') == 16:
                image = numpy.floor_divide(image, 256).astype(numpy.uint8)
            image = PIL.Image.fromarray(image, 'YCbCr')
            image = numpy.array(image.convert('RGB'))
        return image

    def _getTileRotated(self, x, y):
        """
        Get a tile from a rotated TIF.  This composites uncompressed tiles as
        necessary and then rotates the result.

        :param x: The column index of the desired tile.
        :param y: The row index of the desired tile.
        :return: either a buffer with a JPEG or a PIL image.
        """
        x0 = x * self._tileWidth
        x1 = x0 + self._tileWidth
        y0 = y * self._tileHeight
        y1 = y0 + self._tileHeight
        iw, ih = self._imageWidth, self._imageHeight
        tw, th = self._tileWidth, self._tileHeight
        transpose = False
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_LEFTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            x0, x1, y0, y1 = y0, y1, x0, x1
            iw, ih = ih, iw
            tw, th = th, tw
            transpose = True
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_TOPRIGHT,
                libtiff_ctypes.ORIENTATION_BOTRIGHT,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT}:
            x0, x1 = iw - x1, iw - x0
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_BOTRIGHT,
                libtiff_ctypes.ORIENTATION_BOTLEFT,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            y0, y1 = ih - y1, ih - y0
        tx0 = x0 // tw
        tx1 = (x1 - 1) // tw
        ty0 = y0 // th
        ty1 = (y1 - 1) // th
        tile = None
        for ty in range(max(0, ty0), max(0, ty1 + 1)):
            for tx in range(max(0, tx0), max(0, tx1 + 1)):
                subtile = self._getUncompressedTile(self._toTileNum(tx, ty, transpose))
                if tile is None:
                    tile = numpy.zeros(
                        (th, tw) if len(subtile.shape) == 2 else
                        (th, tw, subtile.shape[2]), dtype=subtile.dtype)
                stx, sty = tx * tw - x0, ty * th - y0
                if (stx >= tw or stx + subtile.shape[1] <= 0 or
                        sty >= th or sty + subtile.shape[0] <= 0):
                    continue
                if stx < 0:
                    subtile = subtile[:, -stx:]
                    stx = 0
                if sty < 0:
                    subtile = subtile[-sty:, :]
                    sty = 0
                subtile = subtile[:min(subtile.shape[0], th - sty),
                                  :min(subtile.shape[1], tw - stx)]
                tile[sty:sty + subtile.shape[0], stx:stx + subtile.shape[1]] = subtile
        if tile is None:
            raise InvalidOperationTiffException(
                'Tile x=%d, y=%d does not exist' % (x, y))
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_BOTRIGHT,
                libtiff_ctypes.ORIENTATION_BOTLEFT,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            tile = tile[::-1, :]
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_TOPRIGHT,
                libtiff_ctypes.ORIENTATION_BOTRIGHT,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT}:
            tile = tile[:, ::-1]
        if self._tiffInfo.get('orientation') in {
                libtiff_ctypes.ORIENTATION_LEFTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTTOP,
                libtiff_ctypes.ORIENTATION_RIGHTBOT,
                libtiff_ctypes.ORIENTATION_LEFTBOT}:
            tile = tile.transpose((1, 0) if len(tile.shape) == 2 else (1, 0, 2))
        return tile

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
        if self._tiffInfo.get('orientation') not in {
                libtiff_ctypes.ORIENTATION_TOPLEFT,
                None}:
            return self._getTileRotated(x, y)
        # This raises an InvalidOperationTiffException if the tile doesn't exist
        tileNum = self._toTileNum(x, y)

        if (not self._tiffInfo.get('istiled') or
                self._tiffInfo.get('compression') not in (
                    libtiff_ctypes.COMPRESSION_JPEG, 33003, 33005, 34712) or
                self._tiffInfo.get('bitspersample') != 8 or
                self._tiffInfo.get('sampleformat') not in {
                    None, libtiff_ctypes.SAMPLEFORMAT_UINT}):
            return self._getUncompressedTile(tileNum)

        imageBuffer = io.BytesIO()

        if (self._tiffInfo.get('compression') == libtiff_ctypes.COMPRESSION_JPEG and
                not getattr(self, '_completeJpeg', False)):
            # Write JPEG Start Of Image marker
            imageBuffer.write(b'\xff\xd8')
            imageBuffer.write(self._getJpegTables())
            imageBuffer.write(self._getJpegFrame(tileNum))
            # Write JPEG End Of Image marker
            imageBuffer.write(b'\xff\xd9')
            return imageBuffer.getvalue()
        # Get the whole frame, which is in a JPEG or JPEG 2000 format, and
        # convert it to a PIL image
        imageBuffer.write(self._getJpegFrame(tileNum, True))
        image = PIL.Image.open(imageBuffer)
        # Converting the image mode ensures that it gets loaded once and is in
        # a form we expect.  If this isn't done, then PIL can load the image
        # multiple times, which sometimes throws an exception in PIL's JPEG
        # 2000 module.
        image = image.convert('RGB')
        return image

    def parse_image_description(self, meta=None):  # noqa
        self._pixelInfo = {}
        self._embeddedImages = {}

        if not meta:
            return
        if not isinstance(meta, str):
            meta = meta.decode(errors='ignore')
        try:
            parsed = json.loads(meta)
            if isinstance(parsed, dict):
                self._description_record = parsed
                return True
        except Exception:
            pass
        try:
            xml = ElementTree.fromstring(meta)
        except Exception:
            if 'AppMag = ' in meta:
                try:
                    self._pixelInfo = {
                        'magnification': float(meta.split('AppMag = ')[1].split('|')[0].strip())
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
        try:
            self._description_record = etreeToDict(xml)
        except Exception:
            pass
        return True
