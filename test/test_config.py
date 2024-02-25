from large_image.config import getConfig, setConfig


def testConfigFunctions():
    assert isinstance(getConfig(), dict)
    setConfig('cache_backend', 'python')
    assert getConfig('cache_backend') == 'python'
    setConfig('cache_backend', 'memcached')
    assert getConfig('cache_backend') == 'memcached'
    setConfig('cache_backend', 'redis')
    assert getConfig('cache_backend') == 'redis'
    setConfig('cache_backend', None)
    assert getConfig('cache_backend') is None
    assert getConfig('unknown', 'python') == 'python'
