from girder_large_image.girder_tilesource import GirderTileSource

from girder.constants import AssetstoreType
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

from . import DICOMFileTileSource
from .assetstore import DICOMWEB_META_KEY


class DICOMGirderTileSource(DICOMFileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with an DICOM file or other files that
    the dicomreader library can read.
    """

    cacheName = 'tilesource'
    name = 'dicom'

    _mayHaveAdjacentFiles = True

    def _getAssetstore(self):
        files = Item().childFiles(self.item, limit=1)
        if not files:
            return None

        assetstore_id = files[0].get('assetstoreId')
        if not assetstore_id:
            return None

        return File()._getAssetstoreModel(files[0]).load(assetstore_id)

    def _getLargeImagePath(self):
        # Look at a single file and see what type of assetstore it came from
        # If it came from a DICOMweb assetstore, then we will use that method.
        assetstore = self._getAssetstore()
        assetstore_type = assetstore['type'] if assetstore else None
        if assetstore_type == getattr(AssetstoreType, 'DICOMWEB', '__undefined__'):
            return self._getDICOMwebLargeImagePath(assetstore)
        else:
            return self._getFilesystemLargeImagePath()

    def _getFilesystemLargeImagePath(self):
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

    def _getDICOMwebLargeImagePath(self, assetstore):
        meta = assetstore[DICOMWEB_META_KEY]
        file = Item().childFiles(self.item, limit=1)[0]
        file_meta = file['dicomweb_meta']

        return {
            'url': meta['url'],
            'study_uid': file_meta['study_uid'],
            'series_uid': file_meta['series_uid'],
            # The following are optional
            'qido_prefix': meta.get('qido_prefix'),
            'wado_prefix': meta.get('wado_prefix'),
            'auth': meta.get('auth'),
        }
