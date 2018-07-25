"""Test the svs based tile source."""

import os
import large_image
import testinfra.utils.ansible_runner
import urllib
import pytest


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_pip_packages(host):
    """Check python dependencies for svs tile source."""
    virtualenv = '~/.virtualenvs/large_image/bin/pip'
    packages = host.pip_package.get_packages(pip_path=virtualenv).keys()
    assert 'openslide-python' in packages


@pytest.mark.parametrize("file, output", [
    ('57b345d28d777f126827dc27', '/tmp/sample_jp2k.svs'),
    ('57b345d28d777f126827dc28', '/tmp/sample_svs_imamge.svs')
])
def test_tiff_tile_source(file, output):
    """Check whether large_image can return a tile with svs sources."""
    test_url = 'https://data.kitware.com/api/v1/file/{}/download'.format(file)
    urllib.urlretrieve(test_url, output)
    image = large_image.getTileSource(output)
    # Make sure it is the svs tile source
    assert isinstance(image, large_image.tilesource.SVSFileTileSource)
    # Make sure we can get a tile without an exception
    assert type(image.getTile(0, 0, 0)) == str
