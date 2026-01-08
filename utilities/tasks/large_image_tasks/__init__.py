"""Top-level package for Large Image Tasks."""

__author__ = """Kitware Inc"""
__email__ = 'kitware@kitware.com'

import contextlib
import importlib.metadata

from girder_worker import GirderWorkerPluginABC

with contextlib.suppress(importlib.metadata.PackageNotFoundError):
    __version__ = importlib.metadata.version(__name__)


class LargeImageTasks(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['large_image_tasks.tasks']
