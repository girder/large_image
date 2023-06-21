import io
import json
import os
import re
import sys
from pathlib import Path

import numpy
import PIL.Image
import pytest

import large_image
from large_image.cache_util import cachesClear
from large_image.tilesource import nearPowerOfTwo

from . import utilities
from .datastore import datastore, registry

# In general, if there is something in skipTiles, the reader should be improved
# to either indicate that the file can't be read or changed to handle reading
# with correct exceptions.
# 'skip' is used to exclude testing specific paths.  This might be necessary
# if a file is dependent on other files as these generalized tests don't ensure
# a download order.
SourceAndFiles = {
    'bioformats': {
        'read': r'\.(czi|jp2|svs|scn|dcm|qptiff)$',
        'noread': r'JK-kidney_B',
        'skip': r'TCGA-AA-A02O.*\.svs',
        # We need to modify the bioformats reader similar to tiff's
        # getTileFromEmptyDirectory
        'skipTiles': r'(TCGA-DU-6399|sample_jp2k_33003)',
    },
    'deepzoom': {},
    'dicom': {
        'read': r'\.dcm$',
        'python': sys.version_info >= (3, 8),
    },
    'dummy': {'any': True, 'skipTiles': r''},
    'gdal': {
        'read': r'\.(jpg|jpeg|jp2|ptif|scn|svs|tif.*|qptiff)$',
        'noread': r'(huron\.image2_jpeg2k|sample_jp2k_33003|TCGA-DU-6399|\.(ome.tiff|nc)$)',
        'skipTiles': r'\.*nc$',
    },
    'mapnik': {
        'read': r'\.(jpg|jpeg|jp2|ptif|nc|scn|svs|tif.*|qptiff)$',
        'noread': r'(huron\.image2_jpeg2k|sample_jp2k_33003|TCGA-DU-6399|\.(ome.tiff)$)',
        # we should only test this with a projection
        'skipTiles': r'',
    },
    'multi': {
        'read': r'\.(yml|yaml)$',
        'skip': r'(multi_source\.yml|multi-source-composite\.yaml)$',
    },
    'nd2': {
        'read': r'\.(nd2)$',
        'python': sys.version_info >= (3, 7),
    },
    'ometiff': {'read': r'\.(ome\.tif.*)$'},
    'openjpeg': {'read': r'\.(jp2)$'},
    'openslide': {
        'read': r'\.(ptif|svs|tif.*|qptiff)$',
        'noread': r'(oahu|DDX58_AXL|huron\.image2_jpeg2k|landcover_sample|d042-353\.crop|US_Geo\.|extraoverview|imagej)',  # noqa
        'skipTiles': r'one_layer_missing',
    },
    'pil': {
        'read': r'\.(jpg|jpeg|png|tif.*)$',
        'noread': r'(G10-3|JK-kidney|d042-353.*tif|huron|one_layer_missing|US_Geo|extraoverview' + (
            r'|sample.*ome' if sys.version_info < (3, 7) else r'') + r')',
    },
    'rasterio': {
        'read': r'\.(jpg|jpeg|jp2|ptif|scn|svs|tif.*|qptiff)$',
        'noread': r'(huron\.image2_jpeg2k|sample_jp2k_33003|TCGA-DU-6399|\.(ome.tiff|nc)$)',
        'python': sys.version_info >= (3, 8),
    },
    'test': {'any': True, 'skipTiles': r''},
    'tiff': {
        'read': r'\.(ptif|scn|svs|tif.*|qptiff)$',
        'noread': r'(oahu|DDX58_AXL|G10-3_pelvis_crop|'
                  r'd042-353\.crop\.small\.float|landcover_sample|US_Geo\.|'
                  r'imagej)',
        'skipTiles': r'(sample_image\.ptif|one_layer_missing_tiles)'},
    'tifffile': {
        'read': r'',
        'noread': r'\.(nc|nd2|yml|yaml|json|czi|png|jpg|jpeg|jp2|dcm)$',
        'python': sys.version_info >= (3, 7),
    },
    'vips': {
        'read': r'',
        'noread': r'\.(nc|nd2|yml|yaml|json|czi|png|svs|scn|dcm)$',
        'skipTiles': r'(sample_image\.ptif|one_layer_missing_tiles|JK-kidney_B-gal_H3_4C_1-500sec\.jp2|extraoverview)'  # noqa
    },
}


