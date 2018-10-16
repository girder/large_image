# -*- coding: utf-8 -*-

"""Top-level package for Large Image Tasks."""

__author__ = """Kitware Inc"""
__email__ = 'kitware@kitware.com'
__version__ = '0.2.0'


from girder_worker import GirderWorkerPluginABC


class LargeImageTasks(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['large_image_tasks.tasks']
