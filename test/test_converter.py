import json
import os
import shutil

import large_image_converter
import large_image_converter.__main__ as main
import large_image_source_tiff
import pytest
import tifftools

import large_image
from large_image import constants

from .datastore import datastore


def testIsGeospatial():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    assert large_image_converter.is_geospatial(imagePath) is True

    imagePath = datastore.fetch(
        'sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-'
        'af6f-14fefbbdf7bd.svs')
    assert large_image_converter.is_geospatial(imagePath) is False

    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    assert large_image_converter.is_geospatial(imagePath) is False


def testIsVips():
    imagePath = datastore.fetch(
        'sample_svs_image.TCGA-DU-6399-01A-01-TS1.e8eb65de-d63e-42db-'
        'af6f-14fefbbdf7bd.svs')
    assert large_image_converter.is_vips(imagePath) is True

    imagePath = datastore.fetch('HENormalN801.czi')
    assert large_image_converter.is_vips(imagePath) is False


@pytest.mark.parametrize(('convert_args', 'taglist'), [
    ({}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.LZW.value,
        tifftools.Tag.TileWidth.value: 256,
    }),
    ({'compression': 'jpeg'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.JPEG.value,
    }),
    ({'compression': 'deflate'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.AdobeDeflate.value,
    }),
    ({'compression': 'lzw'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.LZW.value,
    }),
    ({'compression': 'packbits', 'predictor': 'yes'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.Packbits.value,
    }),
    ({'compression': 'zstd'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.ZSTD.value,
    }),
    ({'compression': 'jpeg', 'quality': 50}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.JPEG.value,
    }),
    ({'compression': 'deflate', 'level': 2}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.AdobeDeflate.value,
    }),
    ({'compression': 'lzw', 'predictor': 'yes'}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.LZW.value,
    }),
    ({'compression': 'webp', 'quality': 0}, {
        tifftools.Tag.Compression.value: tifftools.constants.Compression.WEBP.value,
    }),
    ({'tileSize': 512}, {
        tifftools.Tag.TileWidth.value: 512,
    }),
])
def testConvert(tmpdir, convert_args, taglist):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, **convert_args)
    info = tifftools.read_tiff(outputPath)
    for key, value in taglist.items():
        assert info['ifds'][0]['tags'][key]['data'][0] == value


