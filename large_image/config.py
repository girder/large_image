import logging

# Default logger
fallbackLogger = logging.getLogger('large_image')
fallbackLogger.setLevel(logging.INFO)
fallbackLogHandler = logging.StreamHandler()
fallbackLogHandler.setLevel(logging.NOTSET)
fallbackLogger.addHandler(fallbackLogHandler)

ConfigValues = {
    'logger': fallbackLogger,
    'logprint': fallbackLogger,

    'cache_backend': 'python',  # 'python' or 'memcached'
    # 'python' cache can use 1/(val) of the available memory
    'cache_python_memory_portion': 32,
    # cache_memcached_url may be a list
    'cache_memcached_url': '127.0.0.1',
    'cache_memcached_username': None,
    'cache_memcached_password': None,

    'max_small_image_size': 4096,
}


def getConfig(key=None, default=None):
    """
    Get the config dictionary or a value from the cache config settings.

    :param key: if None, return the config dictionary.  Otherwise, return the
        value of the key if it is set or the default value if it is not.
    :param default: a value to return if a key is requested and not set.
    :returns: either the config dictionary or the value of a key.
    """
    if key is None:
        return ConfigValues
    return ConfigValues.get(key, default)


def setConfig(key, value):
    """
    Set a value in the config settings.

    :param key: the key to set.
    :param value: the value to store in the key.
    """
    curConfig = getConfig()
    if curConfig.get(key) is not value:
        curConfig[key] = value
