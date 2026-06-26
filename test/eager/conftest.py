import pytest


@pytest.fixture(autouse=True)
def python_tile_cache_for_eager_workers():
    import large_image.cache_util.cache as large_image_cache
    from large_image import config

    old_backend = config.getConfig('cache_backend')
    old_tile_cache = large_image_cache._tileCache
    old_tile_lock = large_image_cache._tileLock
    config.setConfig('cache_backend', 'python')
    large_image_cache._tileCache = None
    large_image_cache._tileLock = None
    try:
        yield
    finally:
        large_image_cache._tileCache = old_tile_cache
        large_image_cache._tileLock = old_tile_lock
        config.setConfig('cache_backend', old_backend)


DATASTORE_SVS_FILENAME = 'TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs'


@pytest.fixture(scope='module')
def datastore_svs_path():
    pytest.importorskip('pooch', reason='eager datastore fixtures require pooch')
    from test.datastore import datastore

    return datastore.fetch(DATASTORE_SVS_FILENAME)


@pytest.fixture
def datastore_svs_source(datastore_svs_path):
    pytest.importorskip('pykdtree.kdtree', reason='eager read planning requires pykdtree')
    import large_image

    return large_image.open(datastore_svs_path)
