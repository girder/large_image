# -*- coding: utf-8 -*-

import os
import pytest
import six
import subprocess

from girder import events
from girder.models.folder import Folder
from girder.models.setting import Setting
from girder.models.upload import Upload

from girder_worker.girder_plugin.constants import PluginSettings as WorkerSettings

from test.utilities import externaldata


def namedFolder(user, folderName='Public'):
    return Folder().find({
        'parentId': user['_id'],
        'name': folderName,
    })[0]


def uploadFile(filePath, user, assetstore, folderName='Public', name=None):
    if name is None:
        name = os.path.basename(filePath)
    folder = namedFolder(user, folderName)
    file = Upload().uploadFromFile(
        open(filePath, 'rb'), os.path.getsize(filePath), name,
        parentType='folder', parent=folder, user=user, assetstore=assetstore)
    return file


def uploadExternalFile(hashPath, user, assetstore, folderName='Public', name=None):
    imagePath = externaldata(hashPath)
    return uploadFile(imagePath, user=user, assetstore=assetstore, folderName=folderName, name=name)


def uploadTestFile(fileName, user, assetstore, folderName='Public', name=None):
    testDir = os.path.dirname(os.path.realpath(__file__))
    imagePath = os.path.join(testDir, '..', '..', 'test', 'test_files', fileName)
    return uploadFile(imagePath, user=user, assetstore=assetstore, folderName=folderName, name=None)


def respStatus(resp):
    return int(resp.output_status.split()[0])


def getBody(response, text=True):
    """
    Returns the response body as a text type or binary string.

    :param response: The response object from the server.
    :param text: If true, treat the data as a text string, otherwise, treat
                 as binary.
    """
    data = '' if text else b''

    for chunk in response.body:
        if text and isinstance(chunk, six.binary_type):
            chunk = chunk.decode('utf8')
        elif not text and not isinstance(chunk, six.binary_type):
            chunk = chunk.encode('utf8')
        data += chunk

    return data


@pytest.fixture
def girderWorker(db):
    """
    Run an instance of Girder worker, connected to rabbitmq.  The rabbitmq
    service must be running.
    """
    broker = 'amqp://guest@127.0.0.1'
    Setting().set(WorkerSettings.BROKER, broker)
    Setting().set(WorkerSettings.BACKEND, broker)
    env = os.environ.copy()
    env['C_FORCE_ROOT'] = 'true'
    proc = subprocess.Popen([
        'celery', '-A', 'girder_worker.app', 'worker', '--broker', broker, '--concurrency=1'],
        close_fds=True, env=env)
    yield True
    proc.terminate()
    proc.wait()
    Setting().unset(WorkerSettings.BROKER)
    Setting().unset(WorkerSettings.BACKEND)


def unbindGirderEventsByHandlerName(handlerName):
    for eventName in events._mapping:
        events.unbind(eventName, handlerName)


@pytest.fixture
def unbindLargeImage(db):
    yield True
    unbindGirderEventsByHandlerName('large_image')


@pytest.fixture
def unbindAnnotation(db):
    yield True
    unbindGirderEventsByHandlerName('large_image_annotation')
