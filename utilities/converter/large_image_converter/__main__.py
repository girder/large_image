import argparse
import logging
import os
import sys
import time

import large_image_converter


def get_parser():
    parser = argparse.ArgumentParser(description='Large Image image converter')
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
        '--quality', '-q', default=90, type=int,
        help='JPEG or webp compression quality.  For webp, specify 0 for '
        'lossless.')
    parser.add_argument(
        '--level', '-l', type=int,
        help='General compression level.  Used for deflate (zip), zstd, and '
        'some others.')
    parser.add_argument(
        '--predictor', '-p', choices=['', 'none', 'horizontal', 'float', 'yes'],
        help='Predictor for some compressions.  Default is horizontal for '
        'non-geospatial data and yes for geospatial.')
    parser.add_argument(
        '--psnr', type=int,
        help='JP2K peak signal to noise ratio.  0 for lossless')
    parser.add_argument(
        '--cr', type=int, help='JP2K compression ratio.  1 for lossless')
    parser.add_argument(
        '--tile', '-t', type=int, default=256, help='Tile size',
        dest='tileSize')
    parser.add_argument(
        '--overwrite', '-w', action='store_true',
        help='Overwrite an existing output file')
    return parser


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


if __name__ == '__main__':
    sys.exit(main())
