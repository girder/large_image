import json
from xml.etree import ElementTree

import large_image_source_ometiff
import numpy as np

from large_image.constants import TILE_FORMAT_NUMPY
from large_image.tilesource import dictToEtree, etreeToDict

from . import utilities
from .datastore import datastore


def testTilesFromOMETiff():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 1024
    assert tileMetadata['sizeX'] == 2106
    assert tileMetadata['sizeY'] == 2016
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 3
    assert tileMetadata['frames'][1]['Frame'] == 1
    assert tileMetadata['frames'][1]['Index'] == 0
    assert tileMetadata['frames'][1]['IndexC'] == 1
    assert tileMetadata['IndexRange'] == {'IndexC': 3}
    utilities.checkTilesZXY(source, tileMetadata)


def testTilesFromOMETiffWithSubIFD():
    imagePath = datastore.fetch('sample.subifd.ome.tif')
    source = large_image_source_ometiff.open(imagePath, frame=1)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 2106
    assert tileMetadata['sizeY'] == 2016
    assert tileMetadata['levels'] == 5
    assert len(tileMetadata['frames']) == 3
    assert tileMetadata['frames'][1]['Frame'] == 1
    assert tileMetadata['frames'][1]['Index'] == 0
    assert tileMetadata['frames'][1]['IndexC'] == 1
    assert tileMetadata['IndexRange'] == {'IndexC': 3}
    utilities.checkTilesZXY(source, tileMetadata)


def testTilesFromStripOMETiff():
    imagePath = datastore.fetch('DDX58_AXL_EGFR_well2_XY01.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 1024
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 1024
    assert tileMetadata['sizeY'] == 1022
    assert tileMetadata['levels'] == 3
    assert len(tileMetadata['frames']) == 145
    assert tileMetadata['frames'][101]['Frame'] == 101
    assert tileMetadata['frames'][101]['Index'] == 20
    assert tileMetadata['frames'][101]['IndexC'] == 1
    assert tileMetadata['frames'][101]['IndexZ'] == 20
    assert tileMetadata['channels'] == ['Brightfield', 'CY3', 'A594', 'CY5', 'DAPI']
    assert tileMetadata['IndexRange'] == {'IndexC': 5, 'IndexZ': 29}
    utilities.checkTilesZXY(source, tileMetadata)


def testOMETiffAre16Bit():
    imagePath = datastore.fetch('DDX58_AXL_EGFR_well2_XY01.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    tile = next(source.tileIterator(format=TILE_FORMAT_NUMPY))['tile']
    assert tile.dtype == np.uint16
    assert tile[15][15][0] == 17852

    region, _ = source.getRegion(format=TILE_FORMAT_NUMPY)
    assert region.dtype == np.uint16
    assert region[300][300][0] == 17816


def testStyleAutoMinMax():
    imagePath = datastore.fetch('DDX58_AXL_EGFR_well2_XY01.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    sourceB = large_image_source_ometiff.open(
        imagePath, style={'min': 'auto', 'max': 'auto'})
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    imageB = imageB[:, :, :1]
    assert np.any(image != imageB)
    imageB = imageB.astype(np.uint16) * 257
    assert image.shape == imageB.shape
    assert image[128][128][0] < imageB[128][128][0]
    assert image[0][128][0] < imageB[0][128][0]
    assert image[240][128][0] < imageB[240][128][0]


def testStyleFrame():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'palette': ['#000000', '#0000ff'],
        }, {
            'palette': ['#000000', '#00ff00'],
        }]}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    sourceB = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'palette': ['#000000', '#0000ff'],
        }, {
            'frame': 1,
            'palette': ['#000000', '#00ff00'],
        }]}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    assert np.all(image == imageB)
    assert image.shape == imageB.shape
    sourceC = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'palette': ['#000000', '#0000ff'],
        }, {
            'frame': 2,
            'palette': ['#000000', '#00ff00'],
        }]}))
    imageC, _ = sourceC.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    assert np.any(image != imageC)
    assert image.shape == imageC.shape


