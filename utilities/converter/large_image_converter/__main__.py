import argparse
import logging
import os
import sys
import time

import large_image_converter


logger = logging.getLogger('large-image-converter')


def get_parser():
    parser = argparse.ArgumentParser(description="""
Convert files for use with Large Image.
Output files are written as tiled tiff files.  For geospatial files, these
conform to the cloud-optimized geospatial tiff format (COG).  For
non-geospatial, the output image will be either 8- or 16-bits per sample per
channel.  Some compression formats are always 8-bits per sample (webp, jpeg),
even if that format could support more and the original image is higher bit
depth.
""")
    parser.add_argument(
        '--version', action='version',
        version=large_image_converter.__version__, help='Report version')
    parser.add_argument(
        '--verbose', '-v', action='count', default=0, help='Increase verbosity')
    parser.add_argument(
        '--silent', '-s', action='count', default=0, help='Decrease verbosity')
    parser.add_argument(
        'source', help='Path to source image')
    parser.add_argument(
        'dest', nargs='?', help='Output path')
    parser.add_argument(
        '--overwrite', '-w', '-y', action='store_true',
        help='Overwrite an existing output file')
    parser.add_argument(
        '--tile', '--tile-size', '--tilesize', '--tileSize', '-t', type=int,
        help='Tile size.  Default is 256.', dest='tileSize')
    parser.add_argument(
        '--no-subifds', action='store_false', dest='subifds', default=None,
        help='When writing multiframe files, do not use subifds.')
    parser.add_argument(
        '--subifds', action='store_true', dest='subifds', default=None,
        help='When writing multiframe files, use subifds.')
    parser.add_argument(
        '--frame', dest='onlyFrame', default=None, type=int,
        help='When handling a multiframe file, only output a single frame.  '
        'This is the zero-based frame number.')
    parser.add_argument(
        '--format', default=None,
        choices=['tiff', 'aperio'],
        help='Output format.  The default is a standardized pyramidal tiff or '
        'COG geotiff.  Other formats may not be available for all input '
        'options and will change some defaults.  '
        'Aperio (svs) defaults to no-subifds.  If there is no label image, a '
        'cropped nearly square thumbnail is used in its place if the source '
        'image can be read by any of the known tile sources.')
    parser.add_argument(
        '--compression', '-c',
        choices=[
            '', 'jpeg', 'deflate', 'zip', 'lzw', 'zstd', 'packbits', 'jbig',
            'lzma', 'webp', 'jp2k', 'none',
        ],
        help='Internal compression.  Default will use jpeg if the source '
        'appears to be lossy or lzw if lossless.  lzw is the most compatible '
        'lossless mode.  jpeg is the most compatible lossy mode.  jbig and '
        'lzma may not be available.  jp2k will first write the file with no '
        'compression and then rewrite it with jp2k the specified psnr or '
        'compression ratio.')
    parser.add_argument(
        '--quality', '-q', type=int,
        help='JPEG or webp compression quality.  For webp, specify 0 for '
        'lossless.  Default is 90.')
    parser.add_argument(
        '--level', '-l', type=int,
        help='General compression level.  Used for deflate (zip) (1-9), zstd '
        '(1-22), and some others.')
    parser.add_argument(
        '--predictor', '-p', choices=['', 'none', 'horizontal', 'float', 'yes'],
        help='Predictor for some compressions.  Default is horizontal for '
        'non-geospatial data and yes for geospatial.')
    parser.add_argument(
        '--psnr', type=int,
        help='JP2K peak signal to noise ratio.  0 for lossless.')
    parser.add_argument(
        '--cr', type=int, help='JP2K compression ratio.  1 for lossless.')
    parser.add_argument(
        '--concurrency', '-j', type=int, dest='_concurrency',
        help='Maximum processor concurrency.  Some conversion tasks can use '
        'multiple processors.  By default, all logical processors are used.  '
        'This is a recommendation and is not strict.')
    parser.add_argument(
        '--stats', action='store_true', dest='_stats',
        help='Add conversion stats (time and size) to the ImageDescription of '
        'the output file.  This involves writing the file an extra time; the '
        'stats do not include the extra write.')
    parser.add_argument(
        '--stats-full', '--full-stats',
        action='store_const', const='full', dest='_stats',
        help='Add conversion stats, including noise metrics (PSNR, etc.) to '
        'the output file.  This takes more time and temporary disk space.')
    return parser


