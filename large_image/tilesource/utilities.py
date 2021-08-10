import io
import math
import xml.etree.ElementTree
from collections import defaultdict

import numpy
import PIL
import PIL.Image
import PIL.ImageColor
import PIL.ImageDraw

from ..constants import (TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL,
                         TileOutputMimeTypes, TileOutputPILFormat)

# Turn off decompression warning check
PIL.Image.MAX_IMAGE_PIXELS = None


def _encodeImage(image, encoding='JPEG', jpegQuality=95, jpegSubsampling=0,
                 format=(TILE_FORMAT_IMAGE, ), tiffCompression='raw',
                 **kwargs):
    """
    Convert a PIL or numpy image into raw output bytes and a mime type.

    :param image: a PIL image.
    :param encoding: a valid PIL encoding (typically 'PNG' or 'JPEG').  Must
        also be in the TileOutputMimeTypes map.
    :param jpegQuality: the quality to use when encoding a JPEG.
    :param jpegSubsampling: the subsampling level to use when encoding a JPEG.
    :param format: the desired format or a tuple of allowed formats.  Formats
        are members of (TILE_FORMAT_PIL, TILE_FORMAT_NUMPY, TILE_FORMAT_IMAGE).
    :param tiffCompression: the compression format to use when encoding a TIFF.
    :returns:
        :imageData: the image data in the specified format and encoding.
        :imageFormatOrMimeType: the image mime type if the format is
            TILE_FORMAT_IMAGE, or the format of the image data if it is
            anything else.
    """
    if not isinstance(format, (tuple, set, list)):
        format = (format, )
    imageData = image
    imageFormatOrMimeType = TILE_FORMAT_PIL
    if TILE_FORMAT_NUMPY in format:
        imageData, _ = _imageToNumpy(image)
        imageFormatOrMimeType = TILE_FORMAT_NUMPY
    elif TILE_FORMAT_PIL in format:
        imageData = _imageToPIL(image)
        imageFormatOrMimeType = TILE_FORMAT_PIL
    elif TILE_FORMAT_IMAGE in format:
        if encoding not in TileOutputMimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        imageFormatOrMimeType = TileOutputMimeTypes[encoding]
        image = _imageToPIL(image)
        if image.width == 0 or image.height == 0:
            imageData = b''
        else:
            encoding = TileOutputPILFormat.get(encoding, encoding)
            output = io.BytesIO()
            params = {}
            if encoding == 'JPEG' and image.mode not in ('L', 'RGB'):
                image = image.convert('RGB' if image.mode != 'LA' else 'L')
            if encoding == 'JPEG':
                params['quality'] = jpegQuality
                params['subsampling'] = jpegSubsampling
            elif encoding in {'TIFF', 'TILED'}:
                params['compression'] = {
                    'none': 'raw',
                    'lzw': 'tiff_lzw',
                    'deflate': 'tiff_adobe_deflate',
                }.get(tiffCompression, tiffCompression)
            elif encoding == 'PNG':
                params['compress_level'] = 2
            image.save(output, encoding, **params)
            imageData = output.getvalue()
    return imageData, imageFormatOrMimeType


def _imageToPIL(image, setMode=None):
    """
    Convert an image in PIL, numpy, or image file format to a PIL image.

    :param image: input image.
    :param setMode: if specified, the output image is converted to this mode.
    :returns: a PIL image.
    """
    if isinstance(image, numpy.ndarray):
        mode = 'L'
        if len(image.shape) == 3:
            # Fallback for hyperspectral data to just use the first three bands
            if image.shape[2] > 4:
                image = image[:, :, :3]
            mode = ['L', 'LA', 'RGB', 'RGBA'][image.shape[2] - 1]
        if len(image.shape) == 3 and image.shape[2] == 1:
            image = numpy.resize(image, image.shape[:2])
        if image.dtype == numpy.uint16:
            image = numpy.floor_divide(image, 256).astype(numpy.uint8)
        # TODO: The scaling of float data needs to be identical across all
        # tiles of an image.  This means that we need a reference to the parent
        # tile source or some other way of regulating it.
        # elif image.dtype.kind == 'f':
        #     if numpy.max(image) > 1:
        #         maxl2 = math.ceil(math.log(numpy.max(image) + 1) / math.log(2))
        #         image = image / ((2 ** maxl2) - 1)
        #     image = (image * 255).astype(numpy.uint8)
        elif image.dtype != numpy.uint8:
            image = image.astype(numpy.uint8)
        image = PIL.Image.fromarray(image, mode)
    elif not isinstance(image, PIL.Image.Image):
        image = PIL.Image.open(io.BytesIO(image))
    if setMode is not None and image.mode != setMode:
        image = image.convert(setMode)
    return image


