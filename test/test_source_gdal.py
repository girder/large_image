# -*- coding: utf-8 -*-

import glob
import json
import numpy
import os
import PIL.Image
import PIL.ImageChops
import pytest
import six

from large_image.exceptions import TileSourceException

import large_image_source_gdal

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
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
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
    assert (tileMetadata['bounds']['srs'].strip() ==
            '+proj=utm +zone=11 +datum=WGS84 +units=m +no_defs')
    assert tileMetadata['geospatial']
    # Check that we read some band data, too
    assert len(tileMetadata['bands']) == 3
    assert tileMetadata['bands'][2]['interpretation'] == 'green'
    assert tileMetadata['bands'][2]['max'] == 212.0
    assert tileMetadata['bands'][2]['min'] == 0.0

    # Getting the metadata with a specified projection will be different
    source = large_image_source_gdal.GDALFileTileSource(
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

    source = large_image_source_gdal.GDALFileTileSource(
        imagePath, projection='EPSG:3857', style=json.dumps({'band': -1}), encoding='PNG')
    image = source.getTile(89, 207, 9)
    _assertImageMatches(image, 'geotiff_9_89_207')


def testTileLinearStyleFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'matplotlib.Plasma_6',
                        'scheme': 'linear'})
    source = large_image_source_gdal.GDALFileTileSource(
        imagePath, projection='EPSG:3857', style=style, encoding='PNG')
    image = source.getTile(22, 51, 7)
    _assertImageMatches(image, 'geotiff_style_linear_7_22_51')


def testTileStyleBadInput():
    def _assertStyleResponse(imagePath, style, message):
        with pytest.raises(TileSourceException, match=message):
            source = large_image_source_gdal.GDALFileTileSource(
                imagePath, projection='EPSG:3857', style=json.dumps(style), encoding='PNG')
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
    }, 'Palette is not a valid palettable path.')

    _assertStyleResponse(imagePath, ['style'],
                         'Style is not a valid json object.')


def testThumbnailFromGeotiffs():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
    # We get a thumbnail without a projection
    image, mimeType = source.getThumbnail(encoding='PNG')
    assert image[:len(utilities.PNGHeader)] == utilities.PNGHeader
    # We get a different thumbnail with a projection
    source = large_image_source_gdal.GDALFileTileSource(imagePath, projection='EPSG:3857')
    image2, mimeType = source.getThumbnail(encoding='PNG')
    assert image2[:len(utilities.PNGHeader)] == utilities.PNGHeader
    assert image != image2


