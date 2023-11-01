"""Top-level package for Large Image Tasks."""

__author__ = """Kitware Inc"""
__email__ = 'kitware@kitware.com'


from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _importlib_version

from girder_worker import GirderWorkerPluginABC

try:
    __version__ = _importlib_version(__name__)
except PackageNotFoundError:
    # package is not installed
    pass


class LargeImageTasks(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['large_image_tasks.tasks']