def _imageToNumpy(image):
    """
    Convert an image in PIL, numpy, or image file format to a numpy array.  The
    output numpy array always has three dimensions.

    :param image: input image.
    :returns: a numpy array and a target PIL image mode.
    """
    if not isinstance(image, numpy.ndarray):
        if not isinstance(image, PIL.Image.Image):
            image = PIL.Image.open(io.BytesIO(image))
        if image.mode not in ('L', 'LA', 'RGB', 'RGBA'):
            image = image.convert('RGBA')
        mode = image.mode
        image = numpy.asarray(image)
    else:
        if len(image.shape) == 3:
            mode = ['L', 'LA', 'RGB', 'RGBA'][(image.shape[2] - 1) if image.shape[2] <= 4 else 3]
        else:
            mode = 'L'
    if len(image.shape) == 2:
        image = numpy.resize(image, (image.shape[0], image.shape[1], 1))
    return image, mode


def _letterboxImage(image, width, height, fill):
    """
    Given a PIL image, width, height, and fill color, letterbox or pillarbox
    the image to make it the specified dimensions.  The image is never
    cropped.  The original image will be returned if no action is needed.

    :param image: the source image.
    :param width: the desired width in pixels.
    :param height: the desired height in pixels.
    :param fill: a fill color.
    """
    if ((image.width >= width and image.height >= height) or
            not fill or str(fill).lower() == 'none'):
        return image
    corner = False
    if fill.lower().startswith('corner:'):
        corner, fill = True, fill.split(':', 1)[1]
    color = PIL.ImageColor.getcolor(fill, image.mode)
    width = max(width, image.width)
    height = max(height, image.height)
    result = PIL.Image.new(image.mode, (width, height), color)
    result.paste(image, (
        int((width - image.width) / 2) if not corner else 0,
        int((height - image.height) / 2) if not corner else 0))
    return result


def _vipsCast(image, mustBe8Bit=False, originalScale=None):
    """
    Cast a vips image to a format we want.

    :param image: a vips image
    :param mustBe9Bit: if True, then always cast to unsigned 8-bit.
    :param originalScale:
    :returns: a vips image
    """
    import pyvips

    formats = {
        pyvips.BandFormat.CHAR: (pyvips.BandFormat.UCHAR, 2**7, 1),
        pyvips.BandFormat.COMPLEX: (pyvips.BandFormat.USHORT, 0, 65535),
        pyvips.BandFormat.DOUBLE: (pyvips.BandFormat.USHORT, 0, 65535),
        pyvips.BandFormat.DPCOMPLEX: (pyvips.BandFormat.USHORT, 0, 65535),
        pyvips.BandFormat.FLOAT: (pyvips.BandFormat.USHORT, 0, 65535),
        pyvips.BandFormat.INT: (pyvips.BandFormat.USHORT, 2**31, 2**-16),
        pyvips.BandFormat.USHORT: (pyvips.BandFormat.UCHAR, 0, 2**-8),
        pyvips.BandFormat.SHORT: (pyvips.BandFormat.USHORT, 2**15, 1),
        pyvips.BandFormat.UINT: (pyvips.BandFormat.USHORT, 0, 2**-16),
    }
    if image.format not in formats or (image.format == pyvips.BandFormat.USHORT and not mustBe8Bit):
        return image
    target, offset, multiplier = formats[image.format]
    if image.format == pyvips.BandFormat.DOUBLE:
        maxVal = image.max()
        # These thresholds are higher than 256 and 65536 because bicubic and
        # other interpolations can cause value spikes
        if maxVal >= 2 and maxVal < 2**9:
            multiplier = 256
        elif maxVal >= 256 and maxVal < 2**17:
            multiplier = 1
    if mustBe8Bit and target != pyvips.BandFormat.UCHAR:
        target = pyvips.BandFormat.UCHAR
        multiplier /= 256
    # logger.debug('Casting image from %r to %r', image.format, target)
    image = ((image.cast(pyvips.BandFormat.DOUBLE) + offset) * multiplier).cast(target)
    return image


def _gdalParameters(defaultCompression=None, **kwargs):
    """
    Return an array of gdal translation parameters.

    :param defaultCompression: if not specified, use this value.

    Optional parameters that can be specified in kwargs:

    :param tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'none'.
    :param quality: a jpeg quality passed to gdal.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    :returns: a dictionary of parameters.
    """
    options = {
        'tileSize': 256,
        'compression': 'lzw',
        'quality': 90,
        'predictor': 'yes',
    }
    predictor = {
        'none': 'NO',
        'horizontal': 'STANDARD',
        'float': 'FLOATING_POINT',
        'yes': 'YES',
    }
    options.update({k: v for k, v in kwargs.items() if v not in (None, '')})
    cmdopt = ['-of', 'COG', '-co', 'BIGTIFF=IF_SAFER']
    cmdopt += ['-co', 'BLOCKSIZE=%d' % options['tileSize']]
    cmdopt += ['-co', 'COMPRESS=%s' % options['compression'].upper()]
    cmdopt += ['-co', 'QUALITY=%s' % options['quality']]
    cmdopt += ['-co', 'PREDICTOR=%s' % predictor[options['predictor']]]
    if 'level' in options:
        cmdopt += ['-co', 'LEVEL=%s' % options['level']]
    return cmdopt


