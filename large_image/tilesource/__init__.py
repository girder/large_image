import contextlib
import os
import re
import sys
import uuid
from importlib.metadata import entry_points
from pathlib import PosixPath
from typing import Any, cast

from .. import config
from ..constants import NEW_IMAGE_PATH_FLAG, SourcePriority
from ..exceptions import (TileGeneralError, TileGeneralException,
                          TileSourceAssetstoreError,
                          TileSourceAssetstoreException, TileSourceError,
                          TileSourceException, TileSourceFileNotFoundError)
from .base import (TILE_FORMAT_IMAGE, TILE_FORMAT_NUMPY, TILE_FORMAT_PIL,
                   FileTileSource, TileOutputMimeTypes, TileSource,
                   dictToEtree, etreeToDict, nearPowerOfTwo)

AvailableTileSources: dict[str, type[FileTileSource]] = {}


def isGeospatial(
        path: str | PosixPath,
        availableSources: dict[str, type[FileTileSource]] | None = None) -> bool:
    """
    Check if a path is likely to be a geospatial file.

    :param path: The path to the file
    :param availableSources: an optional ordered dictionary of sources to use
        for potentially checking the path.
    :returns: True if geospatial.
    """
    if availableSources is None:
        if not len(AvailableTileSources):
            loadTileSources()
        availableSources = AvailableTileSources
    for sourceName in sorted(availableSources):
        source = availableSources[sourceName]
        if hasattr(source, 'isGeospatial'):
            result = None
            with contextlib.suppress(Exception):
                result = source.isGeospatial(path)
            if result in (True, False):
                return result
    return False


def loadTileSources(entryPointName: str = 'large_image.source',
                    sourceDict: dict[str, type[FileTileSource]] = AvailableTileSources) -> None:
    """
    Load all tilesources from entrypoints and add them to the
    AvailableTileSources dictionary.

    :param entryPointName: the name of the entry points to load.
    :param sourceDict: a dictionary to populate with the loaded sources.
    """
    epoints = entry_points()
    epointList = epoints.select(group=entryPointName)
    for entryPoint in epointList:
        try:
            sourceClass = entryPoint.load()
            if sourceClass.name and None in sourceClass.extensions:
                sourceDict[entryPoint.name] = sourceClass
                config.getLogger('logprint').debug('Loaded tile source %s' % entryPoint.name)
        except Exception:
            config.getLogger('logprint').exception(
                'Failed to loaded tile source %s' % entryPoint.name)


def getSortedSourceList(
    availableSources: dict[str, type[FileTileSource]], pathOrUri: str | PosixPath,
    mimeType: str | None = None, *args, **kwargs,
) -> list[tuple[bool, bool, SourcePriority, str]]:
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
        '_geospatial_source': isGeospatial(pathOrUri, availableSources),
    }
    isNew = str(pathOrUri).startswith(NEW_IMAGE_PATH_FLAG)
    ignored_names = config.getConfig('all_sources_ignored_names')
    ignoreName = (ignored_names and re.search(
        ignored_names, os.path.basename(str(pathOrUri)), flags=re.IGNORECASE))
    sourceList = []
    for sourceName in availableSources:
        sourceExtensions = availableSources[sourceName].extensions
        priority = sourceExtensions.get(None, SourcePriority.MANUAL)
        fallback = True
        if isNew and getattr(availableSources[sourceName], 'newPriority', None) is not None:
            priority = min(priority, cast(SourcePriority, availableSources[sourceName].newPriority))
        if (mimeType and getattr(availableSources[sourceName], 'mimeTypes', None) and
                mimeType in availableSources[sourceName].mimeTypes):
            priority = min(priority, availableSources[sourceName].mimeTypes[mimeType])
            fallback = False
        for regex in getattr(availableSources[sourceName], 'nameMatches', {}):
            if re.match(regex, baseName):
                priority = min(priority, availableSources[sourceName].nameMatches[regex])
                fallback = False
        for ext in extensions:
            if ext in sourceExtensions:
                priority = min(priority, sourceExtensions[ext])
                fallback = False
        if isLargeImageUri and sourceName == uriWithoutProtocol:
            priority = SourcePriority.NAMED
        if priority >= SourcePriority.MANUAL or (ignoreName and fallback):
            continue
        propertiesClash = any(
            getattr(availableSources[sourceName], k, False) != v
            for k, v in properties.items())
        sourceList.append((propertiesClash, fallback, priority, sourceName))
    return sourceList


def getSourceNameFromDict(
        availableSources: dict[str, type[FileTileSource]], pathOrUri: str | PosixPath,
        mimeType: str | None = None, *args, **kwargs) -> str | None:
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
    for entry in sorted(sourceList):
        sourceName = entry[-1]
        if availableSources[sourceName].canRead(pathOrUri, *args, **kwargs):
            return sourceName
    return None


def getTileSourceFromDict(
        availableSources: dict[str, type[FileTileSource]], pathOrUri: str | PosixPath,
        *args, **kwargs) -> FileTileSource:
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
    if not os.path.exists(pathOrUri) and '://' not in str(pathOrUri):
        raise TileSourceFileNotFoundError(pathOrUri)
    raise TileSourceError('No available tilesource for %s' % pathOrUri)


def getTileSource(*args, **kwargs) -> FileTileSource:
    """
    Get a tilesource using the known sources.  If tile sources have not yet
    been loaded, load them.

    :returns: A tilesource for the passed arguments.
    """
    if not len(AvailableTileSources):
        loadTileSources()
    return getTileSourceFromDict(AvailableTileSources, *args, **kwargs)


