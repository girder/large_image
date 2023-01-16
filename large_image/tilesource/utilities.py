import io
import math
import types
import xml.etree.ElementTree
from collections import defaultdict
from operator import attrgetter

import numpy
import PIL
import PIL.Image
import PIL.ImageColor
import PIL.ImageDraw

try:
    import simplejpeg
except ImportError:
    simplejpeg = None

from ..constants import (TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL,
                         TileOutputMimeTypes, TileOutputPILFormat)

# Turn off decompression warning check
PIL.Image.MAX_IMAGE_PIXELS = None

# Extend colors so G and GREEN map to expected values.  CSS green is #0080ff,
# which is unfortunate.
colormap = {
    'R': '#ff0000',
    'G': '#00ff00',
    'B': '#0000ff',
    'RED': '#ff0000',
    'GREEN': '#00ff00',
    'BLUE': '#0000ff',
}


class ImageBytes(bytes):
    """Wrapper class to make repr of image bytes better in ipython."""

    def __new__(cls, source: bytes, mimetype: str = None):
        self = super().__new__(cls, source)
        self._mime_type = mimetype
        return self

    @property
    def mimetype(self):
        return self._mime_type

    def _repr_png_(self):
        if self.mimetype == 'image/png':
            return self

    def _repr_jpeg_(self):
        if self.mimetype == 'image/jpeg':
            return self

    def __repr__(self):
        if self.mimetype:
            return f'ImageBytes<{len(self)}> ({self.mimetype})'
        return f'ImageBytes<{len(self)}> (wrapped image bytes)'


def _encodeImageBinary(image, encoding, jpegQuality, jpegSubsampling, tiffCompression):
    """
    Encode a PIL Image to a binary representation of the image (a jpeg, png, or
    tif).

    :param image: a PIL image.
    :param encoding: a valid PIL encoding (typically 'PNG' or 'JPEG').  Must
        also be in the TileOutputMimeTypes map.
    :param jpegQuality: the quality to use when encoding a JPEG.
    :param jpegSubsampling: the subsampling level to use when encoding a JPEG.
    :param tiffCompression: the compression format to use when encoding a TIFF.
    :returns: a binary image or b'' if the image is of zero size.
    """
    encoding = TileOutputPILFormat.get(encoding, encoding)
    if image.width == 0 or image.height == 0:
        return b''
    params = {}
    if encoding == 'JPEG':
        if image.mode not in ({'L', 'RGB', 'RGBA'} if simplejpeg else {'L', 'RGB'}):
            image = image.convert('RGB' if image.mode != 'LA' else 'L')
        if simplejpeg:
            return ImageBytes(simplejpeg.encode_jpeg(
                _imageToNumpy(image)[0],
                quality=jpegQuality,
                colorspace=image.mode if image.mode in {'RGB', 'RGBA'} else 'GRAY',
                colorsubsampling={-1: '444', 0: '444', 1: '422', 2: '420'}.get(
                    jpegSubsampling, str(jpegSubsampling).strip(':')),
            ), mimetype='image/jpeg')
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
    output = io.BytesIO()
    try:
        image.save(output, encoding, **params)
    except Exception:
        retry = True
        if image.mode not in {'RGB', 'L'}:
            image = image.convert('RGB')
            try:
                image.convert('RGB').save(output, encoding, **params)
                retry = False
            except Exception:
                pass
        if retry:
            image.convert('1').save(output, encoding, **params)
    return ImageBytes(
        output.getvalue(),
        mimetype=f'image/{encoding.lower().replace("tiled", "tiff")}'
    )


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
        imageData = _encodeImageBinary(
            image, encoding, jpegQuality, jpegSubsampling, tiffCompression)
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
        if image.dtype == numpy.uint32:
            image = numpy.floor_divide(image, 2 ** 24).astype(numpy.uint8)
        elif image.dtype == numpy.uint16:
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
    color = PIL.ImageColor.getcolor(colormap.get(fill, fill), image.mode)
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
    :param shrinkMode: one of vips's VipsRegionShrink strings.
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
    # For lossless modes, make sure pixel values in lower resolutions are
    # values that exist in the upper resolutions.
    if convertParams['compression'] in {'none', 'lzw'}:
        convertParams['region_shrink'] = 'nearest'
    if kwargs.get('shrinkMode') and kwargs['shrinkMode'] != 'default':
        convertParams['region_shrink'] = kwargs['shrinkMode']
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
                arr.append(PIL.ImageColor.getcolor(str(colormap.get(clr, clr)), 'RGBA'))
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
            PIL.ImageColor.getcolor(str(colormap.get(value, value)), 'RGBA')
            palette = ['#000', str(value)]
        except ValueError:
            pass
    if palette is None:
        import palettable

        try:
            palette = attrgetter(str(value))(palettable).hex_colors
        except AttributeError:
            pass
    if palette is None:
        try:
            import matplotlib

            if value in matplotlib.colors.get_named_colors_mapping():
                palette = ['#0000', matplotlib.colors.to_hex(value)]
            else:
                cmap = matplotlib.colormaps.get_cmap(value) if hasattr(getattr(
                    matplotlib, 'colormaps', None), 'get_cmap') else matplotlib.cm.get_cmap(value)
                palette = [matplotlib.colors.to_hex(cmap(i)) for i in range(cmap.N)]
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
    import palettable

    palettes = set()
    if includeColors:
        palettes |= set(PIL.ImageColor.colormap.keys())
        palettes |= set(colormap.keys())
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