# Remove sources that don't meet python requirements from our list
for source, entry in list(SourceAndFiles.items()):
    if entry.get('python', True) is False:
        SourceAndFiles.pop(source, None)


def testNearPowerOfTwo():
    assert nearPowerOfTwo(45808, 11456)
    assert nearPowerOfTwo(45808, 11450)
    assert not nearPowerOfTwo(45808, 11200)
    assert nearPowerOfTwo(45808, 11400)
    assert not nearPowerOfTwo(45808, 11400, 0.005)
    assert nearPowerOfTwo(45808, 11500)
    assert not nearPowerOfTwo(45808, 11500, 0.005)


def testCanRead():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    assert large_image.canRead(imagePath) is False
    assert large_image.canRead(imagePath, mimeType='image/png') is False

    imagePath = datastore.fetch('sample_image.ptif')
    assert large_image.canRead(imagePath) is True
    assert large_image.canRead(imagePath, mimeType='image/png') is True


@pytest.mark.parametrize('source', [k for k, v in SourceAndFiles.items() if not v.get('any')])
def testSourcesFileNotFound(source):
    large_image.tilesource.loadTileSources()
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile')
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile.ext')


def testBaseFileNotFound():
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.open('nosuchfile')
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.open('nosuchfile.ext')


@pytest.mark.parametrize('filename', registry)
@pytest.mark.parametrize('source', SourceAndFiles)
def testSourcesCanRead(source, filename):
    sourceInfo = SourceAndFiles[source]
    if re.search(sourceInfo.get('skip', r'^$'), filename):
        pytest.skip('this file needs more complex tests')
    canRead = sourceInfo.get('any') or (
        re.search(sourceInfo.get('read', r'^$'), filename) and
        not re.search(sourceInfo.get('noread', r'^$'), filename))
    imagePath = datastore.fetch(filename)
    large_image.tilesource.loadTileSources()
    sourceClass = large_image.tilesource.AvailableTileSources[source]
    assert bool(sourceClass.canRead(imagePath)) is bool(canRead)
    # Test module canRead method
    mod = sys.modules[sourceClass.__module__]
    assert bool(mod.canRead(imagePath)) is bool(canRead)

    cachesClear()


@pytest.mark.parametrize('filename', registry)
@pytest.mark.parametrize('source', SourceAndFiles)
def testSourcesCanReadPath(source, filename):
    sourceInfo = SourceAndFiles[source]
    if re.search(sourceInfo.get('skip', r'^$'), filename):
        pytest.skip('this file needs more complex tests')
    canRead = sourceInfo.get('any') or (
        re.search(sourceInfo.get('read', r'^$'), filename) and
        not re.search(sourceInfo.get('noread', r'^$'), filename))
    imagePath = datastore.fetch(filename)
    large_image.tilesource.loadTileSources()
    sourceClass = large_image.tilesource.AvailableTileSources[source]
    assert bool(sourceClass.canRead(Path(imagePath))) is bool(canRead)

    cachesClear()


