import concurrent.futures
import datetime
import fractions
import json
import logging
import math
import os
import re
import struct
import threading
import time
from tempfile import TemporaryDirectory

import numpy
import psutil
import tifftools
from pkg_resources import DistributionNotFound, get_distribution

import large_image

from . import format_aperio

pyvips = None

try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


logger = logging.getLogger('large-image-converter')


FormatModules = {
    'aperio': format_aperio,
}

# Estimated maximum memory use per frame conversion.  Used to limit concurrent
# frame conversions.
FrameMemoryEstimate = 3 * 1024 ** 3


def _use_associated_image(key, **kwargs):
    """
    Check if an associated image key should be used.  If a list of images to
    keep was specified, it must match at least one of the regex in that list.
    If a list of images to exclude was specified, it must not any regex in that
    list.  The exclude list takes priority.
    """
    if kwargs.get('_exclude_associated'):
        for exp in kwargs['_exclude_associated']:
            if re.match(exp, key):
                return False
    if kwargs.get('_keep_associated'):
        for exp in kwargs['_keep_associated']:
            if re.match(exp, key):
                return True
        return False
    return True


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
    _import_pyvips()
    if not path.startswith('large_image://test'):
        try:
            ts = large_image.getTileSource(path)
        except Exception:
            return
    else:
        import urllib.parse

        tsparams = {
            k: int(v[0]) if v[0].isdigit() else v[0]
            for k, v in urllib.parse.parse_qs(
                path.split('?', 1)[1] if '?' in path else '').items()}
        ts = large_image.getTileSource('large_image://test', **tsparams)
    results = {
        'metadata': ts.getMetadata(),
        'internal_metadata': ts.getInternalMetadata(),
        'images': {},
        'tilesource': ts,
    }
    tasks = []
    pool = _get_thread_pool(**kwargs)
    for key in ts.getAssociatedImagesList():
        if not _use_associated_image(key, **kwargs):
            continue
        try:
            img, mime = ts.getAssociatedImage(key)
        except Exception:
            continue
        savePath = outputPath + '-%s-%s.tiff' % (key, time.strftime('%Y%m%d-%H%M%S'))
        # TODO: allow specifying quality separately from main image quality
        _pool_add(tasks, (pool.submit(
            _convert_via_vips, img, savePath, outputPath, mime=mime, forTiled=False), ))
        results['images'][key] = savePath
    _drain_pool(pool, tasks)
    return results


