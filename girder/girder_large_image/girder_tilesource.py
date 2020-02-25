from girder.constants import AccessType
from girder.exceptions import ValidationException, FilePathException
from girder.models.file import File
from girder.models.item import Item

from large_image.constants import SourcePriority
from large_image.exceptions import TileSourceException, TileSourceAssetstoreException
from large_image import tilesource


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
        super(GirderTileSource, self).__init__(item, *args, **kwargs)
        self.item = item

    @staticmethod
    def getLRUHash(*args, **kwargs):
        return '%s,%s,%s,%s,%s,%s,%s,%s' % (
            args[0]['largeImage']['fileId'],
            args[0]['updated'],
            kwargs.get('encoding', 'JPEG'),
            kwargs.get('jpegQuality', 95),
            kwargs.get('jpegSubsampling', 0),
            kwargs.get('tiffCompression', 'raw'),
            kwargs.get('edge', False),
            kwargs.get('style', None))

    def getState(self):
        return '%s,%s,%s,%s,%s,%s,%s,%s' % (
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
            largeImageFileId = self.item['largeImage']['fileId']
            # The item has adjacent files if there are any files that are not
            # the large image file or an original file it was derived from.
            # This is always the case if there are 3 or more files.
            fileIds = [str(file['_id']) for file in Item().childFiles(self.item, limit=3)]
            knownIds = [str(largeImageFileId)]
            if 'originalId' in self.item['largeImage']:
                knownIds.append(str(self.item['largeImage']['originalId']))
            self._mayHaveAdjacentFiles = (
                len(fileIds) >= 3 or
                fileIds[0] not in knownIds or
                fileIds[-1] not in knownIds)
            if (any(ext in KnownExtensionsWithAdjacentFiles for ext in largeImageFile['exts']) or
                    largeImageFile.get('mimeType') in KnownMimeTypesWithAdjacentFiles):
                self._mayHaveAdjacentFiles = True
        return self._mayHaveAdjacentFiles

    def _getLargeImagePath(self):
        # If self.mayHaveAdjacentFiles is True, we try to use the girder
        # mount where companion files appear next to each other.
        largeImageFileId = self.item['largeImage']['fileId']
        largeImageFile = File().load(largeImageFileId, force=True)
        try:
            largeImagePath = None
            if (self.mayHaveAdjacentFiles(largeImageFile) and
                    hasattr(File(), 'getGirderMountFilePath')):
                try:
                    if (largeImageFile.get('imported') and
                            File().getLocalFilePath(largeImageFile) == largeImageFile['path']):
                        largeImagePath = largeImageFile['path']
                except Exception:
                    pass
                if not largeImagePath:
                    try:
                        largeImagePath = File().getGirderMountFilePath(largeImageFile)
                    except FilePathException:
                        pass
            if not largeImagePath:
                try:
                    largeImagePath = File().getLocalFilePath(largeImageFile)
                except AttributeError as e:
                    raise TileSourceException(
                        'No local file path for this file: %s' % e.args[0])
            return largeImagePath
        except (TileSourceAssetstoreException, FilePathException):
            raise
        except (KeyError, ValidationException, TileSourceException) as e:
            raise TileSourceException(
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


def getGirderTileSourceName(item, file=None, *args, **kwargs):
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
    if not file:
        file = File().load(item['largeImage']['fileId'], force=True)
    extensions = [entry.lower().split()[0] for entry in file['exts']]
    sourceList = []
    for sourceName in AvailableGirderTileSources:
        if not getattr(AvailableGirderTileSources[sourceName], 'girderSource', False):
            continue
        sourceExtensions = AvailableGirderTileSources[sourceName].extensions
        priority = sourceExtensions.get(None, SourcePriority.MANUAL)
        for ext in extensions:
            if ext in sourceExtensions:
                priority = min(priority, sourceExtensions[ext])
        if priority >= SourcePriority.MANUAL:
            continue
        sourceList.append((priority, sourceName))
    for _priority, sourceName in sorted(sourceList):
        if AvailableGirderTileSources[sourceName].canRead(item):
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
        item = Item().load(item, user=kwargs.get('user', None), level=AccessType.READ)
    sourceName = getGirderTileSourceName(item, file, *args, **kwargs)
    if sourceName:
        return AvailableGirderTileSources[sourceName](item, *args, **kwargs)
