import os

import pytest

import large_image

try:
    import ipyleaflet  # noqa: F401
    import IPython  # noqa: F401
    import tornado  # noqa: F401
except ImportError:  # pragma: no cover
    pytest.skip(reason='Requires ipyleaflet, tornado, IPython', allow_module_level=True)


def testJupyterIpyleafletGeospatial():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'rgb_geotiff.tiff')
    source = large_image.open(imagePath, projection='EPSG:3857')
    assert source.geospatial and source.projection
    source._ipython_display_()  # smoke test
    # Run twice to make sure launched only once
    port = source._jupyter_server_manager.port
    source._ipython_display_()  # smoke test
    assert source._jupyter_server_manager.port == port


def testJupyterIpyleaflet():
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, 'test_files', 'test_orient0.tif')
    source = large_image.open(imagePath)
    source._ipython_display_()  # smoke test
    # port = source._jupyter_server_manager.port
    # TODO: set up event loop properly for server
    # r = requests.get(f'http://localhost:{port}/tile?z=0&x=0&y=0&encoding=png')
    # r.raise_for_status()
    # assert r.content
    # r = requests.get(f'http://localhost:{port}/metadata')
    # r.raise_for_status()
    # assert r.content
