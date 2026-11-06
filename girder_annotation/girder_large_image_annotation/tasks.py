from girder_worker import GirderWorkerPluginABC


class LargeImageAnnotationWorkerPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        return [
            'girder_large_image_annotation.handlers',
        ]