def testPixel():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')

    # Test in pixel coordinates
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
    pixel = source.getPixel(region={'left': 212, 'top': 198})
    assert pixel == {
        'r': 76, 'g': 78, 'b': 77, 'a': 255, 'bands': {1: 62.0, 2: 65.0, 3: 66.0}}
    pixel = source.getPixel(region={'left': 2120, 'top': 198})
    assert pixel == {}

    # Test with a projection
    source = large_image_source_gdal.GDALFileTileSource(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with styles
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': 'matplotlib.Plasma_6'})
    source = large_image_source_gdal.GDALFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 247, 'g': 156, 'b': 60, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with palette as an array of colors
    style = json.dumps({'band': 1, 'min': 0, 'max': 100,
                        'palette': ['#0000ff', '#00ff00', '#ff0000']})
    source = large_image_source_gdal.GDALFileTileSource(
        imagePath, projection='EPSG:3857', style=style)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'projection'})
    assert pixel == {
        'r': 137, 'g': 117, 'b': 0, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}

    # Test with projection units
    source = large_image_source_gdal.GDALFileTileSource(imagePath, projection='EPSG:3857')
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    pixel = source.getPixel(region={'left': -117.975, 'top': 33.865, 'units': 'WGS84'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}
    # When the tile has a different projection, the pixel is the same as
    # the band values.
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
    pixel = source.getPixel(region={'left': -13132910, 'top': 4010586, 'units': 'EPSG:3857'})
    assert pixel == {
        'r': 94, 'g': 98, 'b': 99, 'a': 255, 'bands': {1: 77.0, 2: 82.0, 3: 84.0}}


def testSourceErrors():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    with pytest.raises(TileSourceException, match='must not be geographic'):
        large_image_source_gdal.GDALFileTileSource(imagePath, 'EPSG:4326')
    imagePath = os.path.join(testDir, 'test_files', 'zero_gi.tif')
    with pytest.raises(TileSourceException, match='cannot be opened via'):
        large_image_source_gdal.GDALFileTileSource(imagePath)
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    with pytest.raises(TileSourceException, match='does not have a projected scale'):
        large_image_source_gdal.GDALFileTileSource(imagePath)


def testStereographicProjection():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    # We will fail if we ask for a stereographic projection and don't
    # specify unitsPerPixel
    with pytest.raises(TileSourceException, match='unitsPerPixel must be specified'):
        large_image_source_gdal.GDALFileTileSource(imagePath, 'EPSG:3411')
    # But will pass if unitsPerPixel is specified
    large_image_source_gdal.GDALFileTileSource(imagePath, 'EPSG:3411', unitsPerPixel=150000)


def testProj4Proj():
    # Test obtaining pyproj.Proj projection values
    proj4Proj = large_image_source_gdal.GDALFileTileSource._proj4Proj

    proj = proj4Proj(b'epsg:4326')
    assert proj4Proj(u'epsg:4326').srs == proj.srs
    assert proj4Proj('proj4:EPSG:4326').srs == proj.srs
    assert proj4Proj(4326) is None


def testConvertProjectionUnits():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    tsNoProj = large_image_source_gdal.GDALFileTileSource(imagePath)

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

    with pytest.raises(TileSourceException, match='Cannot convert'):
        tsNoProj._convertProjectionUnits(
            -117.5, None, -117, None, None, None, 'EPSG:4326')

    tsProj = large_image_source_gdal.GDALFileTileSource(imagePath, projection='EPSG:3857')
    result = tsProj._convertProjectionUnits(
        -13024380, 3895303, None, None, None, None, 'EPSG:3857')
    assert result[0] == pytest.approx(-13024380, 1)
    assert result[1] == pytest.approx(3895303, 1)
    assert result[2:] == (None, None, 'projection')


def testGuardAgainstBadLatLong():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'global_dem.tif')
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
    bounds = source.getBounds(srs='EPSG:4326')

    assert bounds['xmin'] == -180.00416667
    assert bounds['xmax'] == 179.99583333
    assert bounds['ymin'] == -89.99583333
    assert bounds['ymax'] == 90


def testPalettizedGeotiff():
    imagePath = utilities.externaldata('data/landcover_sample_1000.tif.sha512')
    source = large_image_source_gdal.GDALFileTileSource(imagePath)
    tileMetadata = source.getMetadata()
    assert tileMetadata['tileWidth'] == 256
    assert tileMetadata['tileHeight'] == 256
    assert tileMetadata['sizeX'] == 687
    assert tileMetadata['sizeY'] == 509
    assert tileMetadata['levels'] == 3
    assert (tileMetadata['bounds']['srs'].strip() ==
            '+proj=aea +lat_0=23 +lon_0=-96 +lat_1=29.5 +lat_2=45.5 +x_0=0 '
            '+y_0=0 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs')
    assert tileMetadata['geospatial']
    assert len(tileMetadata['bands']) == 1
    assert tileMetadata['bands'][1]['interpretation'] == 'palette'
    # Getting the metadata with a specified projection will be different
    source = large_image_source_gdal.GDALFileTileSource(
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
    assert tileMetadata['bounds']['srs'] == '+init=epsg:3857'
    assert tileMetadata['geospatial']
    image = source.getTile(37, 46, 7)
    image = PIL.Image.open(six.BytesIO(image))
    image = numpy.asarray(image)
    assert list(image[0, 0, :]) == [0, 0, 0, 0]
    assert list(image[255, 0, :]) == [221, 201, 201, 255]