def open(*args, **kwargs) -> FileTileSource:
    """
    Alternate name of getTileSource.

    Get a tilesource using the known sources.  If tile sources have not yet
    been loaded, load them.

    :returns: A tilesource for the passed arguments.
    """
    return getTileSource(*args, **kwargs)


def canRead(*args, **kwargs) -> bool:
    """
    Check if large_image can read a path or uri.

    If there is no intention to open the image immediately, conisder adding
    `noCache=True` to the kwargs to avoid cycling the cache unnecessarily.

    :returns: True if any appropriate source reports it can read the path or
        uri.
    """
    if not len(AvailableTileSources):
        loadTileSources()
    if getSourceNameFromDict(AvailableTileSources, *args, **kwargs):
        return True
    return False


def canReadList(
        pathOrUri: str | PosixPath, mimeType: str | None = None,
        availableSources: dict[str, type[FileTileSource]] | None = None,
        *args, **kwargs) -> list[tuple[str, bool]]:
    """
    Check if large_image can read a path or uri via each source.

    If there is no intention to open the image immediately, conisder adding
    `noCache=True` to the kwargs to avoid cycling the cache unnecessarily.

    :param pathOrUri: either a file path or a fixed source via
        large_image://<source>.
    :param mimeType: the mimetype of the file, if known.
    :param availableSources: an ordered dictionary of sources to try.  If None,
        use the primary list of sources.
    :returns: A list of tuples of (source name, canRead).
    """
    if availableSources is None and not len(AvailableTileSources):
        loadTileSources()
    sourceList = getSortedSourceList(
        availableSources or AvailableTileSources, pathOrUri, mimeType, *args, **kwargs)
    result = []
    for entry in sorted(sourceList):
        sourceName = entry[-1]
        result.append((sourceName, (availableSources or AvailableTileSources)[sourceName].canRead(
            pathOrUri, *args, **kwargs)))
    return result


def new(*args, **kwargs) -> TileSource:
    """
    Create a new image.

    TODO: add specific arguments to choose a source based on criteria.
    """
    return getTileSource(NEW_IMAGE_PATH_FLAG + str(uuid.uuid4()), *args, **kwargs)


def listSources(
    availableSources: dict[str, type[FileTileSource]] | None = None,
) -> dict[str, dict[str, Any]]:
    """
    Get a dictionary with all sources, all known extensions, and all known
    mimetypes.

    :param availableSources: an ordered dictionary of sources to try.
    :returns: a dictionary with sources, extensions, and mimeTypes.  The
        extensions and mimeTypes list their matching sources in priority order.
        The sources list their supported extensions and mimeTypes with their
        priority.
    """
    if availableSources is None:
        if not len(AvailableTileSources):
            loadTileSources()
        availableSources = AvailableTileSources
    results: dict[str, dict[str, Any]] = {'sources': {}, 'extensions': {}, 'mimeTypes': {}}
    for key, source in availableSources.items():
        if hasattr(source, 'addKnownExtensions'):
            source.addKnownExtensions()
        if hasattr(source, 'addKnownMimetypes'):
            source.addKnownMimetypes()
        results['sources'][key] = {
            'extensions': {
                k or 'default': v for k, v in source.extensions.items()},
            'mimeTypes': {
                k or 'default': v for k, v in source.mimeTypes.items()},
        }
        for k, v in source.extensions.items():
            if k is not None:
                results['extensions'].setdefault(k, [])
                results['extensions'][k].append((v, key))
                results['extensions'][k].sort()
        for k, v in source.mimeTypes.items():
            if k is not None:
                results['mimeTypes'].setdefault(k, [])
                results['mimeTypes'][k].append((v, key))
                results['mimeTypes'][k].sort()
        for cls in source.__mro__:
            try:
                if sys.modules[cls.__module__].__version__:
                    results['sources'][key]['version'] = sys.modules[cls.__module__].__version__
                    break
            except Exception:
                pass
    return results


def listExtensions(
        availableSources: dict[str, type[FileTileSource]] | None = None) -> list[str]:
    """
    Get a list of all known extensions.

    :param availableSources: an ordered dictionary of sources to try.
    :returns: a list of extensions (without leading dots).
    """
    return sorted(listSources(availableSources)['extensions'].keys())


def listMimeTypes(
        availableSources: dict[str, type[FileTileSource]] | None = None) -> list[str]:
    """
    Get a list of all known mime types.

    :param availableSources: an ordered dictionary of sources to try.
    :returns: a list of mime types.
    """
    return sorted(listSources(availableSources)['mimeTypes'].keys())


__all__ = [
    'TileSource', 'FileTileSource',
    'TileGeneralError', 'TileSourceError',
    'TileSourceAssetstoreError', 'TileSourceFileNotFoundError',
    'TileGeneralException', 'TileSourceException', 'TileSourceAssetstoreException',
    'TileOutputMimeTypes', 'TILE_FORMAT_IMAGE', 'TILE_FORMAT_PIL', 'TILE_FORMAT_NUMPY',
    'AvailableTileSources', 'getTileSource', 'getSourceNameFromDict', 'nearPowerOfTwo',
    'canRead', 'open', 'new',
    'listSources', 'listExtensions', 'listMimeTypes',
    'etreeToDict', 'dictToEtree',
]