def _vipsParameters(forTiled=True, defaultCompression=None, **kwargs):
    """
    Return a dictionary of vips conversion parameters.

    :param forTiled: True if this is for a tiled image.  False for an
        associated image.
    :param defaultCompression: if not specified, use this value.

    Optional parameters that can be specified in kwargs:

    :param tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'none'.
    :param quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    :returns: a dictionary of parameters.
    """
    if not forTiled:
        convertParams = {
            'compression': defaultCompression or 'jpeg',
            'Q': 90,
            'predictor': 'horizontal',
            'tile': False,
        }
        if 'mime' in kwargs and kwargs.get('mime') != 'image/jpeg':
            convertParams['compression'] = 'lzw'
        return convertParams
    convertParams = {
        'tile': True,
        'tile_width': 256,
        'tile_height': 256,
        'pyramid': True,
        'bigtiff': True,
        'compression': defaultCompression or 'jpeg',
        'Q': 90,
        'predictor': 'horizontal',
    }
    for vkey, kwkeys in {
        'tile_width': {'tileSize'},
        'tile_height': {'tileSize'},
        'compression': {'compression', 'tiffCompression'},
        'Q': {'quality', 'jpegQuality'},
        'level': {'level'},
        'predictor': {'predictor'},
    }.items():
        for kwkey in kwkeys:
            if kwkey in kwargs and kwargs[kwkey] not in {None, ''}:
                convertParams[vkey] = kwargs[kwkey]
    if convertParams['compression'] == 'jp2k':
        convertParams['compression'] = 'none'
    if convertParams['compression'] == 'webp' and kwargs.get('quality') == 0:
        convertParams['lossless'] = True
        convertParams.pop('Q', None)
    if convertParams['predictor'] == 'yes':
        convertParams['predictor'] = 'horizontal'
    if convertParams['compression'] == 'jpeg':
        convertParams['rgbjpeg'] = True
    return convertParams


def etreeToDict(t):
    """
    Convert an xml etree to a nested dictionary without schema names in the
    keys.  If you have an xml string, this can be converted to a dictionary via
    xml.etree.etreeToDict(ElementTree.fromstring(xml_string)).

    :param t: an etree.
    :returns: a python dictionary with the results.
    """
    # Remove schema
    tag = t.tag.split('}', 1)[1] if t.tag.startswith('{') else t.tag
    d = {tag: {}}
    children = list(t)
    if children:
        entries = defaultdict(list)
        for entry in map(etreeToDict, children):
            for k, v in entry.items():
                entries[k].append(v)
        d = {tag: {k: v[0] if len(v) == 1 else v
                   for k, v in entries.items()}}

    if t.attrib:
        d[tag].update({(k.split('}', 1)[1] if k.startswith('{') else k): v
                       for k, v in t.attrib.items()})
    text = (t.text or '').strip()
    if text and len(d[tag]):
        d[tag]['text'] = text
    elif text:
        d[tag] = text
    return d


def dictToEtree(d, root=None):
    """
    Convert a dictionary in the style produced by etreeToDict back to an etree.
    Make an xml string via xml.etree.ElementTree.tostring(dictToEtree(
    dictionary), encoding='utf8', method='xml').  Note that this function and
    etreeToDict are not perfect conversions; numerical values are quoted in
    xml.  Plain key-value pairs are ambiguous whether they should be attributes
    or text values.  Text fields are collected together.

    :param d: a dictionary.
    :prarm root: the root node to attach this dictionary to.
    :returns: an etree.
    """
    if root is None:
        if len(d) == 1:
            k, v = next(iter(d.items()))
            root = xml.etree.ElementTree.Element(k)
            dictToEtree(v, root)
            return root
        root = xml.etree.ElementTree.Element('root')
    for k, v in d.items():
        if isinstance(v, list):
            for l in v:
                elem = xml.etree.ElementTree.SubElement(root, k)
                dictToEtree(l, elem)
        elif isinstance(v, dict):
            elem = xml.etree.ElementTree.SubElement(root, k)
            dictToEtree(v, elem)
        else:
            if k == 'text':
                root.text = v
            else:
                root.set(k, v)
    return root


def nearPowerOfTwo(val1, val2, tolerance=0.02):
    """
    Check if two values are different by nearly a power of two.

    :param val1: the first value to check.
    :param val2: the second value to check.
    :param tolerance: the maximum difference in the log2 ratio's mantissa.
    :return: True if the valeus are nearly a power of two different from each
        other; false otherwise.
    """
    # If one or more of the values is zero or they have different signs, then
    # return False
    if val1 * val2 <= 0:
        return False
    log2ratio = math.log(float(val1) / float(val2)) / math.log(2)
    # Compare the mantissa of the ratio's log2 value.
    return abs(log2ratio - round(log2ratio)) < tolerance