@pytest.mark.parametrize('filename', registry)
@pytest.mark.parametrize('source', SourceAndFiles)
def testSourcesTilesAndMethods(source, filename):
    sourceInfo = SourceAndFiles[source]
    if re.search(sourceInfo.get('skip', r'^$'), filename):
        pytest.skip('this file needs more complex tests')
    canRead = sourceInfo.get('any') or (
        re.search(sourceInfo.get('read', r'^$'), filename) and
        not re.search(sourceInfo.get('noread', r'^$'), filename))
    if not canRead:
        pytest.skip('source does not work with this file')
    if re.search(sourceInfo.get('skipTiles', r'^$'), filename):
        pytest.skip('source fails tile tests from this file')
    imagePath = datastore.fetch(filename)
    large_image.tilesource.loadTileSources()
    sourceClass = large_image.tilesource.AvailableTileSources[source]
    ts = sourceClass(imagePath)
    tileMetadata = ts.getMetadata()
    utilities.checkTilesZXY(ts, tileMetadata)
    # All of these should succeed
    assert ts.getInternalMetadata() is not None
    assert ts.getOneBandInformation(1) is not None
    assert len(ts.getBandInformation()) >= 1
    assert len(ts.getBandInformation()) == tileMetadata['bandCount']
    assert ts.getPixel(region=dict(left=0, top=0)) is not None
    # Histograms are too slow to test in this way
    #  assert len(ts.histogram()['histogram']) >= 1
    #  assert ts.histogram(onlyMinMax=True)['min'][0] is not None
    # Test multiple frames if they exist
    assert ts.frames >= 1
    if ts.frames > 1:
        assert ts.frames == len(tileMetadata['frames'])
        utilities.checkTilesZXY(
            ts, tileMetadata, tileParams=dict(frame=ts.frames - 1))
    # Test if we can fetch an associated image if any exist
    assert ts.getAssociatedImagesList() is not None
    if len(ts.getAssociatedImagesList()):
        # This should be an image and a mime type
        assert len(ts.getAssociatedImage(ts.getAssociatedImagesList()[0])) == 2
    assert ts.getAssociatedImage('nosuchimage') is None
    # Test the serializability of common methods
    assert json.dumps(ts.getMetadata())
    assert json.dumps(ts.getPixel(region=dict(left=0, top=0)))
    # Test module open method
    mod = sys.modules[sourceClass.__module__]
    assert mod.open(imagePath) is not None

    cachesClear()


@pytest.mark.parametrize('filename,isgeo', [
    ('04091217_ruc.nc', True),
    ('HENormalN801.czi', False),
    ('landcover_sample_1000.tif', True),
    ('oahu-dense.tiff', True),
    ('region_gcp.tiff', True),
])
def testIsGeospatial(filename, isgeo):
    imagePath = datastore.fetch(filename)
    assert large_image.tilesource.isGeospatial(imagePath) == isgeo

    cachesClear()


@pytest.mark.parametrize('palette', [
    ['#000', '#FFF'],
    ['#000', '#888', '#FFF'],
    '#fff',
    'black',
    'rgba(128, 128, 128, 128)',
    'rgb(128, 128, 128)',
    'xkcd:blue',
    'viridis',
    'matplotlib.Plasma_6',
    [(0.5, 0.5, 0.5), (0.1, 0.1, 0.1, 0.1), 'xkcd:blue'],
    'coolwarm',
    'GREEN',
])
def testGoodGetPaletteColors(palette):
    large_image.tilesource.utilities.getPaletteColors(palette)
    assert large_image.tilesource.utilities.isValidPalette(palette) is True


@pytest.mark.parametrize('palette', [
    'notacolor',
    [0.5, 0.5, 0.5],
    ['notacolor', '#fff'],
    'notapalette',
    'matplotlib.Plasma_128',
])
def testBadGetPaletteColors(palette):
    with pytest.raises(ValueError):
        large_image.tilesource.utilities.getPaletteColors(palette)
    assert large_image.tilesource.utilities.isValidPalette(palette) is False


def testGetAvailableNamedPalettes():
    assert len(large_image.tilesource.utilities.getAvailableNamedPalettes()) > 100
    assert len(large_image.tilesource.utilities.getAvailableNamedPalettes()) > \
        len(large_image.tilesource.utilities.getAvailableNamedPalettes(False))

    assert len(large_image.tilesource.utilities.getAvailableNamedPalettes(False)) > \
        len(large_image.tilesource.utilities.getAvailableNamedPalettes(False, True))


def testExpanduserPath():
    imagePath = datastore.fetch('sample_image.ptif')
    assert large_image.canRead(imagePath)
    absPath = os.path.abspath(imagePath)
    userDir = os.path.expanduser('~') + os.sep
    if absPath.startswith(userDir):
        userPath = '~' + os.sep + absPath[len(userDir):]
        assert large_image.canRead(userPath)
        assert large_image.canRead(Path(userPath))


def testClassRepr():
    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image.open(imagePath)
    assert 'sample_image.ptif' in repr(ts)


