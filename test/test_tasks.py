import os
import pytest
import shutil
import tempfile

from large_image_tasks import tasks


def test_conversion():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')

    tmpdir = tempfile.mkdtemp()
    outputPath = tasks.create_tiff(imagePath, 'temp.tiff', tmpdir)
    assert os.path.getsize(outputPath) > 500000
    shutil.rmtree(tmpdir)


def test_conversion_with_non_tiff_name():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'yb10kx5k.png')
    tmpdir = tempfile.mkdtemp()
    outputPath = tasks.create_tiff(imagePath, 'temp.test', tmpdir)
    assert os.path.getsize(outputPath) > 500000
    shutil.rmtree(tmpdir)


def test_conversion_with_no_name():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    tmpdir = tempfile.mkdtemp()
    outputPath = tasks.create_tiff(imagePath, outputDir=tmpdir)
    assert os.path.getsize(outputPath) > 2000
    shutil.rmtree(tmpdir)


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
