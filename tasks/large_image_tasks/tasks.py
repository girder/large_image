import os
import time

from girder_worker.app import app
from girder_worker.utils import girder_job


@girder_job(title='Create a pyramidal tiff using vips', type='large_image_tiff')
@app.task(bind=True)
def create_tiff(self, inputFile, outputName=None, outputDir=None, quality=90, tileSize=256):
    # Because of its use of gobject, pyvips should be invoked without concurrency
    os.environ['VIPS_CONCURRENCY'] = '1'
    import pyvips

    inputPath = os.path.abspath(os.path.expanduser(inputFile))
    inputName = os.path.basename(inputPath)
    if not outputName:
        outputName = (os.path.splitext(inputName)[0] + '.' +
                      time.strftime('%Y%m%d-%H%M%S') + '.tiff')
    renameOutput = outputName
    if not outputName.endswith('.tiff'):
        outputName += '.tiff'
    if not outputDir:
        outputDir = os.path.dirname(inputPath)
    outputPath = os.path.join(outputDir, outputName)
    # This is equivalent to a vips command line of
    #  vips tiffsave <input path> <output path>
    # followed by the convert params in the form of --<key>[=<value>] where no
    # value needs to be specified if they are True.
    convertParams = {
        'compression': 'jpeg',
        'Q': quality,
        'tile': True,
        'tile_width': tileSize,
        'tile_height': tileSize,
        'pyramid': True,
        'bigtiff': True
    }
    print('Input: %s\nOutput: %s\nOptions: %r' % (inputPath, outputPath, convertParams))
    pyvips.Image.new_from_file(inputPath).write_to_file(outputPath, **convertParams)
    # vips always seems to raise its own exception, so this may be needless
    if not os.path.exists(outputPath):
        raise Exception('VIPS command failed to produce output')
    if renameOutput != outputName:
        import shutil

        renamePath = os.path.join(outputDir, renameOutput)
        shutil.move(outputPath, renamePath)
        outputPath = renamePath
    print('Created a file of size %d' % os.path.getsize(outputPath))
    return outputPath
