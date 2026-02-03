import sys

def _register(name, fn):
    fn.__module__ = __name__
    fn.__qualname__ = name
    setattr(sys.modules[__name__], name, fn)