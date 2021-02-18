import concurrent.futures
import datetime
import fractions
import json
import logging
import math
import os
from pkg_resources import DistributionNotFound, get_distribution
import psutil
import struct
from tempfile import TemporaryDirectory
import threading
import time

import numpy
import tifftools

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


logger = logging.getLogger('large-image-converter')


def _data_from_large_image(path, outputPath, **kwargs):
    """
    Check if the input file can be read by installed large_image tile sources.
    If so, return the metadata, internal metadata, and extract each associated
    image.

    :param path: path of the file.
    :param outputPath: the name of a temporary output file.
    :returns: a dictionary of metadata, internal_metadata, and images.  images
        is a dictionary of keys and paths.  Returns None if the path is not
        readable by large_image.
    """
    try:
        import large_image
    except ImportError:
        return

    _import_pyvips()
    try:
        ts = large_image.getTileSource(path)
    except Exception:
        return
    results = {
        'metadata': ts.getMetadata(),
        'internal_metadata': ts.getInternalMetadata(),
        'images': {},
        'tilesource': ts,
    }
    tasks = []
    pool = _get_thread_pool(**kwargs)
    for key in ts.getAssociatedImagesList():
        try:
            img, mime = ts.getAssociatedImage(key)
        except Exception:
            continue
        savePath = outputPath + '-%s-%s.tiff' % (key, time.strftime('%Y%m%d-%H%M%S'))
        # TODO: allow specifying quality separately from main image quality
        tasks.append((pool.submit(
            _convert_via_vips, img, savePath, outputPath, mime=mime, forTiled=False), ))
        results['images'][key] = savePath
    _drain_pool(pool, tasks)
    return results


def _generate_geotiff(inputPath, outputPath, **kwargs):
    """
    Take a source input file, readable by gdal, and output a cloud-optimized
    geotiff file.  See https://gdal.org/drivers/raster/cog.html.

    :params inputPath: the path to the input file or base file of a set.
    :params outputPath: the path of the output file.
    Optional parameters that can be specified in kwargs:
    :params tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', or 'zstd'.
    :params quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', 'float', or 'yes' used for
        lzw and deflate.
    """
    from osgeo import gdal
    from osgeo import gdalconst

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
    cmdopt = ['-of', 'COG', '-co', 'BIGTIFF=YES']
    cmdopt += ['-co', 'BLOCKSIZE=%d' % options['tileSize']]
    cmdopt += ['-co', 'COMPRESS=%s' % options['compression'].upper()]
    cmdopt += ['-co', 'QUALITY=%s' % options['quality']]
    cmdopt += ['-co', 'PREDICTOR=%s' % predictor[options['predictor']]]
    if 'level' in options:
        cmdopt += ['-co', 'LEVEL=%s' % options['level']]
    cmd = ['gdal_translate', inputPath, outputPath] + cmdopt
    logger.info('Convert to geotiff: %r' % (cmd))
    try:
        # subprocess.check_call(cmd)
        ds = gdal.Open(inputPath, gdalconst.GA_ReadOnly)
        gdal.Translate(outputPath, ds, options=cmdopt)
    except Exception:
        os.unlink(outputPath)
        raise


