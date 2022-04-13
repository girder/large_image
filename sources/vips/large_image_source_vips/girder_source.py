# -*- coding: utf-8 -*-

from girder_large_image.girder_tilesource import GirderTileSource

from . import VipsFileTileSource


class VipsGirderTileSource(VipsFileTileSource, GirderTileSource):
    """
    Vips large_image tile source for Girder.
    """

    cacheName = 'tilesource'
    name = 'vips'

    # vips uses extensions and adjacent files for some formats
    _mayHaveAdjacentFiles = True
