import logging
import os
import shutil
import sys
import time

from girder_worker.app import app
from girder_worker.utils import girder_job


@girder_job(title='Create a pyramidal tiff using vips', type='large_image_tiff')
@app.task(bind=True)
def create_tiff(self, inputFile, outputName=None, outputDir=None, quality=90,
                tileSize=256, **kwargs):
    """
    Take a source input file, readable by vips, and output a pyramidal tiff
    file.

    :params inputFile: the path to the input file or base file of a set.
    :params outputName: the name of the output file.  If None, the name is
        based on the input name and current date and time.  May be a full path.
    :params outputDir: the location to store the output.  If unspecified, the
        inputFile's directory is used.  If the outputName is a fully qualified
        path, this is ignored.
    :params quality: a jpeg quality passed to vips.  0 is small, 100 is high
        quality.  90 or above is recommended.
    :params tileSize: the horizontal and vertical tile size.
    Optional parameters that can be specified in kwargs:
    :param compression: one of 'jpeg', 'deflate' (zip), 'lzw', 'packbits', or
        'zstd'.
    :param level: compression level for zstd, 1-22 (default is 10).
    :param predictor: one of 'none', 'horizontal', or 'float' used for lzw and
        deflate.
    :param inputName: if no output name is specified, and this is specified,
        this is used as the basis of the output name instead of extracting the
        name from the inputFile path.
    """
    import large_image_converter

    logger = logging.getLogger('large-image-converter')
    if not len(logger.handlers):
        logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.setLevel(logging.INFO)

    inputPath = os.path.abspath(os.path.expanduser(inputFile))
    geospatial = large_image_converter.is_geospatial(inputPath)
    inputName = kwargs.get('inputName', os.path.basename(inputPath))
    suffix = '.tiff' if not geospatial else '.geo.tiff'
    if not outputName:
        outputName = os.path.splitext(inputName)[0] + suffix
        if outputName.endswith('.geo' + suffix):
            outputName = outputName[:len(outputName) - len(suffix) - 4] + suffix
        if outputName == inputName:
            outputName = (os.path.splitext(inputName)[0] + '.' +
                          time.strftime('%Y%m%d-%H%M%S') + suffix)
    renameOutput = outputName
    if not outputName.endswith(suffix):
        outputName += suffix
    if not outputDir:
        outputDir = os.path.dirname(inputPath)
    outputPath = os.path.join(outputDir, outputName)
    large_image_converter.convert(
        inputPath, outputPath, quality=quality, tileSize=tileSize, **kwargs)
    if not os.path.exists(outputPath):
        raise Exception('Conversion command failed to produce output')
    if renameOutput != outputName:
        renamePath = os.path.join(outputDir, renameOutput)
        shutil.move(outputPath, renamePath)
        outputPath = renamePath
    logger.info('Created a file of size %d' % os.path.getsize(outputPath))
    return outputPath