def testStyleFrameDelta():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'palette': ['#000000', '#0000ff'],
        }, {
            'palette': ['#000000', '#00ff00'],
        }]}))
    image, _ = source.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    sourceB = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'palette': ['#000000', '#0000ff'],
        }, {
            'framedelta': 1,
            'palette': ['#000000', '#00ff00'],
        }]}))
    imageB, _ = sourceB.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=1)
    assert np.any(image != imageB)
    assert image.shape == imageB.shape
    sourceC = large_image_source_ometiff.open(
        imagePath, style=json.dumps({'bands': [{
            'framedelta': -1,
            'palette': ['#000000', '#0000ff'],
        }, {
            'palette': ['#000000', '#00ff00'],
        }]}))
    imageC, _ = sourceC.getRegion(
        output={'maxWidth': 256, 'maxHeight': 256}, format=TILE_FORMAT_NUMPY, frame=2)
    assert np.all(imageB == imageC)
    assert imageB.shape == imageC.shape


def testInternalMetadata():
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    metadata = source.getInternalMetadata()
    assert 'omeinfo' in metadata


def testXMLParsing():
    samples = [{
        'xml': """<?xml version='1.0' encoding='utf-8'?>
<OME xmlns="http://www.openmicroscopy.org/Schemas/OME/2016-06" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" UUID="urn:uuid:1ae9b229-162c-4431-8be0-1833b52302e5" xsi:schemaLocation="http://www.openmicroscopy.org/Schemas/OME/2016-06 http://www.openmicroscopy.org/Schemas/OME/2016-06/ome.xsd"><Image ID="Image:0"><Pixels BigEndian="false" DimensionOrder="XYZCT" ID="Pixels:0" PhysicalSizeX="0.32499998807907104" PhysicalSizeXUnit="µm" PhysicalSizeY="0.32499998807907104" PhysicalSizeYUnit="µm" SizeC="3" SizeT="1" SizeX="57346" SizeY="54325" SizeZ="1" Type="uint8"><Channel ID="Channel:0:0" Name="Red" SamplesPerPixel="1"><LightPath /></Channel><Channel ID="Channel:0:1" Name="Green" SamplesPerPixel="1"><LightPath /></Channel><Channel ID="Channel:0:2" Name="Blue" SamplesPerPixel="1"><LightPath /></Channel><TiffData IFD="0" PlaneCount="3" /><Plane TheC="0" TheT="0" TheZ="0" /><Plane TheC="1" TheT="0" TheZ="0" /><Plane TheC="2" TheT="0" TheZ="0" /></Pixels></Image></OME>""",  # noqa
        'checks': {
            'frames': 3,
            'IndexRange': {'IndexC': 3},
            'IndexStride': {'IndexC': 1},
            'channelmap': {'Blue': 2, 'Green': 1, 'Red': 0},
            'channels': ['Red', 'Green', 'Blue'],
        },
    }]
    # Create a source so we can use internal functions for testing
    imagePath = datastore.fetch('sample.ome.tif')
    source = large_image_source_ometiff.open(imagePath)
    for sample in samples:
        xml = ElementTree.fromstring(sample['xml'])
        info = etreeToDict(xml)
        assert etreeToDict(dictToEtree(info)) == info
        source._omeinfo = info['OME']
        source._parseOMEInfo()
        metadata = source.getMetadata()
        for key, value in sample['checks'].items():
            if key in {'frames'}:
                assert len(metadata[key]) == value
            else:
                assert metadata[key] == value


def testFrameStyleOMETiff():
    imagePath = datastore.fetch('DDX58_AXL_EGFR_well2_XY01.ome.tif')
    source = large_image_source_ometiff.open(imagePath, style={'bands': [{'frame': 4}]})
    tile1 = source.getTile(0, 0, 2)
    tile2 = source.getTile(0, 0, 2, frame=1)
    assert tile1 == tile2
