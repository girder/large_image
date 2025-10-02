import inspect
import os
import re

from girder.constants import AccessType
from girder.exceptions import FilePathException, ValidationException
from girder.models.file import File
from girder.models.item import Item
from large_image import config, tilesource
from large_image.constants import SourcePriority
from large_image.exceptions import TileSourceAssetstoreError, TileSourceError

AvailableGirderTileSources = {}
KnownMimeTypes = set()
KnownExtensions = set()
KnownMimeTypesWithAdjacentFiles = set()
KnownExtensionsWithAdjacentFiles = set()


class GirderTileSource(tilesource.FileTileSource):
    girderSource = True

    # If the large image file has one of these extensions or mimetypes, it will
    # always be treated as if there are possible adjacent files.
    extensionsWithAdjacentFiles = set()
    mimeTypesWithAdjacentFiles = set()

    def __init__(self, item, *args, **kwargs):
        """
        Initialize the tile class.  See the base class for other available
        parameters.

        :param item: a Girder item document which contains
            ['largeImage']['fileId'] identifying the Girder file to be used
            for the tile source.
        """
        super().__init__(item, *args, **kwargs)
        self.item = item

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return '%s,%s,%s,%s,%s,%s,%s,__STYLESTART__,%s,__STYLEEND__' % (
            args[0]['largeImage']['fileId'],
            args[0]['updated'],
            kwargs.get('encoding') or config.getConfig('default_encoding'),
            kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0),
            kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False),
            kwargs.get('style'))

    def getState(self):
        if hasattr(self, '_classkey'):
            return self._classkey
        return '%s,%s,%s,%s,%s,%s,%s,__STYLESTART__,%s,__STYLEEND__' % (
            self.item['largeImage']['fileId'],
            self.item['updated'],
            self.encoding,
            self.jpegQuality,
            self.jpegSubsampling,
            self.tiffCompression,
            self.edge,
            self._jsonstyle)

    def mayHaveAdjacentFiles(self, largeImageFile):
        if not hasattr(self, '_mayHaveAdjacentFiles'):
            from .models.image_item import ImageItem

            self._mayHaveAdjacentFiles = ImageItem().mayHaveAdjacentFiles(self.item, largeImageFile)
        return self._mayHaveAdjacentFiles

    def _getLargeImagePath(self):
        # If self.mayHaveAdjacentFiles is True, we try to use the girder
        # mount where companion files appear next to each other.
        largeImageFileId = self.item['largeImage']['fileId']
        largeImageFile = File().load(largeImageFileId, force=True)
        try:
            largeImagePath = None
            mayHaveAdjacent = self.mayHaveAdjacentFiles(largeImageFile)
            if (mayHaveAdjacent and hasattr(File(), 'getGirderMountFilePath')):
                try:
                    if (largeImageFile.get('imported') and
                            File().getLocalFilePath(largeImageFile) == largeImageFile['path']):
                        largeImagePath = largeImageFile['path']
                except Exception:
                    pass
                if not largeImagePath:
                    try:
                        largeImagePath = File().getGirderMountFilePath(
                            largeImageFile,
                            **({'preferFlat': True} if mayHaveAdjacent != 'local' and
                                'preferFlat' in inspect.signature(
                                    File.getGirderMountFilePath).parameters else {}))
                    except FilePathException:
                        pass
            if not largeImagePath:
                try:
                    largeImagePath = File().getLocalFilePath(largeImageFile)
                except AttributeError as e:
                    raise TileSourceError(
                        'No local file path for this file: %s' % e.args[0])
            return largeImagePath
        except (TileSourceAssetstoreError, FilePathException):
            raise
        except (KeyError, ValidationException, TileSourceError) as e:
            raise TileSourceError(
                'No large image file in this item: %s' % e.args[0])


def loadGirderTileSources():
    """
    Load all Girder tilesources from entrypoints and add them to the
    AvailableGiderTileSources dictionary.
    """
    tilesource.loadTileSources('girder_large_image.source', AvailableGirderTileSources)
    for sourceName in AvailableGirderTileSources:
        if getattr(AvailableGirderTileSources[sourceName], 'girderSource', False):
            KnownExtensions.update({
                key for key in AvailableGirderTileSources[sourceName].extensions
                if key is not None})
            KnownExtensionsWithAdjacentFiles.update({
                key for key in AvailableGirderTileSources[sourceName].extensionsWithAdjacentFiles
                if key is not None})
        if getattr(AvailableGirderTileSources[sourceName], 'girderSource', False):
            KnownMimeTypes.update({
                key for key in AvailableGirderTileSources[sourceName].mimeTypes
                if key is not None})
            KnownMimeTypesWithAdjacentFiles.update({
                key for key in AvailableGirderTileSources[sourceName].mimeTypesWithAdjacentFiles
                if key is not None})


def getGirderTileSourceName(item, file=None, *args, **kwargs):  # noqa
    """
    Get a Girder tilesource name using the known sources.  If tile sources have
    not yet been loaded, load them.

    :param item: a Girder item.
    :param file: if specified, the Girder file object to use as the large image
        file; used here only to check extensions.
    :returns: The name of a tilesource that can read the Girder item.
    """
    if not len(AvailableGirderTileSources):
        loadGirderTileSources()
    availableSources = AvailableGirderTileSources
    if not file:
        file = File().load(item['largeImage']['fileId'], force=True)
    mimeType = file['mimeType']
    try:
        localPath = File().getLocalFilePath(file)
    except (FilePathException, AttributeError):
        localPath = None
    extensions = [entry.lower().split()[0] for entry in file['exts'] if entry]
    baseName = os.path.basename(file['name'])
    properties = {}
    if localPath:
        properties['_geospatial_source'] = tilesource.isGeospatial(localPath)
    ignored_names = config.getConfig('all_sources_ignored_names')
    ignoreName = (ignored_names and re.search(
        ignored_names, baseName, flags=re.IGNORECASE))
    sourceList = []
    for sourceName in availableSources:
        if not getattr(availableSources[sourceName], 'girderSource', False):
            continue
        sourceExtensions = availableSources[sourceName].extensions
        priority = sourceExtensions.get(None, SourcePriority.MANUAL)
        fallback = True
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
        if priority >= SourcePriority.MANUAL or (ignoreName and fallback):
            continue
        propertiesClash = any(
            getattr(availableSources[sourceName], k, False) != v
            for k, v in properties.items())
        sourceList.append((propertiesClash, fallback, priority, sourceName))
    for _clash, _fallback, _priority, sourceName in sorted(sourceList):
        if availableSources[sourceName].canRead(item, *args, **kwargs):
            return sourceName


def getGirderTileSource(item, file=None, *args, **kwargs):
    """
    Get a Girder tilesource using the known sources.

    :param item: a Girder item or an item id.
    :param file: if specified, the Girder file object to use as the large image
        file; used here only to check extensions.
    :returns: A girder tilesource for the item.
    """
    if not isinstance(item, dict):
        item = Item().load(item, user=kwargs.get('user'), level=AccessType.READ)
    sourceName = getGirderTileSourceName(item, file, *args, **kwargs)
    if sourceName:
        return AvailableGirderTileSources[sourceName](item, *args, **kwargs)
