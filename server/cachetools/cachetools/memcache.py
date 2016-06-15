from cachetools import Cache, hashkey
import pylibmc


def strhash(*args, **kwargs):
    return str(hashkey(*args, **kwargs))


class MemCache(Cache):
    """subclass of cache that uses a memcached store """
    def __init__(self, missing=None, getsizeof=None):
        super(MemCache, self).__init__(0, missing, getsizeof)
        # name mangling to override "private variable" __data in cache
        # pylibmc used to connect to memcached client
        self._Cache__data = pylibmc.Client(["127.0.0.1"], binary=True,
                                         behaviors={"tcp_nodelay": True,
                                                    "ketama": True})
        self._Cache__data.flush_all()
        print ("initializing memcache client")
        print(self._Cache__data.get_stats())

    def __repr__(self):
        return "Memcache doesnt list its keys"

    def __iter__(self):
        print('return fake iter')
        return None

    def __len__(self):
        print('return fake length')
        return -1

    def __contains__(self, key):
        print('cache contains key')
        return None

    def __delitem__(self, key):

        del self._Cache__data[key]

    def __getitem__(self, key):
        try:
            return self._Cache__data[key]
        except KeyError:
            return self.__missing__(key)

    def __setitem__(self, key, value):
        try:
            self._Cache__data[key] = value
        except KeyError:
            pass