def _generate_multiframe_tiff(inputPath, outputPath, tempPath, lidata, **kwargs):
    """
    Take a source input file with multiple frames and output a multi-pyramidal
    tiff file.

    :params inputPath: the path to the input file or base file of a set.
    :params outputPath: the path of the output file.
    :params tempPath: a temporary file in a temporary directory.
    :params lidata: data from a large_image tilesource including associated
        images.
    Optional parameters that can be specified in kwargs:
    :params tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'jp2k'.
    :params quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    """
    _import_pyvips()

    image = pyvips.Image.new_from_file(inputPath)
    width = image.width
    height = image.height
    pages = 1
    if 'n-pages' in image.get_fields():
        pages = image.get_value('n-pages')
    # Now check if there are other images we need to convert or preserve
    outputList = []
    imageSizes = []
    tasks = []
    pool = _get_thread_pool(**kwargs)
    # Process each image separately to pyramidize it
    for page in range(pages):
        subInputPath = inputPath + '[page=%d]' % page
        subImage = pyvips.Image.new_from_file(subInputPath)
        imageSizes.append((subImage.width, subImage.height, subInputPath, page))
        if subImage.width != width or subImage.height != height:
            if subImage.width * subImage.height <= width * height:
                continue
            logger.info('Bigger image found (was %dx%d, now %dx%d)', (
                width, height, subImage.width, subImage.height))
            for path in outputList:
                os.unlink(path)
            width = subImage.width
            height = subImage.height
        subOutputPath = tempPath + '-%d-%s.tiff' % (
            page + 1, time.strftime('%Y%m%d-%H%M%S'))
        tasks.append((pool.submit(
            _convert_via_vips, subInputPath, subOutputPath, tempPath,
            status='%d/%d' % (page, pages), **kwargs), ))
        outputList.append(subOutputPath)
    extraImages = {}
    if not lidata or not len(lidata['images']):
        # If we couldn't extract images from li, try to detect non-primary
        # images from the original file.  These are any images who size is
        # not a power of two division of the primary image size
        possibleSizes = _list_possible_sizes(width, height)
        for w, h, subInputPath, page in imageSizes:
            if (w, h) not in possibleSizes:
                key = 'image_%d' % page
                savePath = tempPath + '-%s-%s.tiff' % (key, time.strftime('%Y%m%d-%H%M%S'))
                tasks.append((pool.submit(
                    _convert_via_vips, subInputPath, savePath, tempPath, False), ))
                extraImages[key] = savePath
    _drain_pool(pool, tasks)
    _output_tiff(outputList, outputPath, lidata, extraImages, **kwargs)


def _generate_tiff(inputPath, outputPath, tempPath, lidata, **kwargs):
    """
    Take a source input file, readable by vips, and output a pyramidal tiff
    file.

    :params inputPath: the path to the input file or base file of a set.
    :params outputPath: the path of the output file.
    :params tempPath: a temporary file in a temporary directory.
    :params lidata: data from a large_image tilesource including associated
        images.
    Optional parameters that can be specified in kwargs:
    :params tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'jp2k'.
    :params quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    """
    _import_pyvips()
    subOutputPath = tempPath + '-%s.tiff' % (time.strftime('%Y%m%d-%H%M%S'))
    _convert_via_vips(inputPath, subOutputPath, tempPath, **kwargs)
    _output_tiff([subOutputPath], outputPath, lidata, **kwargs)


def _convert_via_vips(inputPathOrBuffer, outputPath, tempPath, forTiled=True,
                      status=None, **kwargs):
    # This is equivalent to a vips command line of
    #  vips tiffsave <input path> <output path>
    # followed by the convert params in the form of --<key>[=<value>] where no
    # value needs to be specified if they are True.
    convertParams = _vips_parameters(forTiled, **kwargs)
    status = (', ' + status) if status else ''
    if type(inputPathOrBuffer) == pyvips.vimage.Image:
        source = 'vips image'
        image = inputPathOrBuffer
    elif type(inputPathOrBuffer) == bytes:
        source = 'buffer'
        image = pyvips.Image.new_from_buffer(inputPathOrBuffer, '')
    else:
        source = inputPathOrBuffer
        image = pyvips.Image.new_from_file(inputPathOrBuffer)
    logger.info('Input: %s, Output: %s, Options: %r%s' % (
        source, outputPath, convertParams, status))
    image = image.autorot()
    if convertParams['compression'] not in {'jpeg'}:
        image = _vips_cast(
            image,
            convertParams['compression'] in {'webp'} or (
                kwargs.get('compression') == 'jp2k' and 'psnr' not in kwargs and 'cr' in kwargs))
    # TODO: revisit the TMPDIR override; this is not thread safe
    oldtmpdir = os.environ.get('TMPDIR')
    os.environ['TMPDIR'] = os.path.dirname(tempPath)
    try:
        image.write_to_file(outputPath, **convertParams)
    finally:
        if oldtmpdir is not None:
            os.environ['TMPDIR'] = oldtmpdir
        else:
            del os.environ['TMPDIR']
    if kwargs.get('compression') == 'jp2k':
        _convert_to_jp2k(outputPath, **kwargs)