def _generate_geotiff(inputPath, outputPath, **kwargs):
    """
    Take a source input file, readable by gdal, and output a cloud-optimized
    geotiff file.  See https://gdal.org/drivers/raster/cog.html.

    :param inputPath: the path to the input file or base file of a set.
    :param outputPath: the path of the output file.
    Optional parameters that can be specified in kwargs:
    :param tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', or 'zstd'.
    :param quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', 'float', or 'yes' used for
        lzw and deflate.
    """
    from osgeo import gdal, gdalconst

    cmdopt = large_image.tilesource.base._gdalParameters(**kwargs)
    cmd = ['gdal_translate', inputPath, outputPath] + cmdopt
    logger.info('Convert to geotiff: %r', cmd)
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

    :param inputPath: the path to the input file or base file of a set.
    :param outputPath: the path of the output file.
    :param tempPath: a temporary file in a temporary directory.
    :param lidata: data from a large_image tilesource including associated
        images.
    Optional parameters that can be specified in kwargs:
    :param tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'jp2k'.
    :param quality: a jpeg quality passed to vips.  0 is small, 100 is high
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
    pool = _get_thread_pool(memoryLimit=FrameMemoryEstimate, **kwargs)
    onlyFrame = int(kwargs.get('onlyFrame')) if str(kwargs.get('onlyFrame')).isdigit() else None
    frame = 0
    # Process each image separately to pyramidize it
    for page in range(pages):
        subInputPath = inputPath + '[page=%d]' % page
        subImage = pyvips.Image.new_from_file(subInputPath)
        imageSizes.append((subImage.width, subImage.height, subInputPath, page))
        if subImage.width != width or subImage.height != height:
            if subImage.width * subImage.height <= width * height:
                continue
            logger.info('Bigger image found (was %dx%d, now %dx%d)',
                        width, height, subImage.width, subImage.height)
            for path in outputList:
                os.unlink(path)
            width = subImage.width
            height = subImage.height
        frame += 1
        if onlyFrame is not None and onlyFrame + 1 != frame:
            continue
        subOutputPath = tempPath + '-%d-%s.tiff' % (
            page + 1, time.strftime('%Y%m%d-%H%M%S'))
        _pool_add(tasks, (pool.submit(
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
                if not _use_associated_image(key, **kwargs):
                    continue
                savePath = tempPath + '-%s-%s.tiff' % (key, time.strftime('%Y%m%d-%H%M%S'))
                _pool_add(tasks, (pool.submit(
                    _convert_via_vips, subInputPath, savePath, tempPath, False), ))
                extraImages[key] = savePath
    _drain_pool(pool, tasks)
    _output_tiff(outputList, outputPath, tempPath, lidata, extraImages, **kwargs)


def _generate_tiff(inputPath, outputPath, tempPath, lidata, **kwargs):
    """
    Take a source input file, readable by vips, and output a pyramidal tiff
    file.

    :param inputPath: the path to the input file or base file of a set.
    :param outputPath: the path of the output file.
    :param tempPath: a temporary file in a temporary directory.
    :param lidata: data from a large_image tilesource including associated
        images.
    Optional parameters that can be specified in kwargs:
    :param tileSize: the horizontal and vertical tile size.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'jp2k'.
    :param quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    """
    _import_pyvips()
    subOutputPath = tempPath + '-%s.tiff' % (time.strftime('%Y%m%d-%H%M%S'))
    _convert_via_vips(inputPath, subOutputPath, tempPath, **kwargs)
    _output_tiff([subOutputPath], outputPath, tempPath, lidata, **kwargs)


def _convert_via_vips(inputPathOrBuffer, outputPath, tempPath, forTiled=True,
                      status=None, **kwargs):
    """
    Convert a file, buffer, or vips image to a tiff file.  This is equivalent
    to a vips command line of
      vips tiffsave <input path> <output path>
    followed by the convert params in the form of --<key>[=<value>] where no
    value needs to be specified if they are True.

    :param inputPathOrBuffer: a file path, bytes object, or vips image.
    :param outputPath: the name of the file to save.
    :param tempPath: a directory where temporary files may be stored.  vips
        also stores files in TMPDIR
    :param forTiled: True if the output should be tiled, false if not.
    :param status: an optional additional string to add to log messages.
    :param kwargs: addition arguments that get passed to _vipsParameters
        and _convert_to_jp2k.
    """
    _import_pyvips()
    convertParams = large_image.tilesource.base._vipsParameters(forTiled, **kwargs)
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
    logger.info('Input: %s, Output: %s, Options: %r%s',
                source, outputPath, convertParams, status)
    image = image.autorot()
    adjusted = format_hook('modify_vips_image_before_output', image, convertParams, **kwargs)
    if adjusted is False:
        return
    elif adjusted:
        image = adjusted
    if (convertParams['compression'] not in {'jpeg'} or
            image.interpretation != pyvips.Interpretation.SCRGB):
        # jp2k compression supports more than 8-bits per sample, but the
        # decompressor claims this is unsupported.
        image = large_image.tilesource.base._vipsCast(
            image,
            convertParams['compression'] in {'webp', 'jpeg'} or
            kwargs.get('compression') in {'jp2k'})
    # TODO: revisit the TMPDIR override; this is not thread safe
    # oldtmpdir = os.environ.get('TMPDIR')
    # os.environ['TMPDIR'] = os.path.dirname(tempPath)
    # try:
    #     image.write_to_file(outputPath, **convertParams)
    # finally:
    #     if oldtmpdir is not None:
    #         os.environ['TMPDIR'] = oldtmpdir
    #     else:
    #         del os.environ['TMPDIR']
    image.write_to_file(outputPath, **convertParams)
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


def _concurrency_to_value(_concurrency=None, **kwargs):
    """
    Convert the _concurrency value to a number of cpus.

    :param _concurrency: a positive value for a set number of cpus.  <= 0 for
        the number of logical cpus less that amount.  None is the same as 0.
    :returns: the number of cpus.
    """
    _concurrency = int(_concurrency) if str(_concurrency).isdigit() else 0
    if _concurrency > 0:
        return _concurrency
    return max(1, psutil.cpu_count(logical=True) + _concurrency)


def _get_thread_pool(memoryLimit=None, **kwargs):
    """
    Allocate a thread pool based on the specific concurrency.

    :param memoryLimit: if not None, limit the concurrency to no more than one
        process per memoryLimit bytes of total memory.
    """
    concurrency = _concurrency_to_value(**kwargs)
    if memoryLimit:
        concurrency = min(concurrency, psutil.virtual_memory().total // memoryLimit)
    concurrency = max(1, concurrency)
    return concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)


def _pool_add(tasks, newtask):
    """
    Add a new task to a pool, then drain any finished tasks at the start of the
    pool.

    :param tasks: a list contiaining either lists or tuples, the last element
        of which is a task submitted to the pool.  Altered.
    :param newtask: a list or tuple to add to the pool.
    """
    tasks.append(newtask)
    while len(tasks):
        try:
            tasks[0][-1].result(0)
        except concurrent.futures.TimeoutError:
            break
        tasks.pop(0)


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
                ifd['tags'][tifftools.Tag.TileWidth.value]['data'][0],
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


def _convert_large_image_tile(tilelock, strips, tile):
    """
    Add a single tile to a list of strips for a vips image so that they can be
    composited together.

    :param tilelock: a lock for thread safety.
    :param strips: an array of strips to adds to the final vips image.
    :param tile: a tileIterator tile.
    """
    data = tile['tile']
    if data.dtype.char not in large_image.constants.dtypeToGValue:
        data = data.astype('d')
    vimg = pyvips.Image.new_from_memory(
        numpy.ascontiguousarray(data).data,
        data.shape[1], data.shape[0], data.shape[2],
        large_image.constants.dtypeToGValue[data.dtype.char])
    vimgTemp = pyvips.Image.new_temp_file('%s.v')
    vimg.write(vimgTemp)
    vimg = vimgTemp
    x = tile['x']
    ty = tile['tile_position']['level_y']
    with tilelock:
        while len(strips) <= ty:
            strips.append(None)
        if strips[ty] is None:
            strips[ty] = vimg
            if not x:
                return
        if vimg.bands > strips[ty].bands:
            vimg = vimg[:strips[ty].bands]
        elif strips[ty].bands > vimg.bands:
            strips[ty] = strips[ty][:vimg.bands]
        strips[ty] = strips[ty].insert(vimg, x, 0, expand=True)


def _convert_large_image_frame(frame, numFrames, ts, frameOutputPath, tempPath, **kwargs):
    """
    Convert a single frame from a large_image source.  This parallelizes tile
    reads.  Once all tiles are converted to a composited vips image, a tiff
    file is generated.

    :param frame: the 0-based frame number.
    :param numFrames: the total number of frames; used for logging.
    :param ts: the open tile source.
    :param frameOutputPath: the destination name for the tiff file.
    :param tempPath: a temporary file in a temporary directory.
    """
    # The iterator tile size is a balance between memory use and fewer calls
    # and file handles.
    _iterTileSize = 4096
    logger.info('Processing frame %d/%d', frame + 1, numFrames)
    strips = []
    pool = _get_thread_pool(**kwargs)
    tasks = []
    tilelock = threading.Lock()
    for tile in ts.tileIterator(tile_size=dict(width=_iterTileSize), frame=frame):
        _pool_add(tasks, (pool.submit(_convert_large_image_tile, tilelock, strips, tile), ))
    _drain_pool(pool, tasks)
    img = strips[0]
    for stripidx in range(1, len(strips)):
        img = img.insert(strips[stripidx], 0, stripidx * _iterTileSize, expand=True)
    _convert_via_vips(
        img, frameOutputPath, tempPath, status='%d/%d' % (frame + 1, numFrames), **kwargs)


def _convert_large_image(inputPath, outputPath, tempPath, lidata, **kwargs):
    """
    Take a large_image source and convert it by resaving each tiles image with
    vips.

    :param inputPath: the path to the input file or base file of a set.
    :param outputPath: the path of the output file.
    :param tempPath: a temporary file in a temporary directory.
    :param lidata: data from a large_image tilesource including associated
        images.
    """
    ts = lidata['tilesource']
    numFrames = len(lidata['metadata'].get('frames', [0]))
    outputList = []
    tasks = []
    pool = _get_thread_pool(memoryLimit=FrameMemoryEstimate, **kwargs)
    startFrame = 0
    endFrame = numFrames
    if kwargs.get('onlyFrame') is not None and str(kwargs.get('onlyFrame')):
        startFrame = int(kwargs.get('onlyFrame'))
        endFrame = startFrame + 1
    for frame in range(startFrame, endFrame):
        frameOutputPath = tempPath + '-%d-%s.tiff' % (
            frame + 1, time.strftime('%Y%m%d-%H%M%S'))
        _pool_add(tasks, (pool.submit(
            _convert_large_image_frame, frame, numFrames, ts, frameOutputPath,
            tempPath, **kwargs), ))
        outputList.append(frameOutputPath)
    _drain_pool(pool, tasks)
    _output_tiff(outputList, outputPath, tempPath, lidata, **kwargs)


def _output_tiff(inputs, outputPath, tempPath, lidata, extraImages=None, **kwargs):
    """
    Given a list of input tiffs and data as parsed by _data_from_large_image,
    generate an output tiff file with the associated images, correct scale, and
    other metadata.

    :param inputs: a list of pyramidal input files.
    :param outputPath: the final destination.
    :param tempPath: a temporary file in a temporary directory.
    :param lidata: large_image data including metadata and associated images.
    :param extraImages: an optional dictionary of keys and paths to add as
        extra associated images.
    """
    logger.debug('Reading %s', inputs[0])
    info = tifftools.read_tiff(inputs[0])
    ifdIndices = [0]
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
            logger.debug('Reading %s', inputPath)
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
            ifdIndices.append(len(info['ifds']))
            if kwargs.get('subifds') is not False:
                nextInfo['ifds'][0]['tags'][tifftools.Tag.SubIFD.value] = {
                    'ifds': nextInfo['ifds'][1:]
                }
                info['ifds'].append(nextInfo['ifds'][0])
            else:
                info['ifds'].extend(nextInfo['ifds'])
    ifdIndices.append(len(info['ifds']))
    assocList = []
    if lidata:
        assocList += list(lidata['images'].items())
    if extraImages:
        assocList += list(extraImages.items())
    for key, assocPath in assocList:
        assocInfo = tifftools.read_tiff(assocPath)
        assocInfo['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value] = {
            'data': key,
            'datatype': tifftools.Datatype.ASCII,
        }
        info['ifds'] += assocInfo['ifds']
    if format_hook('modify_tiff_before_write', info, ifdIndices, tempPath,
                   lidata, **kwargs) is False:
        return
    logger.debug('Writing %s', outputPath)
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

    if pyvips is None:
        import pyvips


def _is_eightbit(path, tiffinfo=None):
    """
    Check if a path has an unsigned 8-bit per sample data size.  If any known
    channel is otherwise or this is unknown, this returns False.

    :param path: The path to the file
    :param tiffinfo: data extracted from tifftools.read_tiff(path).
    :returns: True if known to be 8 bits per sample.
    """
    if not tiffinfo:
        return False
    try:
        if (tifftools.Tag.SampleFormat.value in tiffinfo['ifds'][0]['tags'] and
                not all(val == tifftools.constants.SampleFormat.uint for val in
                        tiffinfo['ifds'][0]['tags'][tifftools.Tag.SampleFormat.value]['data'])):
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

    :param path: The path to the file
    :param tiffinfo: data extracted from tifftools.read_tiff(path).
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

    :param path: The path to the file
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
    """
    Fallback serializier for json.  This serializes datetime objects to iso
    format.

    :param obj: an object to serialize.
    :returns: a serialized string.
    """
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


def format_hook(funcname, *args, **kwargs):
    """
    Call a function specific to a file format.

    :param funcname: name of the function.
    :param args: parameters to pass to the function.
    :param kwargs: parameters to pass to the function.
    :returns: dependent on the function.  False to indicate no further
        processing should be done.
    """
    format = str(kwargs.get('format')).lower()
    func = getattr(FormatModules.get(format, {}), funcname, None)
    if callable(func):
        return func(*args, **kwargs)


def convert(inputPath, outputPath=None, **kwargs):  # noqa: C901
    """
    Take a source input file and output a pyramidal tiff file.

    :param inputPath: the path to the input file or base file of a set.
    :param outputPath: the path of the output file.

    Optional parameters that can be specified in kwargs:

    :param tileSize: the horizontal and vertical tile size.
    :param format: one of 'tiff' or 'aperio'.  Default is 'tiff'.
    :param onlyFrame: None for all frames or the 0-based frame number to just
        convert a single frame of the source.
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits',
        'zstd', or 'none'.
    :param quality: a jpeg or webp quality passed to vips.  0 is small, 100 is
        high quality.  90 or above is recommended.  For webp, 0 is lossless.
    :param level: compression level for zstd, 1-22 (default is 10) and deflate,
        1-9.
    :param predictor: one of 'none', 'horizontal', 'float', or 'yes' used for
        lzw and deflate.  Default is horizontal for non-geospatial data and yes
        for geospatial.
    :param psnr: psnr value for jp2k, higher results in large files.  0 is
        lossless.
    :param cr: jp2k compression ratio.  1 is lossless, 100 will try to make
        a file 1% the size of the original, etc.
    :param subifds: if True (the default), when creating a multi-frame file,
        store lower resolution tiles in sub-ifds.  If False, store all data in
        primary ifds.
    :param overwrite: if not True, throw an exception if the output path
        already exists.

    Additional optional parameters:

    :param geospatial: if not None, a boolean indicating if this file is
        geospatial.  If not specified or None, this will be checked.
    :param _concurrency: the number of cpus to use during conversion.  None to
        use the logical cpu count.

    :returns: outputPath if successful
    """
    if kwargs.get('_concurrency'):
        os.environ['VIPS_CONCURRENCY'] = str(_concurrency_to_value(**kwargs))
    geospatial = kwargs.get('geospatial')
    if geospatial is None:
        geospatial = is_geospatial(inputPath)
        logger.debug('Is file geospatial: %r', geospatial)
    suffix = format_hook('adjust_params', geospatial, kwargs, **kwargs)
    if suffix is False:
        return
    suffix = suffix or ('.tiff' if not geospatial else '.geo.tiff')
    if not outputPath:
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
    eightbit = _is_eightbit(inputPath, tiffinfo)
    if not kwargs.get('compression', None):
        kwargs = kwargs.copy()
        lossy = _is_lossy(inputPath, tiffinfo)
        logger.debug('Is file lossy: %r', lossy)
        logger.debug('Is file 8 bits per samples: %r', eightbit)
        kwargs['_compression'] = None
        kwargs['compression'] = 'jpeg' if lossy and eightbit else 'lzw'
    if geospatial:
        _generate_geotiff(inputPath, outputPath, eightbit=eightbit or None, **kwargs)
    else:
        with TemporaryDirectory() as tempDir:
            tempPath = os.path.join(tempDir, os.path.basename(outputPath))
            lidata = _data_from_large_image(inputPath, tempPath, **kwargs)
            logger.log(logging.DEBUG - 1, 'large_image information for %s: %r',
                       inputPath, lidata)
            if not is_vips(inputPath) and lidata:
                _convert_large_image(inputPath, outputPath, tempPath, lidata, **kwargs)
            elif _is_multiframe(inputPath):
                _generate_multiframe_tiff(inputPath, outputPath, tempPath, lidata, **kwargs)
            else:
                try:
                    _generate_tiff(inputPath, outputPath, tempPath, lidata, **kwargs)
                except Exception:
                    if lidata:
                        _convert_large_image(inputPath, outputPath, tempPath, lidata, **kwargs)
    return outputPath


def is_geospatial(path):
    """
    Check if a path is likely to be a geospatial file.

    :param path: The path to the file
    :returns: True if geospatial.
    """
    try:
        from osgeo import gdal, gdalconst
    except ImportError:
        logger.warning('Cannot import GDAL.')
        return False
    gdal.UseExceptions()
    try:
        ds = gdal.Open(path, gdalconst.GA_ReadOnly)
    except Exception:
        return False
    if ds and (
            (ds.GetGCPs() and ds.GetGCPProjection()) or
            ds.GetProjection() or
            ds.GetDriver().ShortName in {'NITF', 'netCDF'}):
        return True
    return False


def is_vips(path):
    """
    Check if a path is readable by vips.

    :param path: The path to the file
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
