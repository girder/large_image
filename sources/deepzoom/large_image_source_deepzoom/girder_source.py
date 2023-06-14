from girder_large_image.girder_tilesource import GirderTileSource

from . import DeepzoomFileTileSource


class DeepzoomGirderTileSource(DeepzoomFileTileSource, GirderTileSource):
    """
    Deepzoom large_image tile source for Girder.

    Provides tile access to Girder items with a Deepzoom xml (dzi) file and
    associated pngs/jpegs in relative folders and items or on the local file
    system.
    """

    cacheName = 'tilesource'
    name = 'deepzoom'

    _mayHaveAdjacentFiles = True
