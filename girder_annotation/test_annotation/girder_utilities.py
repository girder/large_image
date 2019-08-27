# -*- coding: utf-8 -*-

import os

from girder.models.folder import Folder
from girder.models.upload import Upload

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
