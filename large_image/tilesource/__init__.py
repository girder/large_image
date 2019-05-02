# -*- coding: utf-8 -*-

import os
from pkg_resources import iter_entry_points

from .base import TileSource, FileTileSource, TileOutputMimeTypes, \
    TILE_FORMAT_IMAGE, TILE_FORMAT_PIL, TILE_FORMAT_NUMPY
from ..exceptions import TileGeneralException, TileSourceException, TileSourceAssetstoreException
from .. import config
from ..constants import SourcePriority


AvailableTileSources = {}


def loadTileSources(entryPointName='large_image.source', sourceDict=AvailableTileSources):
    """
    Load all tilesources from entrypoints and add them to the
    AvailableTileSources dictionary.

    :param entryPointName: the name of the entry points to load.
    :param sourceDict: a dictionary to populate with the loaded sources.
    """
    for entryPoint in iter_entry_points(entryPointName):
        try:
            sourceClass = entryPoint.load()
            if sourceClass.name and None in sourceClass.extensions:
                sourceDict[entryPoint.name] = sourceClass
                config.getConfig('logprint').debug('Loaded tile source %s' % entryPoint.name)
        except Exception:
            config.getConfig('logprint').exception(
                'Failed to loaded tile source %s' % entryPoint.name)
            pass


def getTileSourceFromDict(availableSources, pathOrUri, *args, **kwargs):
    """
    Get a tile source based on a ordered dictionary of known sources and a path
    name or URI.  Additional parameters are passed to the tile source and can
    be used for properties such as encoding.

    :param availableSources: an ordered dictionary of sources to try.
    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :returns: a tile source instance or and error.
    """
    sourceObj = pathOrUri
    uriWithoutProtocol = pathOrUri.split('://', 1)[-1]
    isLargeImageUri = pathOrUri.startswith('large_image://')
    extensions = [ext.lower() for ext in os.path.basename(uriWithoutProtocol).split('.')[1:]]
    sourceList = []
    for sourceName in availableSources:
        sourceExtensions = availableSources[sourceName].extensions
        priority = sourceExtensions.get(None, SourcePriority.MANUAL)
        for ext in extensions:
            if ext in sourceExtensions:
                priority = min(priority, sourceExtensions[ext])
        if isLargeImageUri and sourceName == uriWithoutProtocol:
            priority = SourcePriority.NAMED
        if priority >= SourcePriority.MANUAL:
            continue
        sourceList.append((priority, sourceName))
    for _priority, sourceName in sorted(sourceList):
        if availableSources[sourceName].canRead(sourceObj, *args, **kwargs):
            return availableSources[sourceName](sourceObj, *args, **kwargs)
    raise TileSourceException('No available tilesource for %s' % pathOrUri)


def getTileSource(*args, **kwargs):
    """
    Get a tilesource using the known sources.  If tile sources have not yet
    been loaded, load them.

    :returns: A tilesource for the passed arguments.
    """
    if not len(AvailableTileSources):
        loadTileSources()
    return getTileSourceFromDict(AvailableTileSources, *args, **kwargs)


__all__ = [
    'TileSource', 'FileTileSource',
    'exceptions', 'TileGeneralException', 'TileSourceException', 'TileSourceAssetstoreException',
    'TileOutputMimeTypes', 'TILE_FORMAT_IMAGE', 'TILE_FORMAT_PIL', 'TILE_FORMAT_NUMPY',
    'AvailableTileSources', 'getTileSource',
]
