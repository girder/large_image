# An example to get a tile source, save a thumbnail, and iterate through the
# tiles at a specific magnification, reporting the average color of each tile.

import argparse
import numpy

import large_image

# Explicitly set the caching method before we request any data
large_image.config.setConfig('cache_backend', 'python')


def average_color(imagePath, magnification=None):
    """
    Print the average color for a tiled image file.

    :param imagePath: path of the file to analyze.
    :param magnification: optional magnification to use for the analysis.
    """
    source = large_image.getTileSource(imagePath)
    # get a thumbnail no larger than 1024x1024 pixels
    thumbnail, mimeType = source.getThumbnail(
        width=1024, height=1024, encoding='JPEG')
    print('Made a thumbnail of type %s taking %d bytes' % (
        mimeType, len(thumbnail)))
    # We could save it, if we want to.
    # open('/tmp/thumbnail.jpg', 'wb').write(thumbnail)

    tileMeans = []
    tileWeights = []
    # iterate through the tiles at a particular magnification:
    for tile in source.tileIterator(
            format=large_image.tilesource.TILE_FORMAT_NUMPY,
            scale={'magnification': magnification},
            resample=True):
        # The tile image data is in tile['tile'] and is a numpy
        # multi-dimensional array
        mean = numpy.mean(tile['tile'], axis=(0, 1))
        tileMeans.append(mean)
        tileWeights.append(tile['width'] * tile['height'])
        print('x: %d  y: %d  w: %d  h: %d  mag: %g  color: %g %g %g' % (
            tile['x'], tile['y'], tile['width'], tile['height'],
            tile['magnification'], mean[0], mean[1], mean[2]))
    mean = numpy.average(tileMeans, axis=0, weights=tileWeights)
    print('Average color: %g %g %g' % (mean[0], mean[1], mean[2]))
    return mean


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute the mean color of a tiled image')
    parser.add_argument('path', metavar='image-path', type=str,
                        help='Path of the tiled image to examine')
    parser.add_argument('-m', '--magnification', dest='magnification',
                        type=float,
                        help='Magnification to use to examine the image')
    args = parser.parse_args()
    average_color(args.path, args.magnification)
