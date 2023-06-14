import builtins
import math
import os
from xml.etree import ElementTree

import PIL.Image

from large_image.cache_util import LruCacheMetaclass, methodcache
from large_image.constants import TILE_FORMAT_PIL, SourcePriority
from large_image.exceptions import TileSourceError, TileSourceFileNotFoundError
from large_image.tilesource import FileTileSource, etreeToDict


class DeepzoomFileTileSource(FileTileSource, metaclass=LruCacheMetaclass):
    """
    Provides tile access to a Deepzoom xml (dzi) file and associated pngs/jpegs
    in relative folders on the local file system.
    """

    cacheName = 'tilesource'
    name = 'deepzoom'
    extensions = {
        None: SourcePriority.LOW,
        'dzi': SourcePriority.HIGH,
    }
    mimeTypes = {
        None: SourcePriority.FALLBACK,
    }

    def __init__(self, path, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param path: a filesystem path for the tile source.
        """
        super().__init__(path, **kwargs)

        self._largeImagePath = self._getLargeImagePath()
        # Read the root dzi file and check that the expected image files exist
        try:
            with builtins.open(self._largeImagePath) as fptr:
                if fptr.read(1024).strip()[:5] != '<?xml':
                    raise TileSourceError('File cannot be opened via deepzoom reader.')
                fptr.seek(0)
            xml = ElementTree.parse(self._largeImagePath).getroot()
            self._info = etreeToDict(xml)['Image']
        except (ElementTree.ParseError, KeyError, UnicodeDecodeError):
            raise TileSourceError('File cannot be opened via deepzoom reader.')
        except FileNotFoundError:
            if not os.path.isfile(self._largeImagePath):
                raise TileSourceFileNotFoundError(self._largeImagePath) from None
            raise
        # We should now have a dictionary like
        # {'Format': 'png',   # or 'jpeg'
        #  'Overlap': '1',
        #  'Size': {'Height': '41784', 'Width': '44998'},
        #  'TileSize': '254'}
        # and a file structure like
        # <rootname>_files/<level>/<x>_<y>.<format>
        # images will be TileSize+Overlap square; final images will be
        # truncated.  Base level is either 0 or probably 8 (level 0 is a 1x1
        # pixel tile)
        self.sizeX = int(self._info['Size']['Width'])
        self.sizeY = int(self._info['Size']['Height'])
        self.tileWidth = self.tileHeight = int(self._info['TileSize'])
        maxXY = max(self.sizeX, self.sizeY)
        self.levels = int(math.ceil(
            math.log(maxXY / self.tileWidth) / math.log(2))) + 1
        tiledirName = os.path.splitext(os.path.basename(self._largeImagePath))[0] + '_files'
        rootdir = os.path.dirname(self._largeImagePath)
        self._tiledir = os.path.join(rootdir, tiledirName)
        if not os.path.isdir(self._tiledir):
            rootdir = os.path.dirname(rootdir)
            self._tiledir = os.path.join(rootdir, tiledirName)
        zeroname = '0_0.%s' % self._info['Format']
        self._nested = os.path.isdir(os.path.join(self._tiledir, '0', zeroname))
        zeroimg = PIL.Image.open(
            os.path.join(self._tiledir, '0', zeroname) if not self._nested else
            os.path.join(self._tiledir, '0', zeroname, zeroname))
        if zeroimg.size == (1, 1):
            self._baselevel = int(
                math.ceil(math.log(maxXY) / math.log(2)) -
                math.ceil(math.log(maxXY / self.tileWidth) / math.log(2)))
        else:
            self._baselevel = 0

    def getInternalMetadata(self, **kwargs):
        """
        Return additional known metadata about the tile source.  Data returned
        from this method is not guaranteed to be in any particular format or
        have specific values.

        :returns: a dictionary of data or None.
        """
        result = {}
        result['deepzoom'] = self._info
        result['baselevel'] = self._baselevel
        return result

    @methodcache()
    def getTile(self, x, y, z, pilImageAllowed=False, numpyAllowed=False, **kwargs):
        self._xyzInRange(x, y, z)
        tilename = '%d_%d.%s' % (x, y, self._info['Format'])
        tilepath = os.path.join(self._tiledir, '%d' % (self._baselevel + z), tilename)
        if self._nested:
            tilepath = os.path.join(tilepath, tilename)
        tile = PIL.Image.open(tilepath)
        overlap = int(self._info.get('Overlap', 0))
        tile = tile.crop((
            overlap if x else 0, overlap if y else 0,
            self.tileWidth + (overlap if x else 0),
            self.tileHeight + (overlap if y else 0)))
        return self._outputTile(tile, TILE_FORMAT_PIL, x, y, z,
                                pilImageAllowed, numpyAllowed, **kwargs)


def open(*args, **kwargs):
    """Create an instance of the module class."""
    return DeepzoomFileTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """Check if an input can be read by the module class."""
    return DeepzoomFileTileSource.canRead(*args, **kwargs)
