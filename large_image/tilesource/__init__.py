import os

from pkg_resources import iter_entry_points

from .. import config
from ..constants import SourcePriority
from ..exceptions import (TileGeneralError, TileGeneralException,
                          TileSourceAssetstoreError,
                          TileSourceAssetstoreException, TileSourceError,
                          TileSourceException, TileSourceFileNotFoundError)
from .base import (TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL,
                   FileTileSource, TileOutputMimeTypes, TileSource,
                   dictToEtree, etreeToDict, nearPowerOfTwo)

AvailableTileSources = {}


def isGeospatial(path):
    """
    Check if a path is likely to be a geospatial file.

    :param path: The path to the file
    :returns: True if geospatial.
    """
    try:
        from osgeo import gdal, gdalconst
    except ImportError:
        # TODO: log a warning
        return False
    try:
        ds = gdal.Open(str(path), gdalconst.GA_ReadOnly)
    except Exception:
        return False
    if ds:
        if ds.GetGCPs() and ds.GetGCPProjection():
            return True
        if ds.GetProjection():
            return True
        if ds.GetGeoTransform(can_return_null=True):
            return True
        if ds.GetDriver().ShortName in {'NITF', 'netCDF'}:
            return True
    return False


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


def getSourceNameFromDict(availableSources, pathOrUri, *args, **kwargs):
    """
    Get a tile source based on a ordered dictionary of known sources and a path
    name or URI.  Additional parameters are passed to the tile source and can
    be used for properties such as encoding.

    :param availableSources: an ordered dictionary of sources to try.
    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :returns: the name of a tile source that can read the input, or None if
        there is no such source.
    """
    uriWithoutProtocol = str(pathOrUri).split('://', 1)[-1]
    isLargeImageUri = str(pathOrUri).startswith('large_image://')
    extensions = [ext.lower() for ext in os.path.basename(uriWithoutProtocol).split('.')[1:]]
    properties = {
        'geospatial': isGeospatial(pathOrUri),
    }
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
        propertiesClash = any(
            getattr(availableSources[sourceName], k, False) != v
            for k, v in properties.items())
        sourceList.append((propertiesClash, priority, sourceName))
    for _clash, _priority, sourceName in sorted(sourceList):
        if availableSources[sourceName].canRead(pathOrUri, *args, **kwargs):
            return sourceName


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
    sourceName = getSourceNameFromDict(availableSources, pathOrUri, *args, **kwargs)
    if sourceName:
        return availableSources[sourceName](pathOrUri, *args, **kwargs)
    if not os.path.exists(pathOrUri) and '://' not in pathOrUri:
        raise TileSourceFileNotFoundError(pathOrUri)
    raise TileSourceError('No available tilesource for %s' % pathOrUri)


def getTileSource(*args, **kwargs):
    """
    Get a tilesource using the known sources.  If tile sources have not yet
    been loaded, load them.

    :returns: A tilesource for the passed arguments.
    """
    if not len(AvailableTileSources):
        loadTileSources()
    return getTileSourceFromDict(AvailableTileSources, *args, **kwargs)


def open(*args, **kwargs):
    """
    Alternate name of getTileSource.

    Get a tilesource using the known sources.  If tile sources have not yet
    been loaded, load them.

    :returns: A tilesource for the passed arguments.
    """
    return getTileSource(*args, **kwargs)


def canRead(*args, **kwargs):
    """
    Check if large_image can read a path or uri.

    :returns: True if any appropriate source reports it can read the path or
        uri.
    """
    if not len(AvailableTileSources):
        loadTileSources()
    if getSourceNameFromDict(AvailableTileSources, *args, **kwargs):
        return True
    return False


__all__ = [
    'TileSource', 'FileTileSource',
    'exceptions', 'TileGeneralError', 'TileSourceError',
    'TileSourceAssetstoreError', 'TileSourceFileNotFoundError',
    'TileGeneralException', 'TileSourceException', 'TileSourceAssetstoreException',
    'TileOutputMimeTypes', 'TILE_FORMAT_IMAGE', 'TILE_FORMAT_PIL', 'TILE_FORMAT_NUMPY',
    'AvailableTileSources', 'getTileSource', 'canRead', 'getSourceNameFromDict', 'nearPowerOfTwo',
    'etreeToDict', 'dictToEtree',
]
