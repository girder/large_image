"""Top-level package for Large Image Tasks."""

__author__ = """Kitware Inc"""
__email__ = 'kitware@kitware.com'


from girder_worker import GirderWorkerPluginABC
from pkg_resources import DistributionNotFound, get_distribution


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


class LargeImageTasks(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['large_image_tasks.tasks']
