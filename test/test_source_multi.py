import os

import large_image_source_multi
import pytest

from . import utilities
from .datastore import datastore


@pytest.mark.parametrize('filename', [
    'multi1.yml',
    'multi2.yml',
    'multi3.yml',
])
def testTilesFromMulti(filename):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', filename)
    source = large_image_source_multi.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 64
    assert tileMetadata['tileHeight'] == 64
    assert tileMetadata['sizeX'] == 180
    assert tileMetadata['sizeY'] == 180
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 8

    utilities.checkTilesZXY(source, tileMetadata)


def testTilesFromMultiComposite():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'multi_composite.yml')
    source = large_image_source_multi.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 64
    assert tileMetadata['tileHeight'] == 64
    assert tileMetadata['sizeX'] == 360
    assert tileMetadata['sizeY'] == 360
    assert tileMetadata['levels'] == 4
    assert len(tileMetadata['frames']) == 2

    utilities.checkTilesZXY(source, tileMetadata)


def testTilesFromMultiSimpleScaling():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'multi_simple_scaling.yml')
    source = large_image_source_multi.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 2048
    assert tileMetadata['sizeY'] == 1540
    assert tileMetadata['levels'] == 4
    assert len(tileMetadata['frames']) == 8

    for frame in range(len(tileMetadata['frames'])):
        utilities.checkTilesZXY(source, tileMetadata, tileParams={'frame': frame})


def testTilesFromMultiMultiSource():
    imagePath = datastore.fetch('multi_source.yml')
    source = large_image_source_multi.open(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 55988
    assert tileMetadata['sizeY'] == 16256
    assert tileMetadata['levels'] == 9
    assert len(tileMetadata['frames']) == 300

    utilities.checkTilesZXY(source, tileMetadata)
    utilities.checkTilesZXY(source, tileMetadata, tileParams={'frame': 50})


def testInternalMetadata():
    imagePath = datastore.fetch('multi_source.yml')
    source = large_image_source_multi.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'frames' in metadata


def testAssociatedImages():
    imagePath = datastore.fetch('multi_source.yml')
    source = large_image_source_multi.open(imagePath)
    assert 'label' in source.getAssociatedImagesList()
    image, mimeType = source.getAssociatedImage('label')
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader


def testCanRead():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'multi_composite.yml')
    assert large_image_source_multi.canRead(imagePath) is True
    imagePath2 = os.path.join(testDir, 'test_files', 'test_orient1.tif')
    assert large_image_source_multi.canRead(imagePath2) is False