def testTileOverlap():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'test_orient1.tif')
    ts = large_image.open(imagePath)
    assert [(
        tiles['x'], tiles['x'] + tiles['width'], tiles['width'],
        tiles['tile_overlap']['left'], tiles['tile_overlap']['right']
    ) for tiles in ts.tileIterator(
        tile_size=dict(width=75, height=180), tile_overlap=dict(x=60))
    ] == [
        (0, 75, 75, 0, 30),
        (15, 90, 75, 30, 30),
        (30, 105, 75, 30, 30),
        (45, 120, 75, 30, 0),
    ]
    assert [(
        tiles['x'], tiles['x'] + tiles['width'], tiles['width'],
        tiles['tile_overlap']['left'], tiles['tile_overlap']['right']
    ) for tiles in ts.tileIterator(
        tile_size=dict(width=75, height=180), tile_overlap=dict(x=60, edges=True))
    ] == [
        (0, 45, 45, 0, 30),
        (0, 60, 60, 15, 30),
        (0, 75, 75, 30, 30),
        (15, 90, 75, 30, 30),
        (30, 105, 75, 30, 30),
        (45, 120, 75, 30, 30),
        (60, 120, 60, 30, 15),
        (75, 120, 45, 30, 0),
    ]
    assert [(
        tiles['x'], tiles['x'] + tiles['width'], tiles['width'],
        tiles['tile_overlap']['left'], tiles['tile_overlap']['right']
    ) for tiles in ts.tileIterator(
        tile_size=dict(width=60, height=60), tile_overlap=dict(x=40, y=40),
        region=dict(left=55, top=65, width=15, height=15))
    ] == [
        (55, 70, 15, 0, 0)
    ]


def testLazyTileRelease():
    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image.open(imagePath)

    tiles = list(ts.tileIterator(
        scale={'magnification': 2.5},
        format=large_image.constants.TILE_FORMAT_IMAGE,
        encoding='PNG'))
    assert isinstance(tiles[5], large_image.tilesource.tiledict.LazyTileDict)
    assert super(large_image.tilesource.tiledict.LazyTileDict, tiles[5]).__getitem__(
        'tile') is None
    data = tiles[5]['tile']
    assert len(tiles[5]['tile']) > 0
    assert super(large_image.tilesource.tiledict.LazyTileDict, tiles[5]).__getitem__(
        'tile') is not None
    tiles[5].release()
    assert super(large_image.tilesource.tiledict.LazyTileDict, tiles[5]).__getitem__(
        'tile') is None
    assert tiles[5]['tile'] == data


def testTileOverlapWithRegionOffset():
    imagePath = datastore.fetch('sample_image.ptif')
    ts = large_image.open(imagePath)
    tileIter = ts.tileIterator(
        region=dict(left=10000, top=10000, width=6000, height=6000),
        tile_size=dict(width=1936, height=1936),
        tile_overlap=dict(x=400, y=400))
    firstTile = next(tileIter)
    assert firstTile['tile_overlap']['right'] == 200