def _convert_to_jp2k_tile(lock, fptr, dest, offset, length, shape, dtype, jp2kargs):
    """
    Read an uncompressed tile from a file and save it as a JP2000 file.

    :param lock: a lock to ensure exclusive access to the file.
    :param fptr: a pointer to the open file.
    :param dest: the output path for the jp2k file.
    :param offset: the location in the input file with the data.
    :param length: the number of bytes to read.
    :param shape: a tuple with the shape of the tile to read.  This is usually
        (height, width, channels).
    :param dtype: the numpy dtype of the data in the tile.
    :param jp2kargs: arguments to pass to the compression, such as psnr or
        cratios.
    """
    import glymur

    with lock:
        fptr.seek(offset)
        data = fptr.read(length)
    data = numpy.frombuffer(data, dtype=dtype)
    data = numpy.reshape(data, shape)
    glymur.Jp2k(dest, data=data, **jp2kargs)


def _get_thread_pool(**kwargs):
    """
    Allocate a thread pool based on the specifiec concurrency.
    """
    concurrency = psutil.cpu_count(logical=True)
    if kwargs.get('_concurrency'):
        concurrency = int(kwargs['_concurrency'])
    return concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)


def _drain_pool(pool, tasks):
    """
    Wait for all tasks in a pool to complete, then shutdown the pool.

    :param pool: a concurrent futures pool.
    :param tasks: a list contiaining either lists or tuples, the last element
        of which is a task submitted to the pool.  Altered.
    """
    while len(tasks):
        # This allows better stopping on a SIGTERM
        try:
            tasks[0][-1].result(0.1)
        except concurrent.futures.TimeoutError:
            continue
        tasks.pop(0)
    pool.shutdown(False)


def _convert_to_jp2k(path, **kwargs):
    """
    Given a tiled tiff file without compression, convert it to jp2k compression
    using the gylmur library.  This expects a tiff as written by vips without
    any subifds.

    :param path: the path of the tiff file.  The file is altered.
    :param psnr: if set, the target psnr.  0 for lossless.
    :param cr: is set, the target compression ratio.  1 for lossless.
    """
    info = tifftools.read_tiff(path)
    jp2kargs = {}
    if 'psnr' in kwargs:
        jp2kargs['psnr'] = [int(kwargs['psnr'])]
    elif 'cr' in kwargs:
        jp2kargs['cratios'] = [int(kwargs['cr'])]
    tilecount = sum(len(ifd['tags'][tifftools.Tag.TileOffsets.value]['data'])
                    for ifd in info['ifds'])
    processed = 0
    lastlog = 0
    tasks = []
    lock = threading.Lock()
    pool = _get_thread_pool(**kwargs)
    with open(path, 'r+b') as fptr:
        for ifd in info['ifds']:
            ifd['tags'][tifftools.Tag.Compression.value]['data'][0] = (
                tifftools.constants.Compression.JP2000)
            shape = (
                ifd['tags'][tifftools.Tag.TileHeight.value]['data'][0],
                ifd['tags'][tifftools.Tag.TileLength.value]['data'][0],
                len(ifd['tags'][tifftools.Tag.BitsPerSample.value]['data']))
            dtype = numpy.uint16 if ifd['tags'][
                tifftools.Tag.BitsPerSample.value]['data'][0] == 16 else numpy.uint8
            for idx, offset in enumerate(ifd['tags'][tifftools.Tag.TileOffsets.value]['data']):
                tmppath = path + '%d.jp2k' % processed
                tasks.append((ifd, idx, processed, tmppath, pool.submit(
                    _convert_to_jp2k_tile, lock, fptr, tmppath, offset,
                    ifd['tags'][tifftools.Tag.TileByteCounts.value]['data'][idx],
                    shape, dtype, jp2kargs)))
                processed += 1
        while len(tasks):
            try:
                tasks[0][-1].result(0.1)
            except concurrent.futures.TimeoutError:
                continue
            ifd, idx, processed, tmppath, task = tasks.pop(0)
            data = open(tmppath, 'rb').read()
            os.unlink(tmppath)
            # Remove first comment marker.  It adds needless bytes
            compos = data.find(b'\xff\x64')
            if compos >= 0 and compos + 4 < len(data):
                comlen = struct.unpack('>H', data[compos + 2:compos + 4])[0]
                if compos + 2 + comlen + 1 < len(data) and data[compos + 2 + comlen] == 0xff:
                    data = data[:compos] + data[compos + 2 + comlen:]
            with lock:
                fptr.seek(0, os.SEEK_END)
                ifd['tags'][tifftools.Tag.TileOffsets.value]['data'][idx] = fptr.tell()
                ifd['tags'][tifftools.Tag.TileByteCounts.value]['data'][idx] = len(data)
                fptr.write(data)
            if time.time() - lastlog >= 10 and tilecount > 1:
                logger.debug('Converted %d of %d tiles to jp2k', processed + 1, tilecount)
                lastlog = time.time()
        pool.shutdown(False)
        fptr.seek(0, os.SEEK_END)
        for ifd in info['ifds']:
            ifd['size'] = fptr.tell()
        info['size'] = fptr.tell()
    tmppath = path + '.jp2k.tiff'
    tifftools.write_tiff(info, tmppath, bigtiff=False, allowExisting=True)
    os.unlink(path)
    os.rename(tmppath, path)


