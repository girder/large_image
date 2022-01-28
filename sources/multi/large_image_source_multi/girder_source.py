from girder_large_image.girder_tilesource import GirderTileSource

from . import MultiFileTileSource


class MultiGirderTileSource(MultiFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with files that the multi source can
    read.
    """

    cacheName = 'tilesource'
    name = 'multi'

    _mayHaveAdjacentFiles = True
