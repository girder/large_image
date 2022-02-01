import copy

from girder_large_image.girder_tilesource import GirderTileSource
from girder_large_image.models.image_item import ImageItem

from large_image.exceptions import TileSourceFileNotFoundError

from . import MultiFileTileSource


class MultiGirderTileSource(MultiFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with files that the multi source can
    read.
    """

    cacheName = 'tilesource'
    name = 'multi'

    _mayHaveAdjacentFiles = True

    def _resolveSourcePath(self, sources, source):
        try:
            super()._resolveSourcePath(sources, source)
        except TileSourceFileNotFoundError:
            prefix = 'girder://'
            potentialId = source['path']
            if potentialId.startswith(prefix):
                potentialId = potentialId[len(prefix):]
            if '://' not in potentialId:
                try:
                    item = ImageItem().load(potentialId, force=True)
                    ts = ImageItem().tileSource(item)
                    source = copy.deepcopy(source)
                    source['path'] = ts._getLargeImagePath()
                    source['sourceName'] = item['largeImage']['sourceName']
                    sources.append(source)
                    return
                except Exception:
                    pass
            raise