def _convert_large_image(inputPath, outputPath, tempPath, lidata, **kwargs):
    """
    Take a large_image source and convert it by resaving each tiles image with
    vips.

    :params inputPath: the path to the input file or base file of a set.
    :params outputPath: the path of the output file.
    :params tempPath: a temporary file in a temporary directory.
    :params lidata: data from a large_image tilesource including associated
        images.
    """
    ts = lidata['tilesource']
    numFrames = len(lidata['metadata'].get('frames', [0]))
    outputList = []
    _iterTileSize = 1024
    tasks = []
    pool = _get_thread_pool(**kwargs)
    for frame in range(numFrames):
        subOutputPath = tempPath + '-%d-%s.tiff' % (
            frame + 1, time.strftime('%Y%m%d-%H%M%S'))
        strips = []
        for tile in ts.tileIterator(tile_size=dict(width=_iterTileSize), frame=frame):
            data = tile['tile']
            dtypeToGValue = {
                'b': 'char',
                'B': 'uchar',
                'd': 'double',
                'D': 'dpcomplex',
                'f': 'float',
                'F': 'complex',
                'h': 'short',
                'H': 'ushort',
                'i': 'int',
                'I': 'uint',
            }
            if data.dtype.char not in dtypeToGValue:
                data = data.astype('d')
            vimg = pyvips.Image.new_from_memory(
                numpy.ascontiguousarray(data).data,
                data.shape[1], data.shape[0], data.shape[2],
                dtypeToGValue[data.dtype.char])
            x = tile['x']
            ty = tile['tile_position']['level_y']
            if ty >= len(strips):
                strips.append(vimg)
            else:
                strips[ty] = strips[ty].insert(vimg, x, 0, expand=True)
        img = strips[0]
        for stripidx in range(1, len(strips)):
            img = img.insert(strips[stripidx], 0, stripidx * _iterTileSize, expand=True)
        tasks.append((pool.submit(
            _convert_via_vips, img, subOutputPath, tempPath,
            status='%d/%d' % (frame, numFrames), **kwargs), ))
        outputList.append(subOutputPath)
    _drain_pool(pool, tasks)
    _output_tiff(outputList, outputPath, lidata, **kwargs)


