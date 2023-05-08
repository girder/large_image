import glob
import io
import json
import os

import large_image_source_rasterio
import numpy
import PIL.Image
import PIL.ImageChops
import pytest

from large_image import constants
from large_image.exceptions import TileSourceError, TileSourceInefficientError
from large_image.tilesource.utilities import ImageBytes

from . import utilities
from .datastore import datastore


@pytest.fixture
def opener():
    return large_image_source_rasterio.open


def _assertImageMatches(image, testRootName, saveTestImageFailurePath='/tmp'):
    """
    Check if an image matches any of a set of images.

    Adapted from:
    https://stackoverflow.com/questions/35176639/compare-images-python-pil

    :param image: PIL image to compare or a binary string of the image.
    :param testRootName: base name of the images to test.  These images are
        globbed in test_files/<testRootName>*.png.
    :param saveTestImageFailurePath: if the image doesn't match any of the
        test images, if this value is set, save the image to make it easier
        to determine why it failed.
    """
    if isinstance(image, bytes):
        image = PIL.Image.open(io.BytesIO(image))
    image = image.convert('RGBA')
    testDir = os.path.dirname(os.path.realpath(__file__))
    testImagePaths = glob.glob(os.path.join(
        testDir, 'test_files', testRootName + '*.png'))
    testImages = [PIL.Image.open(testImagePath).convert('RGBA')
                  for testImagePath in testImagePaths]
    diffs = [PIL.ImageChops.difference(image, testImage).getbbox()
             for testImage in testImages]
    if None not in diffs and saveTestImageFailurePath:
        image.save(os.path.join(saveTestImageFailurePath, testRootName + '_test.png'))
    assert None in diffs