@pytest.mark.parametrize('options,lensrc,lenquads,frame10,src0,srclast,quads10', [
    ({'maxTextureSize': 16384}, 1, 250, 10, {
        'encoding': 'JPEG',
        'exact': False,
        'fill': 'corner:black',
        'framesAcross': 14,
        'height': 880,
        'jpegQuality': 85,
        'jpegSubsampling': 1,
        'width': 1168,
    }, None, {
        'bottom': 15840,
        'left': 11680,
        'right': 12848,
        'top': 14964,
    }),

    ({'format': {'encoding': 'PNG'}}, 1, 250, 10, {
        'encoding': 'PNG',
        'jpeqQuality': None,
    }, None, None),

    ({'query': {'style': 'abc=def'}}, 1, 250, 10, {
        'style': 'abc=def',
    }, None, None),

    ({'maxTextureSize': 4096}, 1, 250, 10, {
        'framesAcross': 14,
        'height': 224,
        'width': 288,
    }, None, {
        'left': 2880,
        'top': 3816,
    }),

    ({'maxTextureSize': 16384, 'maxTextures': 8}, 4, 250, 10, {
        'framesAcross': 7,
        'height': 1632,
        'width': 2176,
    }, None, {
        'left': 6528,
        'top': 13056,
    }),

    ({'maxTextures': 8, 'maxTextureSize': 4096}, 8, 250, 10, {
        'framesAcross': 5,
        'height': 576,
        'width': 768,
    }, None, {
        'left': 0,
        'top': 2304,
    }),

    ({'maxTextureSize': 16384,
      'maxTextures': 8, 'maxTotalTexturePixels': 8 * 1024 ** 3}, 8, 250, 10, {
        'framesAcross': 5,
        'height': 2336,
        'width': 3120,
    }, None, {
        'left': 0,
        'top': 9344,
    }),

    ({'maxTextureSize': 16384, 'alignment': 32}, 1, 250, 10, {
        'framesAcross': 14,
        'height': 864,
        'width': 1152,
    }, None, {
        'left': 11520,
        'top': 14688,
    }),

    ({'maxTextureSize': 16384, 'frameBase': 100}, 1, 150, 110, {
        'framesAcross': 11,
        'height': 1088,
        'width': 1456,
    }, None, {
        'left': 14560,
        'top': 14144,
    }),

    ({'maxTextureSize': 16384, 'frameStride': 10}, 1, 25, 100, {
        'framesAcross': 5,
        'height': 2448,
        'width': 3264,
    }, None, {
        'left': 0,
        'top': 4896,
    }),

    ({'maxTextures': 8, 'maxTextureSize': 4096, 'frameGroup': 50}, 5, 250, 10, {
        'framesAcross': 7,
        'height': 432,
        'width': 576,
    }, None, {
        'left': 1728,
        'top': 2592,
    }),

    ({
        'maxTextures': 8,
        'maxTextureSize': 4096,
        'frameGroup': 250,
        'frameGroupFactor': 4
    }, 8, 250, 10, {
        'framesAcross': 5,
        'height': 576,
        'width': 768,
    }, None, {
        'left': 0,
        'top': 2304,
    }),

    ({
        'maxTextures': 8,
        'maxTextureSize': 4096,
        'frameGroup': 50,
        'frameGroupStride': 5
    }, 5, 250, 50, {
        'framesAcross': 7,
        'height': 432,
        'width': 576,
    }, None, None),

    ({'maxFrameSize': 250}, 1, 250, 10, {
        'framesAcross': 17,
        'height': 192,
        'width': 240,
    }, None, {
        'left': 2400,
        'top': 2700,
    }),

    ({'maxTotalTexturePixels': 16 * 1024 ** 2}, 1, 250, 10, {
        'framesAcross': 14,
        'height': 224,
        'width': 288,
    }, None, {
        'left': 2880,
        'top': 3816,
    }),

    ({
        'maxTextures': 8,
        'maxTextureSize': 4096,
        'frameBase': 'c',
        'frameStride': 'c',
        'frameGroup': 'z',
        'frameGroupStride': 'auto',
    }, 10, None, None, {
        'framesAcross': 5,
        'height': 624,
        'width': 816,
    }, None, None),
])
def testGetTileFramesQuadInfo(options, lensrc, lenquads, frame10, src0, srclast, quads10):
    metadata = {
        'frames': [0] * 250,
        'IndexRange': {'IndexC': 5, 'IndexZ': 25, 'IndexT': 2},
        'levels': 10,
        'sizeX': 100000,
        'sizeY': 75000,
        'tileHeight': 256,
        'tileWidth': 256
    }
    results = large_image.tilesource.utilities.getTileFramesQuadInfo(metadata, options)
    assert len(results['src']) == lensrc
    if lenquads:
        assert len(results['quads']) == lenquads
    if frame10 is not None and len(results['frames']) > 10:
        assert results['frames'][10] == frame10
    for key, value in src0.items():
        if value is not None:
            assert results['src'][0][key] == value
        else:
            assert key not in results['src'][0]
    if srclast is not None:
        for key, value in srclast.items():
            assert results['src'][-1][key] == value
    if quads10 is not None and len(results['quads']) > 10:
        crop10 = results['quads'][10]['crop']
        for key, value in quads10.items():
            assert crop10[key] == value


def testCanReadList():
    imagePath = datastore.fetch('sample_image.ptif')
    assert len(large_image.canReadList(imagePath)) > 1
    assert any(canRead for source, canRead in large_image.canReadList(imagePath))