def _makeSameChannelDepth(arr1, arr2):
    """
    Given two numpy arrays that are either two or three dimensions, make the
    third dimension the same for both of them.  Specifically, if they are two
    dimensions, first convert to trhee dimensions with a single final value.
    Otherwise, the dimensions are assumed to be channels of L, LA, RGB, RGBA,
    or <all colors>.  If L is needed to change to RGB, it is repeated (LLL).
    Missing A channels are filled with 1.

    :param arr1: one array to compare.
    :param arr2: a second array to compare.
    :returns: the two arrays, possibly modified.
    """
    arrays = {
        'arr1': arr1,
        'arr2': arr2,
    }
    # Make sure we have 3 dimensional arrays
    for key, arr in arrays.items():
        if len(arr.shape) == 2:
            arrays[key] = numpy.resize(arr, (arr.shape[0], arr.shape[1], 1))
    # If any array is RGB, make sure all arrays are RGB.
    for key, arr in arrays.items():
        other = arrays['arr1' if key == 'arr2' else 'arr2']
        if arr.shape[2] < 3 and other.shape[2] >= 3:
            newarr = numpy.ones((arr.shape[0], arr.shape[1], arr.shape[2] + 2))
            newarr[:, :, 0:1] = arr[:, :, 0:1]
            newarr[:, :, 1:2] = arr[:, :, 0:1]
            newarr[:, :, 2:3] = arr[:, :, 0:1]
            if arr.shape[2] == 2:
                newarr[:, :, 3:4] = arr[:, :, 1:2]
            arrays[key] = newarr
    # If only one array has an A channel, make sure all arrays have an A
    # channel
    for key, arr in arrays.items():
        other = arrays['arr1' if key == 'arr2' else 'arr2']
        if arr.shape[2] < other.shape[2]:
            newarr = numpy.ones((arr.shape[0], arr.shape[1], other.shape[2]))
            newarr[:, :, :arr.shape[2]] = arr
            arrays[key] = newarr
    return arrays['arr1'], arrays['arr2']


