"""Test the default libtiff based tile source."""

import os
import large_image
import testinfra.utils.ansible_runner
import urllib
import pytest


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_pip_packages(host):
    """Check python dependencies for tiff tile source."""
    virtualenv = '~/.virtualenvs/large_image/bin/pip'
    packages = host.pip_package.get_packages(pip_path=virtualenv).keys()
    assert 'libtiff' in packages


@pytest.mark.parametrize("item, output", [
    ('590346ff8d777f16d01e054c', '/tmp/Huron.Image2_JPEG2K.tif')
])
def test_tiff_tile_source(item, output):
    """Check whether large_image can return a tile with tiff sources."""
    test_url = 'https://data.kitware.com/api/v1/item/{}/download'.format(item)
    urllib.urlretrieve(test_url, output)
    image = large_image.getTileSource(output)
    # Make sure it is the tiff tile source
    assert isinstance(image, large_image.tilesource.TiffFileTileSource)
    # Make sure we can get a tile without an exception
    assert type(image.getTile(0, 0, 0)) == str
