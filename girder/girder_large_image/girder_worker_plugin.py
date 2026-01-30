from girder_worker import GirderWorkerPluginABC

from girder import events

from .handlers import (checkForLargeImageFiles, handleCopyItem, handleFileSave,
                       handleRemoveFile, prepareCopyItem, removeThumbnails)
from .loadmodelcache import invalidateLoadModelCache


class LargeImageWorkerPlugin(GirderWorkerPluginABC):
    """
    This class is needed to handle events in the local girder worker, such as
    assetstore imports and folder removals.
    """

    def __init__(self, app, *args, **kwargs):
        events.bind('model.folder.save.after', 'large_image', invalidateLoadModelCache)
        events.bind('model.item.remove', 'large_image', invalidateLoadModelCache)
        events.bind('model.item.copy.prepare', 'large_image', prepareCopyItem)
        events.bind('model.item.copy.after', 'large_image', handleCopyItem)
        events.bind('model.file.save.after', 'large_image', checkForLargeImageFiles)
        events.bind('model.item.remove', 'large_image.removeThumbnails', removeThumbnails)
        events.bind('model.file.remove', 'large_image', handleRemoveFile)
        events.bind('model.file.save', 'large_image', handleFileSave)
