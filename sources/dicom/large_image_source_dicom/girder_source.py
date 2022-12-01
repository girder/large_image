from girder_large_image.girder_tilesource import GirderTileSource

from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

from . import DICOMFileTileSource


class DICOMGirderTileSource(DICOMFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with an DICOM file or other files that
    the dicomreader library can read.
    """

    cacheName = 'tilesource'
    name = 'dicom'

    _mayHaveAdjacentFiles = True

    def _getLargeImagePath(self):
        filelist = [
            File().getLocalFilePath(file) for file in Item().childFiles(self.item)
            if self._pathMightBeDicom(file['name'])]
        if len(filelist) > 1:
            return filelist
        filelist = []
        folder = Folder().load(self.item['folderId'], force=True)
        for item in Folder().childItems(folder):
            if len(list(Item().childFiles(item, limit=2))) == 1:
                file = next(Item().childFiles(item, limit=2))
                if self._pathMightBeDicom(file['name']):
                    filelist.append(File().getLocalFilePath(file))
        return filelist
