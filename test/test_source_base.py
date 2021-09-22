import os
import re

import pytest

import large_image
from large_image.tilesource import nearPowerOfTwo

from . import utilities
from .datastore import datastore, registry

# In general, if there is something in skipTiles, the reader should be improved
# to either indicate that the file can't be read or changed to handle reading
# with correct exceptions.
SourceAndFiles = {
    'bioformats': {
        'read': r'\.(czi|jp2|svs|scn)$',
        # We need to modify the bioformats reader similar to tiff's
        # getTileFromEmptyDirectory
        'skipTiles': r'(JK-kidney_B|TCGA-AA-A02O|TCGA-DU-6399|sample_jp2k_33003|\.scn$)'},
    'deepzoom': {},
    'dummy': {'any': True, 'skipTiles': r''},
    'gdal': {
        'read': r'\.(jpeg|jp2|ptif|nc|scn|svs|tif.*)$',
        'noread': r'(huron\.image2_jpeg2k|sample_jp2k_33003|TCGA-DU-6399|\.(ome.tiff)$)',
        'skipTiles': r'\.*nc$'},
    'mapnik': {
        'read': r'\.(jpeg|jp2|ptif|nc|scn|svs|tif.*)$',
        'noread': r'(huron\.image2_jpeg2k|sample_jp2k_33003|TCGA-DU-6399|\.(ome.tiff)$)',
        # we should only test this with a projection
        'skipTiles': r''},
    'nd2': {'read': r'\.(nd2)$'},
    'ometiff': {'read': r'\.(ome\.tif.*)$'},
    'openjpeg': {'read': r'\.(jp2)$'},
    'openslide': {
        'read': r'\.(ptif|svs|tif.*)$',
        'noread': r'(DDX58_AXL|huron\.image2_jpeg2k|landcover_sample|d042-353\.crop)',
        'skipTiles': r'one_layer_missing'},
    'pil': {
        'read': r'\.(jpeg|png|tif.*)$',
        'noread': r'(G10-3|JK-kidney|d042-353|huron|sample.*ome|one_layer_missing)'},
    'test': {'any': True, 'skipTiles': r''},
    'tiff': {
        'read': r'\.(ptif|scn|svs|tif.*)$',
        'noread': r'(DDX58_AXL|G10-3_pelvis_crop|d042-353\.crop\.small\.float|landcover_sample)',
        'skipTiles': r'(sample_image\.ptif|one_layer_missing_tiles)'},
}


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

    imagePath = datastore.fetch('sample_image.ptif')
    assert large_image.canRead(imagePath) is True


@pytest.mark.parametrize('source', [k for k, v in SourceAndFiles.items() if not v.get('any')])
def testSourcesFileNotFound(source):
    large_image.tilesource.loadTileSources()
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile')
    with pytest.raises(large_image.exceptions.TileSourceFileNotFoundError):
        large_image.tilesource.AvailableTileSources[source]('nosuchfile.ext')


@pytest.mark.parametrize('filename', registry)
@pytest.mark.parametrize('source', SourceAndFiles)
def testSourcesCanRead(source, filename):
    sourceInfo = SourceAndFiles[source]
    canRead = sourceInfo.get('any') or (
        re.search(sourceInfo.get('read', r'^$'), filename) and
        not re.search(sourceInfo.get('noread', r'^$'), filename))
    imagePath = datastore.fetch(filename)
    large_image.tilesource.loadTileSources()
    sourceClass = large_image.tilesource.AvailableTileSources[source]
    assert bool(sourceClass.canRead(imagePath)) is bool(canRead)


@pytest.mark.parametrize('filename', registry)
@pytest.mark.parametrize('source', SourceAndFiles)
def testSourcesTilesAndMethods(source, filename):
    sourceInfo = SourceAndFiles[source]
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
    # Histograms are too slow to test in this way
    #  assert len(ts.histogram()['histogram']) >= 1
    #  assert ts.histogram(onlyMinMax=True)['min'][0] is not None
    # Test multiple frames if they exist
    if len(tileMetadata.get('frames', [])) > 1:
        tsf = sourceClass(imagePath, frame=len(tileMetadata['frames']) - 1)
        tileMetadata = tsf.getMetadata()
        utilities.checkTilesZXY(tsf, tileMetadata)
