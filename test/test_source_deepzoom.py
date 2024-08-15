import os

import large_image_source_deepzoom
import pytest
import pyvips

from . import utilities
from .datastore import datastore


@pytest.fixture
def vipsToDzi(tmpdir):
    def convert(imagePath, options=None):
        if options is None:
            options = {}
        image = pyvips.Image.new_from_file(imagePath)
        outputPath = os.path.join(tmpdir, 'out')
        image.dzsave(outputPath, **options)
        outputPath += '.dzi'
        return outputPath
    return convert


@pytest.mark.parametrize('dzoptions', [
    {},
    {'depth': 'onetile'},
    {'suffix': '.png'},
    {'suffix': '.jpeg'},
    {'tile_width': 192, 'tile_height': 192, 'overlap': 6},
])
def testTilesFromDeepzoom(vipsToDzi, dzoptions):
    imagePath = datastore.fetch('G10-3_pelvis_crop-powers-of-3.tif')
    dziPath = vipsToDzi(imagePath, options=dzoptions)
    source = large_image_source_deepzoom.open(dziPath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['sizeX'] == 3000
    assert tileMetadata['sizeY'] == 5000
    utilities.checkTilesZXY(source, tileMetadata)


def testInternalMetadata(vipsToDzi):
    imagePath = datastore.fetch('G10-3_pelvis_crop-powers-of-3.tif')
    dziPath = vipsToDzi(imagePath)
    source = large_image_source_deepzoom.open(dziPath)
    metadata = source.getInternalMetadata()
    assert 'baselevel' in metadata


def testCanRead(vipsToDzi):
    imagePath = datastore.fetch('G10-3_pelvis_crop-powers-of-3.tif')
    dziPath = vipsToDzi(imagePath)
    assert large_image_source_deepzoom.canRead(imagePath) is False
    assert large_image_source_deepzoom.canRead(dziPath) is True