def testTileFromGeotiffs(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = opener(imagePath)
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 256
    assert tileMetadata['sizeY'] == 256
    assert tileMetadata['levels'] == 1
    assert tileMetadata['bounds']['xmax'] == 597915.0
    assert tileMetadata['bounds']['xmin'] == 367185.0
    assert tileMetadata['bounds']['ymax'] == 3788115.0
    assert tileMetadata['bounds']['ymin'] == 3552885.0
    # assert (tileMetadata['bounds']['srs'].strip() ==
    #         '+proj=utm +zone=11 +datum=WGS84 +units=m +no_defs')
    # assert tileMetadata["bounds"]["srs"].lower() == "epsg:32611"
    assert tileMetadata['geospatial']
    # Check that we read some band data, too
    assert len(tileMetadata['bands']) == 3
    assert tileMetadata['bands'][2]['interpretation'] == 'green'
    assert tileMetadata['bands'][2]['max'] == 240.0  # 212.0 (why gdal reporting 212) TODO
    assert tileMetadata['bands'][2]['min'] == 0.0

    # Getting the metadata with a specified projection will be different
    source = opener(
        imagePath, projection='EPSG:3857')
    tileMetadata = source.getMetadata()

    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 65536
    assert tileMetadata['sizeY'] == 65536
    assert tileMetadata['levels'] == 9
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-12906033, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-13184900, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(4059661, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(3777034, 1)
    assert tileMetadata['bounds']['srs'].lower() == 'epsg:3857'
    assert tileMetadata['geospatial']

    source = opener(
        imagePath, projection='EPSG:3857', style={'band': -1}, encoding='PNG')
    image = source.getTile(89, 207, 9)
    _assertImageMatches(image, 'geotiff_9_89_207')


def testTileStyleFromGeotiffs(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = {'band': 1, 'min': 0, 'max': 100,
             'scheme': 'discrete',
             'palette': 'matplotlib.Plasma_6'}
    source = opener(
        imagePath, projection='EPSG:3857', style=style)
    image = source.getTile(22, 51, 7, encoding='PNG')
    _assertImageMatches(image, 'geotiff_style_7_22_51')


def testTileLinearStyleFromGeotiffs(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = {'band': 1, 'min': 0, 'max': 100,
             'palette': 'matplotlib.Plasma_6',
             'scheme': 'linear'}
    source = opener(
        imagePath, projection='EPSG:3857', style=style, encoding='PNG')
    image = source.getTile(22, 51, 7)
    _assertImageMatches(image, 'geotiff_style_linear_7_22_51')


def testTileStyleBadInput(opener):
    def _assertStyleResponse(imagePath, style, message):
        with pytest.raises((TileSourceError, ValueError), match=message):
            source = opener(
                imagePath, projection='EPSG:3857', style=style, encoding='PNG')
            source.getTile(22, 51, 7)

    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')

    _assertStyleResponse(imagePath, {
        'band': 1.1,
    }, 'Band has to be a positive integer, -1, or a band interpretation found in the source.')

    _assertStyleResponse(imagePath, {
        'band': 500,
    }, 'Band has to be a positive integer, -1, or a band interpretation found in the source.')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'palette': 'nonexistent.palette'
    }, 'cannot be used as a color palette')

    _assertStyleResponse(imagePath, ['style'],
                         'Style is not a valid json object.')


def testThumbnailFromGeotiffs(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = opener(imagePath)
    # We get a thumbnail without a projection
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    image, mimeType = source.getThumbnail(encoding='JPEG')
    assert isinstance(image, ImageBytes)
    assert image[:len(utilities.JPEGHeader)] == utilities.JPEGHeader
    # We get a different thumbnail with a projection
    source = opener(imagePath, projection='EPSG:3857')
    image2, mimeType = source.getThumbnail(encoding='PNG')
    assert isinstance(image2, ImageBytes)
    assert image2[:len(utilities.PNGHeader)] == utilities.PNGHeader
    assert image != image2


def testPixel(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')

    # Test in pixel coordinates
    source = opener(imagePath)
    pixel = source.getPixel(region={'left': 212, 'top': 198})
    assert pixel == {
        'r': 76, 'g': 78, 'b': 77, 'a': 255, 'bands': {1: 62.0, 2: 65.0, 3: 66.0}}
    pixel = source.getPixel(region={'left': 2120, 'top': 198})
    assert pixel == {}

    # Test with a projection
    source = opener(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with styles
    style = {'band': 1, 'min': 0, 'max': 100,
             'palette': 'matplotlib.Plasma_6'}
    source = opener(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 247, 'g': 156, 'b': 60, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with palette as an array of colors
    style = {'band': 1, 'min': 0, 'max': 100,
             'palette': ['#0000ff', '#00ff00', '#ff0000']}
    source = opener(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 137, 'g': 117, 'b': 0, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with projection units
    source = opener(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    pixel = source.getPixel(region={'left': -117.975, 'top': 33.865, 'units': 'WGS84'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    # When the tile has a different projection, the pixel is the same as
    # the band values.
    source = opener(imagePath)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}


def testSourceErrors(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    with pytest.raises(TileSourceError, match='must not be geographic'):
        opener(imagePath, 'EPSG:4326')
    imagePath = os.path.join(testDir, 'test_files', 'zero_gi.tif')
    with pytest.raises(TileSourceError, match='cannot be opened via'):
        opener(imagePath)
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    with pytest.raises(TileSourceError, match='does not have a projected scale'):
        opener(imagePath)


def testStereographicProjection(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    # We will fail if we ask for a stereographic projection and don't
    # specify unitsPerPixel
    with pytest.raises(TileSourceError, match='unitsPerPixel must be specified'):
        opener(imagePath, 'EPSG:3411')
    # But will pass if unitsPerPixel is specified
    opener(imagePath, 'EPSG:3411', unitsPerPixel=150000)


def testConvertProjectionUnits(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    tsNoProj = opener(imagePath)

    result = tsNoProj._convertProjectionUnits(
        -13024380, 3895303, None, None, None, None, 'EPSG:3857')
    assert result[0] == pytest.approx(147, 1)
    assert result[1] == pytest.approx(149, 1)
    assert result[2:] == (None, None, 'base_pixels')

    result = tsNoProj._convertProjectionUnits(
        None, None, -13080040, 3961860, None, None, 'EPSG:3857')
    assert result[2] == pytest.approx(96, 1)
    assert result[3] == pytest.approx(88, 1)
    assert result[:2] == (None, None)
    result = tsNoProj._convertProjectionUnits(
        -117.5, 33, None, None, 0.5, 0.5, 'EPSG:4326')
    assert result[0] == pytest.approx(96, 1)
    assert result[1] == pytest.approx(149, 1)
    assert result[2] == pytest.approx(147, 1)
    assert result[3] == pytest.approx(89, 1)
    result = tsNoProj._convertProjectionUnits(
        None, None, -117, 33.5, 0.5, 0.5, 'EPSG:4326')
    assert result[0] == pytest.approx(96, 1)
    assert result[1] == pytest.approx(149, 1)
    assert result[2] == pytest.approx(147, 1)
    assert result[3] == pytest.approx(89, 1)
    result = tsNoProj._convertProjectionUnits(
        -117.5, 33, None, None, 0.5, 0.5, 'EPSG:4326', unitsWH='base_pixels')
    assert result[0] == pytest.approx(96, 1)
    assert result[1] == pytest.approx(149, 1)
    assert result[2:] == (None, None, 'base_pixels')

    with pytest.raises(TileSourceError, match='Cannot convert'):
        tsNoProj._convertProjectionUnits(
            -117.5, None, -117, None, None, None, 'EPSG:4326')

    tsProj = opener(imagePath, projection='EPSG:3857')
    result = tsProj._convertProjectionUnits(
        -13024380, 3895303, None, None, None, None, 'EPSG:3857')
    assert result[0] == pytest.approx(-13024380, 1)
    assert result[1] == pytest.approx(3895303, 1)
    assert result[2:] == (None, None, 'projection')


def testGuardAgainstBadLatLong(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'global_dem.tif')
    source = opener(imagePath)
    bounds = source.getBounds(srs='EPSG:4326')

    assert bounds['xmin'] == -180
    assert bounds['xmax'] == 180
    assert bounds['ymin'] == -89.99583333
    assert bounds['ymax'] == 90


def testPalettizedGeotiff(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    source = opener(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 687
    assert tileMetadata['sizeY'] == 509
    assert tileMetadata['levels'] == 3
    # assert tileMetadata['bounds']['srs'].strip().startswith(
    #     '+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 +y_0=0')
    # assert tileMetadata["bounds"]["srs"].lower() == "epsg:5070"
    assert tileMetadata['geospatial']
    assert len(tileMetadata['bands']) == 1
    assert tileMetadata['bands'][1]['interpretation'] == 'palette'
    # Getting the metadata with a specified projection will be different
    source = opener(
        imagePath, projection='EPSG:3857', encoding='PNG')
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 65536
    assert tileMetadata['sizeY'] == 65536
    assert tileMetadata['levels'] == 9
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-7837888, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-8909162, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(5755717, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(4876273, 1)
    assert tileMetadata['bounds']['srs'].lower() == 'epsg:3857'
    assert tileMetadata['geospatial']
    image = source.getTile(37, 46, 7)
    image = PIL.Image.open(io.BytesIO(image))
    image = numpy.asarray(image)
    assert list(image[0, 0, :]) == [0, 0, 0, 0]
    assert list(image[255, 0, :]) == [221, 201, 201, 255]


def testRetileProjection(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath, projection='EPSG:3857')
    ti = ts.getSingleTile(tile_size=dict(width=1000, height=1000), tile_position=1000)
    assert ti['tile'].size == 3000000
    tile = ts.getTile(1178, 1507, 12)
    assert len(tile) > 1000


def testInternalMetadata(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = opener(imagePath)
    metadata = source.getInternalMetadata()
    assert metadata['driverShortName'] == 'GTiff'


def testGetRegionWithProjection(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath, projection='EPSG:3857')
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             format=constants.TILE_FORMAT_NUMPY)
    assert region.shape == (1024, 1024, 4)


def testGCPProjection(opener):
    imagePath = datastore.fetch('region_gcp.tiff')
    source = opener(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 1204
    assert tileMetadata['sizeY'] == 512
    assert tileMetadata['levels'] == 4
    assert tileMetadata['geospatial']

    source = opener(imagePath, projection='EPSG:3857')
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 524288
    assert tileMetadata['sizeY'] == 524288
    assert tileMetadata['levels'] == 12
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-10753925, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-10871650, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(3949393, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(3899358, 1)
    assert tileMetadata['bounds']['srs'].lower() == 'epsg:3857'
    assert tileMetadata['geospatial']


def testGetTiledRegion(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath)
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(2006547, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(1319547, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(2658548, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(2149548, 1)
    assert '+proj=aea' in tileMetadata['bounds']['srs']
    region.unlink()


def testGetTiledRegionWithProjection(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath, projection='EPSG:3857')
    # This gets the whole world
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(20037508, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-20037508, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(20037508, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(-20037508, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()

    # Ask for a smaller part
    region, _ = ts.getRegion(
        output=dict(maxWidth=1024, maxHeight=1024),
        region=dict(left=-8622811, right=-8192317, bottom=5294998,
                    top=5477835, units='projection'),
        encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-8192215, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-8622708, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(5477783, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(5294946, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()


def testGetTiledRegion16Bit(opener):
    imagePath = datastore.fetch('region_gcp.tiff')
    ts = opener(imagePath)
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-10753925, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-10871650, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(3949393, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(3899358, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()


def testGetTiledRegionWithStyle(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath, style='{"bands":[]}')
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(2006547, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(1319547, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(2658548, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(2149548, 1)
    assert '+proj=aea' in tileMetadata['bounds']['srs']
    region.unlink()


def testGetTiledRegionWithProjectionAndStyle(opener):
    imagePath = datastore.fetch('landcover_sample_1000.tif')
    ts = opener(imagePath, projection='EPSG:3857', style='{"bands":[]}')
    # This gets the whole world
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(20037508, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-20037508, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(20037508, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(-20037508, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()

    # Ask for a smaller part
    region, _ = ts.getRegion(
        output=dict(maxWidth=1024, maxHeight=1024),
        region=dict(left=-8622811, right=-8192317, bottom=5294998,
                    top=5477835, units='projection'),
        encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-8192215, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-8622708, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(5477783, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(5294946, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()


def testGetTiledRegion16BitWithStyle(opener):
    imagePath = datastore.fetch('region_gcp.tiff')
    ts = opener(imagePath, style='{"bands":[]}')
    region, _ = ts.getRegion(output=dict(maxWidth=1024, maxHeight=1024),
                             encoding='TILED')
    result = opener(str(region))
    tileMetadata = result.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-10753925, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-10871650, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(3949393, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(3899358, 1)
    assert '+proj=merc' in tileMetadata['bounds']['srs']
    region.unlink()


def testFileWithoutProjection(opener):
    imagePath = datastore.fetch('oahu-dense.tiff')
    ts = opener(imagePath, projection='EPSG:3857')
    tileMetadata = ts.getMetadata()
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-17548722, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-17620245, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(2477890, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(2420966, 1)
    assert 'epsg:3857' in tileMetadata['bounds']['srs'].lower()


def testMatplotlibPalette(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'viridis'})
    source = opener(
        imagePath, projection='EPSG:3857', style=style, encoding='PNG')
    image = source.getTile(22, 51, 7)
    image = PIL.Image.open(io.BytesIO(image))
    image = numpy.asarray(image)
    assert list(image[0, 0, :]) == [68, 1, 84, 0]


def testHttpVfsPath(opener):
    imagePath = datastore.get_url('landcover_sample_1000.tif')
    source = opener(
        imagePath, projection='EPSG:3857', encoding='PNG')
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 65536
    assert tileMetadata['sizeY'] == 65536
    assert tileMetadata['levels'] == 9
    assert tileMetadata['bounds']['xmax'] == pytest.approx(-7837888, 1)
    assert tileMetadata['bounds']['xmin'] == pytest.approx(-8909162, 1)
    assert tileMetadata['bounds']['ymax'] == pytest.approx(5755717, 1)
    assert tileMetadata['bounds']['ymin'] == pytest.approx(4876273, 1)
    assert tileMetadata['bounds']['srs'].lower() == 'epsg:3857'
    assert tileMetadata['geospatial']


def testVfsCogValidation(opener):
    imagePath = datastore.get_url('TC_NG_SFBay_US_Geo_COG.tif')
    source = opener(
        imagePath, projection='EPSG:3857', encoding='PNG')
    assert source.validateCOG()
    imagePath = datastore.get_url('TC_NG_SFBay_US_Geo.tif')
    source = opener(
        imagePath, projection='EPSG:3857', encoding='PNG')
    with pytest.raises(TileSourceInefficientError):
        source.validateCOG()


def testNoData(opener):
    imagePath = datastore.get_url('TC_NG_SFBay_US_Geo_COG.tif')
    source = opener(
        imagePath, projection='EPSG:3857',
        style={'bands': [{'band': 1, 'max': '100', 'min': '5', 'nodata': '0'}]})
    assert source.getThumbnail()[0]
    source = opener(
        imagePath, projection='EPSG:3857',
        style={'bands': [{'band': 1, 'max': 100, 'min': 5, 'nodata': 0}]})
    assert source.getThumbnail()[0]


def testAlphaProjection(opener):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgba_geotiff.tiff')
    source = opener(
        imagePath, projection='EPSG:3857')
    base = source.getThumbnail(encoding='PNG')[0]
    basenp = source.getThumbnail(format='numpy')[0]
    assert numpy.count_nonzero(basenp[:, :, 3] == 255) > 30000
    source = opener(
        imagePath, projection='EPSG:3857',
        style={'bands': [
            {'band': 1, 'palette': 'R'},
            {'band': 2, 'palette': 'G'},
            {'band': 3, 'palette': 'B'}]})
    assert source.getThumbnail(encoding='PNG')[0] == base
    assert not (source.getThumbnail(format='numpy')[0] - basenp).any()
    source = opener(
        imagePath)
    assert numpy.count_nonzero(source.getThumbnail(format='numpy')[0][:, :, 3] == 255) > 30000
