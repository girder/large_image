# -*- coding: utf-8 -*-

import glob
import json
import os
import PIL.Image
import PIL.ImageChops
import pytest
import six

from large_image.exceptions import TileSourceException

import large_image_source_mapnik

from . import utilities


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
    if isinstance(image, six.binary_type):
        image = PIL.Image.open(six.BytesIO(image))
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


def testTileFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath)
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
    assert tileMetadata['bounds']['srs'] == '+proj=utm +zone=11 +datum=WGS84 +units=m +no_defs '
    assert tileMetadata['geospatial']
    # Check that we read some band data, too
    assert len(tileMetadata['bands']) == 3
    assert tileMetadata['bands'][2]['interpretation'] == 'green'
    assert tileMetadata['bands'][2]['max'] == 212.0
    assert tileMetadata['bands'][2]['min'] == 0.0

    # Getting the metadata with a specified projection will be different
    source = large_image_source_mapnik.MapnikFileTileSource(
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
    assert tileMetadata['bounds']['srs'] == '+init=epsg:3857'
    assert tileMetadata['geospatial']

    source = large_image_source_mapnik.MapnikFileTileSource(
        imagePath, projection='EPSG:3857', style=json.dumps({'band': -1}))
    image = source.getTile(89, 207, 9, encoding='PNG')
    _assertImageMatches(image, 'geotiff_9_89_207')


def testTileStyleFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'matplotlib.Plasma_6'})
    source = large_image_source_mapnik.MapnikFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    image = source.getTile(22, 51, 7, encoding='PNG')
    _assertImageMatches(image, 'geotiff_style_7_22_51')


def testTileLinearStyleFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'matplotlib.Plasma_6',
                        'scheme': 'linear'})
    source = large_image_source_mapnik.MapnikFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    image = source.getTile(22, 51, 7, encoding='PNG')
    _assertImageMatches(image, 'geotiff_style_linear_7_22_51')


def testTileStyleBadInput():
    def _assertStyleResponse(imagePath, style, message):
        with pytest.raises(TileSourceException) as exc:
            source = large_image_source_mapnik.MapnikFileTileSource(
                imagePath, projection='EPSG:3857', style=json.dumps(style))
            source.getTile(22, 51, 7, encoding='PNG')
        assert message in str(exc)

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
        'min': 'bad',
        'max': 100,
    }, 'Minimum and maximum values should be numbers, "auto", "min", or "max".')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'min': 0,
        'max': 'bad',
    }, 'Minimum and maximum values should be numbers, "auto", "min", or "max".')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'palette': 'nonexistent.palette'
    }, 'Palette is not a valid palettable path.')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'palette': ['notacolor', '#00ffff']
    }, 'Mapnik failed to parse color')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'palette': ['#00ffff']
    }, 'A palette must have at least 2 colors.')

    _assertStyleResponse(imagePath, {
        'band': 1,
        'palette': 'matplotlib.Plasma_6',
        'scheme': 'some_invalid_scheme'
    }, 'Scheme has to be either "discrete" or "linear".')

    _assertStyleResponse(imagePath, ['style'],
                         'Style is not a valid json object.')


def testThumbnailFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath)
    # We get a thumbnail without a projection
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    # We get a different thumbnail with a projection
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath, projection='EPSG:3857')
    image2, mimeType = source.getThumbnail(encoding='PNG')
    assert image2[:len(utilities.PNGHeader)] == utilities.PNGHeader
    assert image != image2


def testPixel():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')

    # Test in pixel coordinates
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath)
    pixel = source.getPixel(region={'left': 212, 'top': 198})
    assert pixel == {
        'r': 62, 'g': 65, 'b': 66, 'a': 255, 'bands': {1: 62.0, 2: 65.0, 3: 66.0}}
    pixel = source.getPixel(region={'left': 2120, 'top': 198})
    assert pixel == {}

    # Test with a projection
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 77, 'g': 82, 'b': 84, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Check if the point is outside of the image
    pixel = source.getPixel(region={'left': 10000000, 'top': 4000000, 'units': 'projection'})
    assert pixel == {
        'r': 0, 'g': 0, 'b': 0, 'a': 0}

    # Test with styles
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'matplotlib.Plasma_6'})
    source = large_image_source_mapnik.MapnikFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 225, 'g': 100, 'b': 98, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with palette as an array of colors
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': ['#0000ff', '#00ff00', '#ff0000']})
    source = large_image_source_mapnik.MapnikFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 0, 'g': 255, 'b': 0, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with projection units
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 77, 'g': 82, 'b': 84, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    pixel = source.getPixel(region={'left': -117.975, 'top': 33.865, 'units': 'WGS84'})
    assert pixel == {
        'r': 77, 'g': 82, 'b': 84, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    # When the tile has a different projection, the pixel is the same as
    # the band values.
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 77, 'g': 82, 'b': 84, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}


def testSourceErrors():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    with pytest.raises(TileSourceException) as exc:
        large_image_source_mapnik.MapnikFileTileSource(imagePath, 'EPSG:4326')
    assert 'must not be geographic' in str(exc)
    imagePath = os.path.join(testDir, 'test_files', 'zero_gi.tif')
    with pytest.raises(TileSourceException) as exc:
        large_image_source_mapnik.MapnikFileTileSource(imagePath)
    assert 'cannot be opened via Mapnik' in str(exc)
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    with pytest.raises(TileSourceException) as exc:
        large_image_source_mapnik.MapnikFileTileSource(imagePath)
    assert 'does not have a projected scale' in str(exc)


def testStereographicProjection():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    # We will fail if we ask for a stereographic projection and don't
    # specify unitsPerPixel
    with pytest.raises(TileSourceException) as exc:
        large_image_source_mapnik.MapnikFileTileSource(imagePath, 'EPSG:3411')
    assert 'unitsPerPixel must be specified' in str(exc)
    # But will pass if unitsPerPixel is specified
    large_image_source_mapnik.MapnikFileTileSource(imagePath, 'EPSG:3411', unitsPerPixel=150000)


def testProj4Proj():
    # Test obtaining pyproj.Proj projection values
    proj4Proj = large_image_source_mapnik.MapnikFileTileSource._proj4Proj

    proj = proj4Proj(b'epsg:4326')
    assert proj4Proj(u'epsg:4326').srs == proj.srs
    assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
    assert proj4Proj(4326) is None


def testConvertProjectionUnits():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    tsNoProj = large_image_source_mapnik.MapnikFileTileSource(imagePath)

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

    with pytest.raises(TileSourceException) as exc:
        tsNoProj._convertProjectionUnits(
            -117.5, None, -117, None, None, None, 'EPSG:4326')
    assert 'Cannot convert' in str(exc)

    tsProj = large_image_source_mapnik.MapnikFileTileSource(imagePath, projection='EPSG:3857')
    result = tsProj._convertProjectionUnits(
        -13024380, 3895303, None, None, None, None, 'EPSG:3857')
    assert result[0] == pytest.approx(-13024380, 1)
    assert result[1] == pytest.approx(3895303, 1)
    assert result[2:] == (None, None, 'projection')


def testGuardAgainstBadLatLong():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'global_dem.tif')
    source = large_image_source_mapnik.MapnikFileTileSource(imagePath)
    bounds = source.getBounds(srs='EPSG:4326')

    assert bounds['xmin'] == -180.00416667
    assert bounds['xmax'] == 179.99583333
    assert bounds['ymin'] == -89.99583333
    assert bounds['ymax'] == 89.999999
