from girder_large_image.girder_tilesource import GirderTileSource

from . import ZarrFileTileSource


class ZarrGirderTileSource(ZarrFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with files that OME Zarr can read.
    """

    cacheName = 'tilesource'
    name = 'zarr'

    _mayHaveAdjacentFiles = True