def testImageBytes():
    ib = large_image.tilesource.utilities.ImageBytes(b'abc')
    assert ib == b'abc'
    assert isinstance(ib, bytes)
    assert 'ImageBytes' in repr(ib)
    assert ib.mimetype is None
    assert ib._repr_jpeg_() is None
    assert ib._repr_png_() is None
    ib = large_image.tilesource.utilities.ImageBytes(b'abc', 'image/jpeg')
    assert ib.mimetype == 'image/jpeg'
    assert 'ImageBytes' in repr(ib)
    assert ib._repr_jpeg_() == b'abc'
    assert ib._repr_png_() is None
    ib = large_image.tilesource.utilities.ImageBytes(b'abc', 'image/png')
    assert ib.mimetype == 'image/png'
    assert 'ImageBytes' in repr(ib)
    assert ib._repr_jpeg_() is None
    assert ib._repr_png_() == b'abc'
    ib = large_image.tilesource.utilities.ImageBytes(b'abc', 'other')
    assert ib.mimetype == 'other'
    assert 'ImageBytes' in repr(ib)
    assert ib._repr_jpeg_() is None
    assert ib._repr_png_() is None


@pytest.mark.parametrize('format', [
    format for format in large_image.constants.TileOutputMimeTypes
    if format not in {'TILED'}])
def testOutputFormats(format):
    imagePath = datastore.fetch('sample_image.ptif')
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePathRGBA = os.path.join(testDir, 'test_files', 'rgba_geotiff.tiff')

    ts = large_image.open(imagePath, encoding=format)
    img = PIL.Image.open(io.BytesIO(ts.getTile(0, 0, 0)))
    assert (img.width, img.height) == (256, 256)
    img = PIL.Image.open(io.BytesIO(ts.getThumbnail(encoding=format)[0]))
    assert (img.width, img.height) == (256, 53)

    ts = large_image.open(imagePathRGBA, encoding=format)
    img = PIL.Image.open(io.BytesIO(ts.getTile(0, 0, 0)))
    assert (img.width, img.height) == (256, 256)
    img = PIL.Image.open(io.BytesIO(ts.getThumbnail(encoding=format)[0]))
    assert (img.width, img.height) == (256, 256)


def testStyleFunctions():
    imagePath = datastore.fetch('extraoverview.tiff')
    source = large_image.open(imagePath)
    region1, _ = source.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    sourceFunc2 = large_image.open(imagePath, style={
        'function': {
            'name': 'large_image.tilesource.stylefuncs.maskPixelValues',
            'context': True,
            'parameters': {'values': [164, 165]}},
        'bands': []})
    region2, _ = sourceFunc2.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert numpy.any(region2 != region1)
    sourceFunc3 = large_image.open(imagePath, style={
        'function': {
            'name': 'large_image.tilesource.stylefuncs.maskPixelValues',
            'context': True,
            'parameters': {'values': [[63, 63, 63]]}},
        'bands': []})
    region3, _ = sourceFunc3.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert numpy.any(region3 != region2)
    sourceFunc4 = large_image.open(imagePath, style={
        'function': [{
            'name': 'large_image.tilesource.stylefuncs.maskPixelValues',
            'context': 'context',
            'parameters': {'values': [164, 165]}}],
        'bands': []})
    region4, _ = sourceFunc4.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert numpy.all(region4 == region2)


def testStyleFunctionsWarnings():
    imagePath = datastore.fetch('extraoverview.tiff')
    source = large_image.open(imagePath, style={
        'function': {
            'name': 'large_image.tilesource.stylefuncs.maskPixelValues',
            'context': True,
            'parameters': {'values': ['bad value']}},
        'bands': []})
    region, _ = source.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert source._styleFunctionWarnings

    source = large_image.open(imagePath, style={
        'function': {
            'name': 'no_such_module.maskPixelValues',
            'context': True,
            'parameters': {'values': [100]}},
        'bands': []})
    region, _ = source.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert source._styleFunctionWarnings

    source = large_image.open(imagePath, style={
        'function': {
            'name': 'large_image.tilesource.stylefuncs.noSuchFunction',
            'context': True,
            'parameters': {'values': [100]}},
        'bands': []})
    region, _ = source.getRegion(
        output=dict(maxWidth=50),
        format=large_image.constants.TILE_FORMAT_NUMPY)
    assert source._styleFunctionWarnings
