import contextlib
import os

import pytest

pytestmark = pytest.mark.girder

# Make it easier to test without girder
with contextlib.suppress(ImportError):
    from large_image_tasks import tasks


def test_conversion(tmp_path):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')

    outputPath = tasks.create_tiff(imagePath, 'temp.tiff', tmp_path)
    assert os.path.getsize(outputPath) > 500000


def test_conversion_with_non_tiff_name(tmp_path):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = tasks.create_tiff(imagePath, 'temp.test', tmp_path)
    assert os.path.getsize(outputPath) > 500000


def test_conversion_with_no_name(tmp_path):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    outputPath = tasks.create_tiff(imagePath, outputDir=tmp_path)
    assert os.path.getsize(outputPath) > 2000


def test_conversion_with_no_directory():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    outputPath = tasks.create_tiff(imagePath, 'temp.tiff')
    assert os.path.getsize(outputPath) > 500000
    os.unlink(outputPath)


def test_conversion_missing_file():
    with pytest.raises(Exception):
        tasks.create_tiff('nosuchfile')


def test_conversion_failure():
    with pytest.raises(Exception):
        tasks.create_tiff(os.path.realpath(__file__))