def _output_tiff(inputs, outputPath, lidata, extraImages=None, **kwargs):
    """
    Given a list of input tiffs and data as parsed by _data_from_large_image,
    generate an output tiff file with the associated images, correct scale, and
    other metadata.

    :param inputs: a list of pyramidal input files.
    :param outputPath: the final destination.
    :param lidata: large_image data including metadata and associated images.
    :param extraImages: an optional dictionary of keys and paths to add as
        extra associated images.
    """
    logger.debug('Reading %s' % inputs[0])
    info = tifftools.read_tiff(inputs[0])
    imgDesc = info['ifds'][0]['tags'].get(tifftools.Tag.ImageDescription.value)
    description = _make_li_description(
        len(info['ifds']), len(inputs), lidata,
        (len(extraImages) if extraImages else 0) + (len(lidata['images']) if lidata else 0),
        imgDesc['data'] if imgDesc else None, **kwargs)
    info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value] = {
        'data': description,
        'datatype': tifftools.Datatype.ASCII,
    }
    if lidata:
        _set_resolution(info['ifds'], lidata['metadata'])
    if len(inputs) > 1:
        if kwargs.get('subifds') is not False:
            info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value] = {
                'ifds': info['ifds'][1:]
            }
            info['ifds'][1:] = []
        for idx, inputPath in enumerate(inputs):
            if not idx:
                continue
            logger.debug('Reading %s' % inputPath)
            nextInfo = tifftools.read_tiff(inputPath)
            if lidata:
                _set_resolution(nextInfo['ifds'], lidata['metadata'])
                if len(lidata['metadata'].get('frames', [])) > idx:
                    nextInfo['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value] = {
                        'data': json.dumps(
                            {'frame': lidata['metadata']['frames'][idx]},
                            separators=(',', ':'), sort_keys=True, default=json_serial),
                        'datatype': tifftools.Datatype.ASCII,
                    }
            if kwargs.get('subifds') is not False:
                nextInfo['ifds'][0]['tags'][tifftools.Tag.SubIFD.value] = {
                    'ifds': nextInfo['ifds'][1:]
                }
                info['ifds'].append(nextInfo['ifds'][0])
            else:
                info['ifds'].extend(nextInfo['ifds'])
    assocList = []
    if lidata:
        assocList += list(lidata['images'].items())
    if extraImages:
        assocList += list(extraImages.items())
    for key, assocPath in assocList:
        logger.debug('Reading %s' % assocPath)
        assocInfo = tifftools.read_tiff(assocPath)
        assocInfo['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value] = {
            'data': key,
            'datatype': tifftools.Datatype.ASCII,
        }
        info['ifds'] += assocInfo['ifds']
    logger.debug('Writing %s' % outputPath)
    tifftools.write_tiff(info, outputPath, bigEndian=False, bigtiff=False, allowExisting=True)


def _set_resolution(ifds, metadata):
    """
    Given metadata with a scale in mm_x and/or mm_y, set the resolution for
    each ifd, assuming that each one is half the scale of the previous one.

    :param ifds: a list of ifds from a single pyramid.  The resolution may be
        set on each one.
    :param metadata: metadata with a scale specified by mm_x and/or mm_y.
    """
    if metadata.get('mm_x') or metadata.get('mm_y'):
        for idx, ifd in enumerate(ifds):
            ifd['tags'][tifftools.Tag.ResolutionUnit.value] = {
                'data': [tifftools.constants.ResolutionUnit.Centimeter],
                'datatype': tifftools.Datatype.SHORT,
            }
            for mkey, tkey in (('mm_x', 'XResolution'), ('mm_y', 'YResolution')):
                if metadata[mkey]:
                    val = fractions.Fraction(
                        10.0 / (metadata[mkey] * 2 ** idx)).limit_denominator()
                    if val.numerator >= 2**32 or val.denominator >= 2**32:
                        origval = val
                        denom = 1000000
                        while val.numerator >= 2**32 or val.denominator >= 2**32 and denom > 1:
                            denom = int(denom / 10)
                            val = origval.limit_denominator(denom)
                    if val.numerator >= 2**32 or val.denominator >= 2**32:
                        continue
                    ifd['tags'][tifftools.Tag[tkey].value] = {
                        'data': [val.numerator, val.denominator],
                        'datatype': tifftools.Datatype.RATIONAL,
                    }


def _import_pyvips():
    """
    Import pyvips on demand.
    """
    global pyvips

    import pyvips


def _is_eightbit(path, tiffinfo=None):
    """
    Check if a path has an unsigned 8-bit per sample data size.  If any known
    channel is otherwise or this is unknown, this returns False.

    :params path: The path to the file
    :params tiffinfo: data extracted from tifftools.read_tiff(path).
    :returns: True if known to be 8 bits per sample.
    """
    if not tiffinfo:
        return False
    try:
        if not all(val == tifftools.constants.SampleFormat.uint for val in
                   tiffinfo['ifds'][0]['tags'][tifftools.Tag.SampleFormat.value]['data']):
            return False
        if tifftools.Tag.BitsPerSample.value in tiffinfo['ifds'][0]['tags'] and not all(
                val == 8 for val in
                tiffinfo['ifds'][0]['tags'][tifftools.Tag.BitsPerSample.value]['data']):
            return False
    except Exception:
        return False
    return True


