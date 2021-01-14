import os
import subprocess

from .utilities import externaldata


def test_average_color():
    testDir = os.path.dirname(os.path.realpath(__file__))
    examplesDir = os.path.join(testDir, '..', 'examples')
    prog = 'average_color.py'

    imagePath = externaldata('data/sample_image.ptif.sha512')
    process = subprocess.Popen([
        'python', prog, imagePath, '-m', '1.25'],
        shell=False, stdout=subprocess.PIPE, cwd=examplesDir)
    results = process.stdout.readlines()
    assert len(results) == 18
    finalColor = [float(val) for val in results[-1].split()[-3:]]
    assert round(finalColor[0]) == 245
    assert round(finalColor[1]) == 247
    assert round(finalColor[2]) == 247


def test_average_color_import():
    from examples.average_color import average_color

    imagePath = externaldata('data/sample_image.ptif.sha512')
    mean = average_color(imagePath, 1.25)
    assert round(mean[0]) == 245
    assert round(mean[1]) == 247
    assert round(mean[2]) == 247


def test_sum_squares():
    testDir = os.path.dirname(os.path.realpath(__file__))
    examplesDir = os.path.join(testDir, '..', 'examples')
    prog = 'sumsquare_color.py'

    imagePath = externaldata('data/sample_image.ptif.sha512')
    process = subprocess.Popen([
        'python', prog, imagePath, '-m', '2.5'],
        shell=False, stdout=subprocess.PIPE, cwd=examplesDir)
    results = process.stdout.readlines()
    firstColor = [float(val) for val in results[-1].split()[-3:]]

    process = subprocess.Popen([
        'python', prog, imagePath, '-m', '2.5',
        '-w', '800', '-h', '423', '-x', '40', '-y', '26'],
        shell=False, stdout=subprocess.PIPE, cwd=examplesDir)
    results = process.stdout.readlines()
    finalColor = [float(val) for val in results[-1].split()[-3:]]
    assert finalColor == firstColor


def test_sum_squares_import():
    from examples.sumsquare_color import sum_squares

    imagePath = externaldata('data/sample_image.ptif.sha512')
    firstColor = sum_squares(imagePath, 2.5).tolist()
    finalColor = sum_squares(
        imagePath, 2.5, tile_width=800, tile_height=423, overlap_x=40,
        overlap_y=26).tolist()
    assert finalColor == firstColor

    # We should get the same result if we retile the image to process it with
    # different options.
    finalColor = sum_squares(
        imagePath, 2.5, tile_width=657, tile_height=323, overlap_x=40,
        overlap_y=26, overlap_edges=True).tolist()
    assert finalColor == firstColor

    # We should get the same results with odd overlaps
    finalColor = sum_squares(
        imagePath, 2.5, tile_width=800, tile_height=423, overlap_x=41,
        overlap_y=27).tolist()
    assert finalColor == firstColor

    finalColor = sum_squares(
        imagePath, 2.5, tile_width=657, tile_height=323, overlap_x=41,
        overlap_y=27, overlap_edges=True).tolist()
    assert finalColor == firstColor
