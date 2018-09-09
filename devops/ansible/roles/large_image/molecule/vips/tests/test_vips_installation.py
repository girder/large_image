"""Test the vips installation."""

import os
import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_system_packages(host):
    """Check if vips is available."""
    vips = host.package("libvips42")
    assert vips.is_installed
