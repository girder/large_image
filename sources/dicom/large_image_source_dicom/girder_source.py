from girder_large_image.girder_tilesource import GirderTileSource

from girder.constants import AssetstoreType
from girder.models.file import File
from girder.models.item import Item
from girder.utility import assetstore_utilities
from large_image.exceptions import TileSourceError

from . import DICOMFileTileSource, _lazyImportPydicom
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
        return self._getFilesystemLargeImagePath()

    def _getFilesystemLargeImagePath(self):
        filelist = [
            File().getLocalFilePath(file) for file in Item().childFiles(self.item)
            if self._pathMightBeDicom(file['name'])]
        if len(filelist) != 1:
            return filelist
        try:
            _lazyImportPydicom().filereader.dcmread(filelist[0], stop_before_pixels=True)
        except Exception as exc:
            msg = f'File cannot be opened via dicom tile source ({exc}).'
            raise TileSourceError(msg)
        filepath = filelist[0]
        for file in Item().collection.aggregate([
            {'$match': {'folderId': self.item['folderId']}},
            {'$lookup': {
                'from': 'file', 'localField': '_id', 'foreignField': 'itemId', 'as': 'files',
            }},
            {'$addFields': {'fileCount': {'$size': '$files'}}},
            {'$match': {'fileCount': 1}},
            {'$unwind': '$files'},
            {'$replaceRoot': {'newRoot': '$files'}},
        ]):
            if self._pathMightBeDicom(File().getLocalFilePath(file), filepath):
                filelist.append(File().getLocalFilePath(file))
        return filelist

    def _getDICOMwebLargeImagePath(self, assetstore):
        meta = assetstore[DICOMWEB_META_KEY]
        item_uids = self.item['dicom_uids']

        adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

        return {
            'url': meta['url'],
            'study_uid': item_uids['study_uid'],
            'series_uid': item_uids['series_uid'],
            # The following are optional
            'qido_prefix': meta.get('qido_prefix'),
            'wado_prefix': meta.get('wado_prefix'),
            'session': adapter.auth_session,
        }

    def _getDicomMetadata(self):
        if self._isDicomWeb:
            # This should have already been saved in the item
            return self.item['dicomweb_meta']

        # Return the parent result. This is a cached method.
        return super()._getDicomMetadata()
