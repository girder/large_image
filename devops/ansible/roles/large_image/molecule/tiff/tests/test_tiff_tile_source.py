"""Test the default libtiff based tile source."""

import os
import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_pip_packages(host):
    """Check python dependencies for tiff tile source."""
    pipPath = '~/.virtualenvs/large_image/bin/pip'
    packages = host.pip_package.get_packages(pip_path=pipPath)
    assert 'libtiff' in packages


def test_large_image_tiff_source(host):
    """Run large image tiff tests."""
    activate = "source /root/.virtualenvs/large_image/bin/activate"
    run = "pytest /request_tile_in_container.py"
    cmd = host.run("bash -c '{} && {}'".format(activate, run))
    assert cmd.rc == 0