def _is_lossy(path, tiffinfo=None):
    """
    Check if a path uses lossy compression.  This imperfectly just checks if
    the file is a TIFF and stored in one of the JPEG formats.

    :params path: The path to the file
    :params tiffinfo: data extracted from tifftools.read_tiff(path).
    :returns: True if known to be lossy.
    """
    if not tiffinfo:
        return False
    try:
        return bool(tifftools.constants.Compression[
            tiffinfo['ifds'][0]['tags'][
                tifftools.Tag.Compression.value]['data'][0]].lossy)
    except Exception:
        return False


def _is_multiframe(path):
    """
    Check if a path is a multiframe file.

    :params path: The path to the file
    :returns: True if multiframe.
    """
    _import_pyvips()
    image = pyvips.Image.new_from_file(path)
    pages = 1
    if 'n-pages' in image.get_fields():
        pages = image.get_value('n-pages')
    return pages > 1


def _list_possible_sizes(width, height):
    """
    Given a width and height, return a list of possible sizes that could be
    reasonable powers-of-two smaller versions of that size.  This includes
    the values rounded up and down.
    """
    results = [(width, height)]
    pos = 0
    while pos < len(results):
        w, h = results[pos]
        if w > 1 or h > 1:
            w2f = int(math.floor(w / 2))
            h2f = int(math.floor(h / 2))
            w2c = int(math.ceil(w / 2))
            h2c = int(math.ceil(h / 2))
            for w2, h2 in [(w2f, h2f), (w2f, h2c), (w2c, h2f), (w2c, h2c)]:
                if (w2, h2) not in results:
                    results.append((w2, h2))
        pos += 1
    return results


def json_serial(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)


def _make_li_description(
        framePyramidSize, numFrames, lidata=None, numAssociatedImages=0,
        imageDescription=None, **kwargs):
    """
    Given the number of frames, the number of levels per frame, the associated
    image list, and any metadata from large_image, construct a json string with
    information about the whole image.

    :param framePyramidSize: the number of layers per frame.
    :param numFrames: the number of frames.
    :param lidata: the data returned from _data_from_large_image.
    :param numAssociatedImages: the number of associated images.
    :param imageDescription: if present, the original description.
    :returns: a json string
    """
    results = {
        'large_image_converter': {
            'conversion_epoch': time.time(),
            'version': __version__,
            'levels': framePyramidSize,
            'frames': numFrames,
            'associated': numAssociatedImages,
            'arguments': {
                k: v for k, v in kwargs.items()
                if not k.startswith('_') and not '_' + k in kwargs and
                k not in {'overwrite', }},
        },
    }
    if lidata:
        results['metadata'] = lidata['metadata']
        if len(lidata['metadata'].get('frames', [])) >= 1:
            results['frame'] = lidata['metadata']['frames'][0]
            if len(lidata['metadata'].get('channels', [])) >= 1:
                results['channels'] = lidata['metadata']['channels']
        results['internal'] = lidata['internal_metadata']
    if imageDescription:
        results['image_description'] = imageDescription
    return json.dumps(results, separators=(',', ':'), sort_keys=True, default=json_serial)


def _vips_cast(image, mustBe8Bit=False):
    """
    Cast a vips image to a format we want.

    :param image: a vips image
    :param mustBe9Bit: if True, then always cast to unsigned 8-bit.
    :returns: a vips image
    """
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
    if mustBe8Bit and target != pyvips.BandFormat.UCHAR:
        target = pyvips.BandFormat.UCHAR
        multiplier /= 256
    logger.debug('Casting image from %r to %r' % (image.format, target))
    image = ((image.cast(pyvips.BandFormat.DOUBLE) + offset) * multiplier).cast(target)
    return image