def testConvertGeospatial(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    inputPath = os.path.join(tmpdir, 'in.geo.tiff')
    shutil.copy(imagePath, inputPath)
    outputPath = large_image_converter.convert(inputPath, level=5)
    assert 'geo.tiff' in outputPath
    assert outputPath != inputPath
    info = tifftools.read_tiff(outputPath)
    assert tifftools.Tag.ModelTiepointTag.value in info['ifds'][0]['tags']


def testConvertPTIF(tmpdir):
    imagePath = datastore.fetch('sample_image.ptif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, compression='jpeg', quality=50)
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 11


def testConvertOverwrite(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    open(outputPath, 'w').write('placeholder')
    with pytest.raises(Exception):
        large_image_converter.convert(imagePath, outputPath)
    large_image_converter.convert(imagePath, outputPath, overwrite=True)
    assert os.path.getsize(outputPath) > 100


def testConvertOMETif(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    # Note: change this when we convert multi-frame files differently
    large_image_converter.convert(imagePath, outputPath)
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 3
    assert len(info['ifds'][0]['tags'][tifftools.Tag.SubIFD.value]['ifds']) == 4


def testConvertTiffFloatPixels(tmpdir):
    imagePath = datastore.fetch('d042-353.crop.small.float32.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath)
    info = tifftools.read_tiff(outputPath)
    assert (info['ifds'][0]['tags'][tifftools.Tag.SampleFormat.value]['data'][0] ==
            tifftools.constants.SampleFormat.uint.value)


def testConvertTiffPreserveFloatPixels(tmpdir):
    imagePath = datastore.fetch('d042-353.crop.small.float32.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, keepFloat=True)
    info = tifftools.read_tiff(outputPath)
    assert (info['ifds'][0]['tags'][tifftools.Tag.SampleFormat.value]['data'][0] ==
            tifftools.constants.SampleFormat.float.value)


def testConvertJp2kCompression(tmpdir):
    imagePath = datastore.fetch('sample_Easy1.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, compression='jp2k')
    info = tifftools.read_tiff(outputPath)
    assert (info['ifds'][0]['tags'][tifftools.Tag.Compression.value]['data'][0] ==
            tifftools.constants.Compression.JP2000.value)
    source = large_image_source_tiff.open(outputPath)
    image, _ = source.getRegion(
        output={'maxWidth': 200, 'maxHeight': 200}, format=constants.TILE_FORMAT_NUMPY)
    # Without or with icc adjustment
    assert ((image[12][167][:3] == [215, 135, 172]).all() or
            (image[12][167][:3] == [216, 134, 172]).all())

    outputPath2 = os.path.join(tmpdir, 'out2.tiff')
    large_image_converter.convert(imagePath, outputPath2, compression='jp2k', psnr=50)
    assert os.path.getsize(outputPath2) < os.path.getsize(outputPath)

    outputPath3 = os.path.join(tmpdir, 'out3.tiff')
    large_image_converter.convert(imagePath, outputPath3, compression='jp2k', cr=100)
    assert os.path.getsize(outputPath3) < os.path.getsize(outputPath)
    assert os.path.getsize(outputPath3) != os.path.getsize(outputPath2)


def testConvertFromLargeImage(tmpdir):
    imagePath = datastore.fetch('sample_image.jp2')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 6


def testConvertFromMultiframeImage(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 5
    assert len(metadata['frames']) == 3
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 3


def testConvertFromMultiframeImageNoSubIFDS(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, subifds=False)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 5
    assert len(metadata['frames']) == 3
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 15


def testConvertFromMultiframeImageOnlyOneFrame(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, onlyFrame=2)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 5
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 5


def testConvertToAperio(tmpdir):
    imagePath = datastore.fetch('huron.image2_jpeg2k.tif')
    outputPath = os.path.join(tmpdir, 'out.svs')
    large_image_converter.convert(imagePath, outputPath, format='aperio')
    source = large_image.open(outputPath)
    assert 'openslide' in source.name
    assert 'label' in source.getAssociatedImagesList()


def testConvertMultiframeToAperio(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, format='aperio', compression='jp2k')
    source = large_image.open(outputPath)
    assert 'label' in source.getAssociatedImagesList()


# Test main program

def testConverterMain(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    main.main([imagePath, outputPath])
    assert os.path.getsize(outputPath) > 100

    outputPath2 = os.path.join(tmpdir, 'out2.tiff')
    main.main([imagePath, outputPath2, '--compression', 'zip'])
    assert os.path.getsize(outputPath2) > 100
    assert os.path.getsize(outputPath2) < os.path.getsize(outputPath)


def testConverterMainNonFile(tmpdir):
    outputPath = os.path.join(tmpdir, 'out.tiff')
    assert main.main(['not a file', outputPath]) == 1


def testConverterMainNonImageFile(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'notanimage.txt')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    with pytest.raises(Exception):
        main.main([imagePath, outputPath])
    assert not os.path.exists(outputPath)


def testConverterMainStats(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    main.main([imagePath, outputPath, '--stats'])
    info = tifftools.read_tiff(outputPath)
    desc = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
    assert 'conversion_stats' in desc['large_image_converter']


def testConverterMainFullStats(tmpdir):
    imagePath = datastore.fetch('sample_Easy1.png')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    main.main([imagePath, outputPath, '--full-stats'])
    info = tifftools.read_tiff(outputPath)
    desc = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
    assert 'psnr' in desc['large_image_converter']['conversion_stats']


def testConverterMainFullStatsWithWebp(tmpdir):
    imagePath = datastore.fetch('d042-353.crop.small.float32.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    main.main([imagePath, outputPath, '--compression', 'webp', '--full-stats'])
    info = tifftools.read_tiff(outputPath)
    desc = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
    assert 'psnr' in desc['large_image_converter']['conversion_stats']
    assert desc['large_image_converter']['conversion_stats']['psnr'] < 60


def testConverterMainConcurrency(tmpdir):
    imagePath = datastore.fetch('sample.ome.tif')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    main.main([imagePath, outputPath, '--concurrency', '2'])
    assert os.path.getsize(outputPath) > 100


def testConverterMissingTiles(tmpdir):
    imagePath = datastore.fetch('one_layer_missing_tiles.tiff')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath)
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 6


def testConvertFromTestSourceFrames(tmpdir):
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert('large_image://test?maxLevel=3&frames=4', outputPath)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 4
    assert len(metadata['frames']) == 4
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 4


def testConvertFromTestSourceFrameArray(tmpdir):
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(
        'large_image://test?maxLevel=3&frames=2,3&monochrome=true', outputPath)
    source = large_image_source_tiff.open(outputPath)
    metadata = source.getMetadata()
    assert metadata['levels'] == 4
    assert len(metadata['frames']) == 6
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 6


def testConvertImageJ(tmpdir):
    imagePath = datastore.fetch('synthetic_imagej.tiff')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath, compression='jpeg', quality=50)
    info = tifftools.read_tiff(outputPath)
    assert len(info['ifds']) == 44


def testConvertFloat328BitRange(tmpdir):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'sample_float32_8bit_range.zarr.zip')
    outputPath = os.path.join(tmpdir, 'out.tiff')
    large_image_converter.convert(imagePath, outputPath)
    ts = large_image.open(outputPath)
    pixel = ts.getPixel(x=0, y=0)
    assert pixel['value'] == [132, 131, 122, 255]
