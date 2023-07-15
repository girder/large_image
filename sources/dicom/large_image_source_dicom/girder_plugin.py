from girder.plugin import GirderPlugin

from . import assetstore


class DICOMwebPlugin(GirderPlugin):
    DISPLAY_NAME = 'DICOMweb Plugin'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        assetstore.load(info)
