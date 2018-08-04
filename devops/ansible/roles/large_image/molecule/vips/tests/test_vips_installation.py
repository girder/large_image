"""Test the default libtiff based tile source."""

import os
import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_pip_packages(host):
    """Check if vips is available."""
    vips = host.package("libvips-dev")
    assert vips.is_installed
