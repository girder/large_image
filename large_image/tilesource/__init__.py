import os
import re
import uuid

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points

from .. import config
from ..constants import NEW_IMAGE_PATH_FLAG, SourcePriority
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
    if not len(AvailableTileSources):
        loadTileSources()
    for sourceName in sorted(AvailableTileSources):
        source = AvailableTileSources[sourceName]
        if hasattr(source, 'isGeospatial'):
            result = None
            try:
                result = source.isGeospatial(path)
            except Exception:
                pass
            if result in (True, False):
                return result
    return False


def loadTileSources(entryPointName='large_image.source', sourceDict=AvailableTileSources):
    """
    Load all tilesources from entrypoints and add them to the
    AvailableTileSources dictionary.

    :param entryPointName: the name of the entry points to load.
    :param sourceDict: a dictionary to populate with the loaded sources.
    """
    epoints = entry_points()
    # Python 3.10 uses select and deprecates dictionary interface
    epointList = epoints.select(group=entryPointName) if hasattr(
        epoints, 'select') else epoints.get(entryPointName, [])
    for entryPoint in epointList:
        try:
            sourceClass = entryPoint.load()
            if sourceClass.name and None in sourceClass.extensions:
                sourceDict[entryPoint.name] = sourceClass
                config.getConfig('logprint').debug('Loaded tile source %s' % entryPoint.name)
        except Exception:
            config.getConfig('logprint').exception(
                'Failed to loaded tile source %s' % entryPoint.name)


def getSortedSourceList(availableSources, pathOrUri, mimeType=None, *args, **kwargs):
    """
    Get an ordered list of sources where earlier sources are more likely to
    work for a specified path or uri.

    :param availableSources: an ordered dictionary of sources to try.
    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :param mimeType: the mimetype of the file, if known.
    :returns: a list of (clash, fallback, priority, sourcename) for sources
        where sourcename is a key in availableSources.
    """
    uriWithoutProtocol = str(pathOrUri).split('://', 1)[-1]
    isLargeImageUri = str(pathOrUri).startswith('large_image://')
    baseName = os.path.basename(uriWithoutProtocol)
    extensions = [ext.lower() for ext in baseName.split('.')[1:]]
    properties = {
        '_geospatial_source': isGeospatial(pathOrUri),
    }
    sourceList = []
    for sourceName in availableSources:
        sourceExtensions = availableSources[sourceName].extensions
        priority = sourceExtensions.get(None, SourcePriority.MANUAL)
        fallback = True
        if (mimeType and getattr(availableSources[sourceName], 'mimeTypes', None) and
                mimeType in availableSources[sourceName].mimeTypes):
            fallback = False
            priority = min(priority, availableSources[sourceName].mimeTypes[mimeType])
        for regex in getattr(availableSources[sourceName], 'nameMatches', {}):
            if re.match(regex, baseName):
                fallback = False
                priority = min(priority, availableSources[sourceName].nameMatches[regex])
        for ext in extensions:
            if ext in sourceExtensions:
                fallback = False
                priority = min(priority, sourceExtensions[ext])
        if isLargeImageUri and sourceName == uriWithoutProtocol:
            priority = SourcePriority.NAMED
        if priority >= SourcePriority.MANUAL:
            continue
        propertiesClash = any(
            getattr(availableSources[sourceName], k, False) != v
            for k, v in properties.items())
        sourceList.append((propertiesClash, fallback, priority, sourceName))
    return sourceList


def getSourceNameFromDict(availableSources, pathOrUri, mimeType=None, *args, **kwargs):
    """
    Get a tile source based on a ordered dictionary of known sources and a path
    name or URI.  Additional parameters are passed to the tile source and can
    be used for properties such as encoding.

    :param availableSources: an ordered dictionary of sources to try.
    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :param mimeType: the mimetype of the file, if known.
    :returns: the name of a tile source that can read the input, or None if
        there is no such source.
    """
    sourceList = getSortedSourceList(availableSources, pathOrUri, mimeType, *args, **kwargs)
    for _clash, _fallback, _priority, sourceName in sorted(sourceList):
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


def canReadList(pathOrUri, mimeType=None, *args, **kwargs):
    """
    Check if large_image can read a path or uri via each source.

    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :param mimeType: the mimetype of the file, if known.
    :returns: A list of tuples of (source name, canRead).
    """
    if not len(AvailableTileSources):
        loadTileSources()
    sourceList = getSortedSourceList(
        AvailableTileSources, pathOrUri, mimeType, *args, **kwargs)
    result = []
    for _clash, _fallback, _priority, sourceName in sorted(sourceList):
        result.append((sourceName, AvailableTileSources[sourceName].canRead(
            pathOrUri, *args, **kwargs)))
    return result


def new(*args, **kwargs):
    """
    Create a new image.

    TODO: add specific arguments to choose a source based on criteria.
    """
    return getTileSource(NEW_IMAGE_PATH_FLAG + str(uuid.uuid4()), *args, **kwargs)


__all__ = [
    'TileSource', 'FileTileSource',
    'exceptions', 'TileGeneralError', 'TileSourceError',
    'TileSourceAssetstoreError', 'TileSourceFileNotFoundError',
    'TileGeneralException', 'TileSourceException', 'TileSourceAssetstoreException',
    'TileOutputMimeTypes', 'TILE_FORMAT_IMAGE', 'TILE_FORMAT_PIL', 'TILE_FORMAT_NUMPY',
    'AvailableTileSources', 'getTileSource', 'getSourceNameFromDict', 'nearPowerOfTwo',
    'canRead', 'open', 'new',
    'etreeToDict', 'dictToEtree',
]
