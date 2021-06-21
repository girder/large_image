# An example to get a tile source, save a thumbnail, and iterate through the
# tiles at a specific magnification, reporting the average color of each tile.

import argparse

import numpy

import large_image


def sum_squares(imagePath, magnification=None, **kwargs):
    """
    Print the sum-of-squares of each color channel for a tiled image file.

    :param imagePath: path of the file to analyze.
    :param magnification: optional magnification to use for the analysis.
    """
    source = large_image.getTileSource(imagePath)

    tileSumSquares = []
    # iterate through the tiles at a particular magnification:
    for tile in source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            scale={'magnification': magnification},
            resample=True, **kwargs):
        # The tile image data is in tile['tile'] and is a numpy
        # multi-dimensional array
        data = tile['tile']
        # trim off any overlap so we don't include it in our calculations.
        data = data[
            tile['tile_overlap']['top']:
                data.shape[0] - tile['tile_overlap']['bottom'],
            tile['tile_overlap']['left']:
                data.shape[1] - tile['tile_overlap']['right'],
            :]
        sumsq = numpy.sum(data**2, axis=(0, 1))
        tileSumSquares.append(sumsq)
        print('x: %d  y: %d  w: %d  h: %d  mag: %g  sums: %d %d %d' % (
            tile['x'], tile['y'], tile['width'], tile['height'],
            tile['magnification'], sumsq[0], sumsq[1], sumsq[2]))
    sumsq = numpy.sum(tileSumSquares, axis=0)
    print('Sum of squares: %d %d %d' % (sumsq[0], sumsq[1], sumsq[2]))
    return sumsq


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute the sum-of-squares of each color channel of a '
        'tiled image', add_help=False)
    parser.add_argument('--help', action='help',
                        help='show this help message and exit')
    parser.add_argument('path', metavar='image-path', type=str,
                        help='Path of the tiled image to examine')
    parser.add_argument('-m', '--magnification', dest='magnification',
                        type=float,
                        help='Magnification to use to examine the image')
    parser.add_argument('-w', '--width', dest='tile_width', type=int,
                        help='Tile width used to examine the image')
    parser.add_argument('-h', '--height', dest='tile_height', type=int,
                        help='Tile height used to examine the image')
    parser.add_argument(
        '-x', dest='overlap_x', type=int,
        help='Horizontal tile overlap used to examine the image')
    parser.add_argument(
        '-y', dest='overlap_y', type=int,
        help='Vertical tile overlap used to examine the image')
    parser.add_argument(
        '-e', dest='overlap_edges', action='store_true', default=False,
        help='Overlaped tiles start at the edge and are cropped.')
    args = parser.parse_args()
    kwargs = {}
    if args.tile_width or args.tile_height:
        kwargs['tile_size'] = {}
        if args.tile_width:
            kwargs['tile_size']['width'] = args.tile_width
        if args.tile_height:
            kwargs['tile_size']['height'] = args.tile_height
    if args.overlap_x or args.overlap_y:
        kwargs['tile_overlap'] = {'edges': args.overlap_edges}
        if args.overlap_x:
            kwargs['tile_overlap']['x'] = args.overlap_x
        if args.overlap_y:
            kwargs['tile_overlap']['y'] = args.overlap_y
    sum_squares(args.path, args.magnification, **kwargs)