def _computeFramesPerTexture(opts, numFrames, sizeX, sizeY):
    """
    Compute the number of frames for each tile_frames texture.

    :param opts: the options dictionary from getTileFramesQuadInfo.
    :param numFrames: the number of frames that need to be included.
    :param sizeX: the size of one frame of the image.
    :param sizeY: the size of one frame of the image.
    :returns: a tuple consisting of:
        fw: the width of an individual frame in the texture.
        fh: the height of an individual frame in the texture.
        fhorz:  the number of frames across the texture/
        fperframe: the number of frames per texture.  The last texture may have
            fewer frames.
        textures: the number of textures to be used.  This many calls will need
            to be made to tileFrames.
    """
    # defining fw, fh, fhorz, fvert, fperframe
    alignment = opts['alignment'] or 16
    texSize = opts['maxTextureSize']
    textures = opts['maxTextures'] or 1
    while texSize ** 2 > opts['maxTotalTexturePixels']:
        texSize //= 2
    while textures > 1 and texSize ** 2 * textures > opts['maxTotalTexturePixels']:
        textures -= 1
    # Iterate in case we can reduce the number of textures or the texture size
    while True:
        f = int(math.ceil(numFrames / textures))  # frames per texture
        if opts['frameGroup'] > 1:
            fg = int(math.ceil(f / opts['frameGroup'])) * opts['frameGroup']
            if fg / f <= opts['frameGroupFactor']:
                f = fg
        texScale2 = texSize ** 2 / f / sizeX / sizeY
        # frames across the texture
        fhorz = int(math.ceil(texSize / (math.ceil(
            sizeX * texScale2 ** 0.5 / alignment) * alignment)))
        fvert = int(math.ceil(texSize / (math.ceil(
            sizeY * texScale2 ** 0.5 / alignment) * alignment)))
        # tile sizes
        fw = int(math.floor(texSize / fhorz / alignment)) * alignment
        fvert = int(max(math.ceil(f / (texSize // fw)), fvert))
        fh = int(math.floor(texSize / fvert / alignment) * alignment)
        if opts['maxFrameSize']:
            maxFrameSize = opts['maxFrameSize'] // alignment * alignment
            fw = min(fw, maxFrameSize)
            fh = min(fh, maxFrameSize)
        if fw > sizeX:
            fw = int(math.ceil(sizeX / alignment) * alignment)
        if fh > sizeY:
            fh = int(math.ceil(sizeY / alignment) * alignment)
        # shrink one dimension to account for aspect ratio
        fw = int(min(math.ceil(fh * sizeX / sizeY / alignment) * alignment, fw))
        fh = int(min(math.ceil(fw * sizeY / sizeX / alignment) * alignment, fh))
        # recompute frames across the texture
        fhorz = texSize // fw
        fvert = int(min(texSize // fh, math.ceil(numFrames / fhorz)))
        fperframe = fhorz * fvert
        if textures > 1 and opts['frameGroup'] > 1:
            fperframe = int(fperframe // opts['frameGroup'] * opts['frameGroup'])
            if textures * fperframe < numFrames and fhorz * fvert * textures >= numFrames:
                fperframe = fhorz * fvert
        # check if we are not using all textures or are using less than a
        # quarter of one texture.  If not, stop, if so, reduce and recalculate
        if textures > 1 and numFrames <= fperframe * (textures - 1):
            textures -= 1
            continue
        if fhorz >= 2 and math.ceil(f / (fhorz // 2)) * fh <= texSize / 2:
            texSize //= 2
            continue
        return fw, fh, fhorz, fperframe, textures


def getTileFramesQuadInfo(metadata, options=None):
    """
    Compute what tile_frames need to be requested for a particular condition.

    :param metadata: the tile source metadata.  Needs to contain sizeX, sizeY,
        tileWidth, tileHeight, and a list of frames.
    :param options: dictionary of
        format: The compression and format for the texture.  Defaults to
            {'encoding': 'JPEG', 'jpegQuality': 85, 'jpegSubsampling': 1}.
        query: Additional query options to add to the tile source, such as
            style.
        frameBase: (default 0) Starting frame number used.  c/z/xy/z to step
            through that index length (0 to 1 less than the value), which is
            probably only useful for cache reporting or scheduling.
        frameStride: (default 1) Only use every ``frameStride`` frame of the
            image.  c/z/xy/z to use that axis length.
        frameGroup: (default 1) If above 1 and multiple textures are used, each
            texture will have an even multiple of the group size number of
            frames.  This helps control where texture loading transitions
            occur.  c/z/xy/z to use that axis length.
        frameGroupFactor: (default 4) If ``frameGroup`` would reduce the size
            of the tile images beyond this factor, don't use it.
        frameGroupStride: (default 1) If ``frameGroup`` is above 1 and multiple
            textures are used, then the frames are reordered based on this
            stride value.  "auto" to use frameGroup / frameStride if that
            value is an integer.
        maxTextureSize: Limit the maximum texture size to a square of this
            size.
        maxTextures: (default 1) If more than one, allow multiple textures to
            increase the size of the individual frames.  The number of textures
            will be capped by ``maxTotalTexturePixels`` as well as this number.
        maxTotalTexturePixels: (default 1073741824) Limit the maximum texture
            size and maximum number of textures so that the combined set does
            not exceed this number of pixels.
        alignment: (default 16) Individual frames are buffered to an alignment
            of this maxy pixels.  If JPEG compression is used, this should
            be 8 for monochrome images or jpegs without subsampling, or 16 for
            jpegs with moderate subsampling to avoid compression artifacts from
            leaking between frames.
        maxFrameSize: If set, limit the maximum width and height of an
            individual frame to this value.
    :returns: a dictionary of values to use for making calls to tile_frames.
    """
    defaultOptions = {
        'format': {
            'encoding': 'JPEG',
            'jpegQuality': 85,
            'jpegSubsampling': 1,
        },
        'query': {},
        'frameBase': 0,
        'frameStride': 1,
        'frameGroup': 1,
        'frameGroupFactor': 4,
        'frameGroupStride': 1,
        'maxTextureSize': 16384,
        'maxTextures': 1,
        'maxTotalTexturePixels': 1024 * 1024 * 1024,
        'alignment': 16,
        'maxFrameSize': None,
    }
    opts = defaultOptions.copy()
    opts.update(options or {})

    opts['frameStride'] = (
        int(opts['frameStride']) if str(opts['frameStride']).isdigit() else
        metadata.get('IndexRange', {}).get('Index' + opts['frameStride'].upper(), 1))
    opts['frameGroup'] = (
        int(opts['frameGroup']) if str(opts['frameGroup']).isdigit() else
        metadata.get('IndexRange', {}).get('Index' + opts['frameGroup'].upper(), 1))
    opts['frameGroupStride'] = (
        int(opts['frameGroupStride']) if opts['frameGroupStride'] != 'auto' else
        max(1, opts['frameGroup'] // opts['frameStride']))
    if str(opts['frameBase']).isdigit():
        opts['frameBase'] = int(opts['frameBase'])
    else:
        status = {
            'metadata': metadata,
            'options': opts,
            'src': [],
        }
        for val in range(metadata.get(
                'IndexRange', {}).get('Index' + opts['frameBase'].upper(), 1)):
            opts['frameBase'] = val
            result = getTileFramesQuadInfo(metadata, opts)
            status['src'].extend(result['src'])
        return status
    sizeX, sizeY = metadata['sizeX'], metadata['sizeY']
    numFrames = len(metadata.get('frames', [])) or 1
    frames = []
    for fds in range(opts['frameGroupStride']):
        frames.extend(list(range(
            opts['frameBase'] + fds * opts['frameStride'], numFrames,
            opts['frameStride'] * opts['frameGroupStride'])))
    numFrames = len(frames)
    # check if numFrames zero and return early?
    fw, fh, fhorz, fperframe, textures = _computeFramesPerTexture(
        opts, numFrames, sizeX, sizeY)
    # used area of each tile
    usedw = int(math.floor(sizeX / max(sizeX / fw, sizeY / fh)))
    usedh = int(math.floor(sizeY / max(sizeX / fw, sizeY / fh)))
    # get the set of texture images
    status = {
        'metadata': metadata,
        'options': opts,
        'src': [],
        'quads': [],
        'quadsToIdx': [],
        'frames': frames,
        'framesToIdx': {}
    }
    if metadata.get('tileWidth') and metadata.get('tileHeight'):
        # report that tiles below this level are not needed
        status['minLevel'] = int(math.ceil(math.log(min(
            usedw / metadata['tileWidth'], usedh / metadata['tileHeight'])) / math.log(2)))
    status['framesToIdx'] = {frame: idx for idx, frame in enumerate(frames)}
    for idx in range(textures):
        frameList = frames[idx * fperframe: (idx + 1) * fperframe]
        tfparams = {
            'framesAcross': fhorz,
            'width': fw,
            'height': fh,
            'fill': 'corner:black',
            'exact': False,
        }
        if len(frameList) != len(metadata.get('frames', [])):
            tfparams['frameList'] = frameList
        tfparams.update(opts['format'])
        tfparams.update(opts['query'])
        status['src'].append(tfparams)
        f = len(frameList)
        ivert = int(math.ceil(f / fhorz))
        ihorz = int(min(f, fhorz))
        for fidx in range(f):
            quad = {
                # z = -1 to place under other tile layers
                'ul': {'x': 0, 'y': 0, 'z': -1},
                # y coordinate is inverted
                'lr': {'x': sizeX, 'y': -sizeY, 'z': -1},
                'crop': {
                    'x': sizeX,
                    'y': sizeY,
                    'left': (fidx % ihorz) * fw,
                    'top': (ivert - (fidx // ihorz)) * fh - usedh,
                    'right': (fidx % ihorz) * fw + usedw,
                    'bottom': (ivert - (fidx // ihorz)) * fh,
                },
            }
            status['quads'].append(quad)
            status['quadsToIdx'].append(idx)
    return status


def histogramThreshold(histogram, threshold, fromMax=False):
    """
    Given a histogram and a threshold on a scale of [0, 1], return the bin
    edge that excludes no more than the specified threshold amount of values.
    For instance, a threshold of 0.02 would exclude at most 2% of the values.

    :param histogram: a histogram record for a specific channel.
    :param threshold: a value from 0 to 1.
    :param fromMax: if False, return values excluding the low end of the
        histogram; if True, return values from excluding the high end of the
        histogram.
    :returns: the value the excludes no more than the threshold from the
        specified end.
    """
    hist = histogram['hist']
    edges = histogram['bin_edges']
    samples = histogram['samples'] if not histogram.get('density') else 1
    if fromMax:
        hist = hist[::-1]
        edges = edges[::-1]
    tally = 0
    for idx in range(len(hist)):
        if tally >= threshold * samples:
            if not idx:
                return histogram['min' if not fromMax else 'max']
            return edges[idx]
        tally += hist[idx]
    return edges[-1]


def addPILFormatsToOutputOptions():
    """
    Check PIL for available formats that be saved and add them to the lists of
    of available formats.
    """
    # Call this to actual register the extensions
    PIL.Image.registered_extensions()
    for key, value in PIL.Image.MIME.items():
        # We don't support these formats; ICNS and ICO have fixed sizes; PALM
        # and PDF can't be read back by PIL without extensions
        if key in {'ICNS', 'ICO', 'PALM', 'PDF'}:
            continue
        if key not in TileOutputMimeTypes and key in PIL.Image.SAVE:
            TileOutputMimeTypes[key] = value
    for key, value in PIL.Image.registered_extensions().items():
        key = key.lstrip('.')
        if (key not in TileOutputMimeTypes and value in TileOutputMimeTypes and
                key not in TileOutputPILFormat):
            TileOutputPILFormat[key] = value


addPILFormatsToOutputOptions()