def _vips_parameters(forTiled=True, **kwargs):
    """
    Return a dictionary of vips conversion parameters.

    :param forTiled: True if this is for a tiled image.  False for an
        associated image.
    Optional parameters that can be specified in kwargs:
    :params tileSize: the horizontal and vertical tile size.
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
            'compression': 'jpeg',
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
        'compression': 'jpeg',
        'Q': 90,
        'predictor': 'horizontal',
    }
    for vkey, kwkey in {
        'tile_width': 'tileSize',
        'tile_height': 'tileSize',
        'compression': 'compression',
        'Q': 'quality',
        'level': 'level',
        'predictor': 'predictor',
    }.items():
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


def convert(inputPath, outputPath=None, **kwargs):
    """
    Take a source input file and output a pyramidal tiff file.

    :params inputPath: the path to the input file or base file of a set.
    :params outputPath: the path of the output file.
    Optional parameters that can be specified in kwargs:
    :params tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'none'.
    :params quality: a jpeg or webp quality passed to vips.  0 is small, 100 is
        high quality.  90 or above is recommended.  For webp, 0 is lossless.
    :param level: compression level for zstd, 1-22 (default is 10) and deflate,
        1-9.
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.  Default is horizontal.
    :param psnr: psnr value for jp2k, higher results in large files.  0 is
        lossless.
    :param cr: jp2k compression ratio.  1 is lossless, 100 will try to make
        a file 1% the size of the original, etc.
    Additional optional parameters:
    :param geospatial: if not None, a boolean indicating if this file is
        geospatial.  If not specified or None, this will be checked.

    :returns: outputPath if successful
    """
    if kwargs.get('_concurrency'):
        os.environ['VIPS_CONCURRENCY'] = str(kwargs['_concurrency'])
    geospatial = kwargs.get('geospatial')
    if geospatial is None:
        geospatial = is_geospatial(inputPath)
    if not outputPath:
        suffix = '.tiff' if not geospatial else '.geo.tiff'
        outputPath = os.path.splitext(inputPath)[0] + suffix
        if outputPath.endswith('.geo' + suffix):
            outputPath = outputPath[:len(outputPath) - len(suffix) - 4] + suffix
        if outputPath == inputPath:
            outputPath = (os.path.splitext(inputPath)[0] + '.' +
                          time.strftime('%Y%m%d-%H%M%S') + suffix)
    if os.path.exists(outputPath) and not kwargs.get('overwrite'):
        raise Exception('Output file already exists.')
    try:
        tiffinfo = tifftools.read_tiff(inputPath)
    except Exception:
        tiffinfo = None
    if not kwargs.get('compression', None):
        kwargs = kwargs.copy()
        lossy = _is_lossy(inputPath, tiffinfo)
        logger.debug('Is file lossy: %r', lossy)
        eightbit = _is_eightbit(inputPath, tiffinfo)
        logger.debug('Is file 8 bits per samples: %r', eightbit)
        kwargs['_compression'] = None
        kwargs['compression'] = 'jpeg' if lossy and eightbit else 'lzw'
    if geospatial:
        _generate_geotiff(inputPath, outputPath, **kwargs)
    else:
        with TemporaryDirectory() as tempDir:
            tempPath = os.path.join(tempDir, os.path.basename(outputPath))
            lidata = _data_from_large_image(inputPath, tempPath, **kwargs)
            logger.debug('large_image information for %s: %r' % (inputPath, lidata))
            if not is_vips(inputPath) and lidata:
                _convert_large_image(inputPath, outputPath, tempPath, lidata, **kwargs)
            elif _is_multiframe(inputPath):
                _generate_multiframe_tiff(inputPath, outputPath, tempPath, lidata, **kwargs)
            else:
                _generate_tiff(inputPath, outputPath, tempPath, lidata, **kwargs)
    return outputPath


def is_geospatial(path):
    """
    Check if a path is likely to be a geospatial file.

    :params path: The path to the file
    :returns: True if geospatial.
    """
    try:
        from osgeo import gdal
        from osgeo import gdalconst
    except ImportError:
        logger.warning('Cannot import GDAL.')
        return False
    gdal.UseExceptions()
    try:
        ds = gdal.Open(path, gdalconst.GA_ReadOnly)
    except Exception:
        return False
    if ds and (ds.GetProjection() or ds.GetDriver().ShortName in {'NITF', 'netCDF'}):
        return True
    return False


def is_vips(path):
    """
    Check if a path is readable by vips.

    :params path: The path to the file
    :returns: True if readable by vips.
    """
    _import_pyvips()
    try:
        image = pyvips.Image.new_from_file(path)
        # image(0, 0) will throw if vips can't decode the image
        if not image.width or not image.height or image(0, 0) is None:
            return False
    except Exception:
        return False
    return True
