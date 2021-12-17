import io
import math
import types
import xml.etree.ElementTree
from collections import defaultdict
from operator import attrgetter

import numpy
import palettable
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


def _gdalParameters(defaultCompression=None, eightbit=None, **kwargs):
    """
    Return an array of gdal translation parameters.

    :param defaultCompression: if not specified, use this value.
    :param eightbit: True or False to indicate that the bit depth per sample is
        known.  None for unknown.

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
    }
    if eightbit is not None:
        options['predictor'] = 'yes' if eightbit else 'none'
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
    if 'predictor' in options:
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


def _arrayToPalette(palette):
    """
    Given an array of color strings, tuples, or lists, return a numpy array.

    :param palette: an array of color strings, tuples, or lists.
    :returns: a numpy array of RGBA value on the scale of [0-255].
    """
    arr = []
    for clr in palette:
        if isinstance(clr, (tuple, list)):
            arr.append(numpy.array((list(clr) + [1, 1, 1])[:4]) * 255)
        else:
            try:
                arr.append(PIL.ImageColor.getcolor(str(clr), 'RGBA'))
            except ValueError:
                try:
                    import matplotlib

                    arr.append(PIL.ImageColor.getcolor(matplotlib.colors.to_hex(clr), 'RGBA'))
                except (ImportError, ValueError):
                    raise ValueError('cannot be used as a color palette: %r.' % palette)
    return numpy.array(arr)


def getPaletteColors(value):
    """
    Given a list or a name, return a list of colors in the form of a numpy
    array of RGBA.  If a list, each entry is a color name resolvable by either
    PIL.ImageColor.getcolor, by matplotlib.colors, or a 3 or 4 element list or
    tuple of RGB(A) values on a scale of 0-1.  If this is NOT a list, then, if
    it can be parsed as a color, it is treated as ['#000', <value>].  If that
    cannot be parsed, then it is assumed to be a named palette in palettable
    (such as viridis.Viridis_12) or a named palette in matplotlib (including
    plugins).

    :param value: Either a list, a single color name, or a palette name.  See
        above.
    :returns: a numpy array of RGBA value on the scale of [0-255].
    """
    palette = None
    if isinstance(value, (tuple, list)):
        palette = value
    if palette is None:
        try:
            color = PIL.ImageColor.getcolor(str(value), 'RGBA')
            palette = ['#000', color]
        except ValueError:
            pass
    if palette is None:
        try:
            palette = attrgetter(str(value))(palettable).hex_colors
        except AttributeError:
            pass
    if palette is None:
        try:
            import matplotlib

            palette = (
                ['#0000', matplotlib.colors.to_hex(value)]
                if value in matplotlib.colors.get_named_colors_mapping()
                else matplotlib.cm.get_cmap(value).colors)
        except (ImportError, ValueError, AttributeError):
            pass
    if palette is None:
        raise ValueError('cannot be used as a color palette.: %r.' % value)
    return _arrayToPalette(palette)


def isValidPalette(value):
    """
    Check if a value can be used as a palette.

    :param value: Either a list, a single color name, or a palette name.  See
        getPaletteColors.
    :returns: a boolean; true if the value can be used as a palette.
    """
    try:
        getPaletteColors(value)
        return True
    except ValueError:
        return False


def _recursePalettablePalettes(module, palettes, root=None, depth=0):
    """
    Walk the modules in palettable to find all of the available palettes.

    :param module: the current module.
    :param palettes: a set to add palette names to.
    :param root: a string of the parent modules.  None for palettable itself.
    :param depth: the depth of the walk.  Used to avoid needless recursion.
    """
    for key in dir(module):
        if not key.startswith('_'):
            attr = getattr(module, key)
            if isinstance(attr, types.ModuleType) and depth < 3:
                _recursePalettablePalettes(
                    attr, palettes, root + '.' + key if root else key, depth + 1)
            elif root and isinstance(getattr(attr, 'hex_colors', None), list):
                palettes.add(root + '.' + key)


def getAvailableNamedPalettes(includeColors=True, reduced=False):
    """
    Get a list of all named palettes that can be used with getPaletteColors.

    :param includeColors: if True, include named colors.  If False, only
        include actual palettes.
    :param reduced: if True, exclude reversed palettes and palettes with
        fewer colors where a palette with the same basic name exists with more
        colors.
    :returns: a list of names.
    """
    palettes = set()
    if includeColors:
        palettes |= set(PIL.ImageColor.colormap.keys())
    _recursePalettablePalettes(palettable, palettes)
    try:
        import matplotlib

        if includeColors:
            palettes |= set(matplotlib.colors.get_named_colors_mapping())
        # matplotlib has made the colormap list more public in recent versions
        mplcm = (matplotlib.colormaps if hasattr(matplotlib, 'colormaps')
                 else matplotlib.cm._cmap_registry)
        for key in mplcm:
            if isValidPalette(key):
                palettes.add(key)
    except ImportError:
        pass
    if reduced:
        palettes = {
            key for key in palettes
            if not key.endswith('_r') and (
                '_' not in key or
                not key.rsplit('_', 1)[-1].isdigit() or
                (key.rsplit('_', 1)[0] + '_' + str(int(
                    key.rsplit('_', 1)[-1]) + 1)) not in palettes)}
    return sorted(palettes)