def compute_error_metrics(original, altered, results, converterOpts=None):
    """
    Compute the amount of error introduced via conversion compared to
    conversion using a lossless method.  Note that this is not compared to the
    original, as we may not be able to read that in an efficient way.  This is
    a very time-consuming way to compute error metrics, since it first
    reprocesses the input file to a lossless format, then steps through each
    tile and computes RSME and SSIM errors per tile, producing a weighted-by-
    number-of-pixels of each of these.  The RSME is used to compute a PSNR
    value.

    :param original: the original file path.
    :param altered: the path of compressed file to compare.
    :param results: a dictionary to store results.  Modified.
    :param converterOpts: an optional dictionary of parameters used for the
        original conversion.  Only parameters that would affect the selected
        pixels are used.
    """
    import math
    from tempfile import TemporaryDirectory
    import skimage.metrics
    import numpy
    import large_image_source_tiff

    lastlog = 0
    with TemporaryDirectory() as tempDir:
        # TODO: check if the original is geospatial; if so appropriate options
        tempPath = os.path.join(tempDir, os.path.basename(original) + '.tiff')
        orig = large_image_converter.convert(original, tempPath, compression='lzw')
        tsOrig = large_image_source_tiff.open(orig)
        numFrames = len(tsOrig.getMetadata().get('frames', [0]))
        tsAlt = large_image_source_tiff.open(altered)
        mse = 0
        ssim = 0
        ssim_count = 0
        maxval = 0
        maxdiff = 0
        sum = 0
        count = 0
        tileSize = 2048
        for frame in range(numFrames):
            tiAlt = tsAlt.tileIterator(tile_size=dict(width=tileSize), frame=frame)
            for tileOrig in tsOrig.tileIterator(tile_size=dict(width=tileSize), frame=frame):
                tileAlt = next(tiAlt)
                do = tileOrig['tile']
                da = tileAlt['tile']
                if do.dtype != da.dtype and da.dtype == numpy.uint8:
                    da = da.astype(int) * 257
                do = do.astype(int)
                da = da.astype(int)
                maxval = max(maxval, do.max(), da.max())
                if do.shape[2] > da.shape[2]:
                    do = do[:, :, :da.shape[2]]
                if da.shape[2] > do.shape[2]:
                    da = da[:, :, :do.shape[2]]
                diff = numpy.absolute(do - da)
                maxdiff = max(maxdiff, diff.max())
                sum += diff.sum()
                count += diff.size
                last_mse = numpy.mean(diff ** 2)
                mse += last_mse * diff.size
                last_ssim = 0
                try:
                    last_ssim = skimage.metrics.structural_similarity(
                        do.astype(float), da.astype(float),
                        data_range=255 if tileOrig['tile'].dtype == numpy.uint8 else 65535,
                        gaussian_weights=True, sigma=1.5, use_sample_covariance=False,
                        multichannel=len(do.shape) > 2)
                    ssim += last_ssim * diff.size
                    ssim_count += diff.size
                except ValueError:
                    pass
                if time.time() - lastlog >= 10 and ssim_count:
                    logger.debug(
                        'Calculating error (%d/%d): rmse %4.2f ssim %6.4f  '
                        'last rmse %4.2f ssim %6.4f' % (
                            tileOrig['tile_position']['position'] + 1 +
                            tileOrig['iterator_range']['position'] * frame,
                            tileOrig['iterator_range']['position'] * numFrames,
                            (mse / count) ** 0.5, ssim / ssim_count,
                            last_mse ** 0.5, last_ssim))
                    lastlog = time.time()
        results['maximum_error'] = maxdiff
        results['average_error'] = sum / count
        results['rmse'] = (mse / count) ** 0.5
        results['psnr'] = 10 * math.log10(
            maxval ** 2 / (mse / count)) if mse else None
        if ssim_count:
            results['ssim'] = ssim / ssim_count
            logger.debug('Calculated error: rmse %4.2f psnr %3.1f ssim %6.4f' % (
                results['rmse'], results['psnr'] or 0, results['ssim']))


def main(args=sys.argv[1:]):
    parser = get_parser()
    opts = parser.parse_args(args=args)
    logger = logging.getLogger('large-image-converter')
    if not len(logger.handlers):
        logger.addHandler(logging.StreamHandler(sys.stderr))
    logger.setLevel(max(1, logging.WARNING - (opts.verbose - opts.silent) * 10))
    try:
        import large_image

        li_logger = large_image.config.getConfig('logger')
        li_logger.setLevel(max(1, logging.CRITICAL - (opts.verbose - opts.silent) * 10))
    except ImportError:
        pass
    logger.debug('Command line options: %r' % opts)
    if not os.path.isfile(opts.source):
        logger.error('Source is not a file (%s)', opts.source)
        return 1
    if opts.compression == 'zip':
        opts.compression = 'deflate'
    converterOpts = {
        k: v for k, v in vars(opts).items()
        if k not in {'source', 'dest', 'verbose', 'silent'} and v is not None}
    start_time = time.time()
    dest = large_image_converter.convert(opts.source, opts.dest, **converterOpts)
    end_time = time.time()
    if not os.path.isfile(dest):
        logger.error('Failed to generate file')
        return 1
    logger.info('Created %s, %d bytes, %3.1f s', dest, os.path.getsize(dest), end_time - start_time)
    if opts._stats:
        import json
        import tifftools.commands

        info = tifftools.read_tiff(dest)
        try:
            desc = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
        except Exception:
            logger.debug('Cannot generate statistics.')
            return
        desc['large_image_converter']['conversion_stats'] = {
            'time': end_time - start_time,
            'filesize': os.path.getsize(dest),
            'original_filesize': os.path.getsize(opts.source),
            'compression_ratio':
                desc['large_image_converter'].get('frames', 1) *
                sum(info['ifds'][0]['tags'][tifftools.Tag.BitsPerSample.value]['data']) / 8 *
                info['ifds'][0]['tags'][tifftools.Tag.ImageWidth.value]['data'][0] *
                info['ifds'][0]['tags'][tifftools.Tag.ImageLength.value]['data'][0] /
                os.path.getsize(dest),
        }
        if opts._stats == 'full' and opts.compression not in {
                'deflate', 'zip', 'lzw', 'zstd', 'packbits', 'none'}:
            compute_error_metrics(
                opts.source, dest, desc['large_image_converter']['conversion_stats'],
                converterOpts)
        tifftools.commands.tiff_set(dest, overwrite=True, setlist=[(
            'ImageDescription', json.dumps(
                desc, separators=(',', ':'), sort_keys=True,
                default=large_image_converter.json_serial))])


if __name__ == '__main__':
    sys.exit(main())
