#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder.models.model_base import ValidationException
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter


class TileSourceException(Exception):
    pass


class TileSource(object):
    def __init__(self):
        self.tileSize = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None

    def getMetadata(self):
        return {
            'tileSize': self.tileSize,
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': getattr(self, 'tileWidth', self.tileSize),
            'tileHeight': getattr(self, 'tileHeight', self.tileSize),
        }

    def getTile(self, x, y, z):
        raise NotImplementedError()


class GirderTileSource(TileSource):
    def __init__(self, item):
        super(GirderTileSource, self).__init__()
        self.item = item

    def _getLargeImagePath(self):
        try:
            largeImageFileId = self.item['largeImage']
            # Access control checking should already have been done on item, so
            # don't repeat.
            # TODO: is it possible that the file is on a different item, so do
            # we want to repeat the access check?
            largeImageFile = ModelImporter.model('file').load(
                largeImageFileId, force=True)

            # TODO: can we move some of this logic into Girder core?
            assetstore = ModelImporter.model('assetstore').load(
                largeImageFile['assetstoreId'])
            adapter = assetstore_utilities.getAssetstoreAdapter(assetstore)

            if not isinstance(adapter,
                              assetstore_utilities.FilesystemAssetstoreAdapter):
                raise TileSourceException(
                    'Non-filesystem assetstores are not supported')

            largeImagePath = adapter.fullPath(largeImageFile)
            return largeImagePath

        except (KeyError, ValidationException, TileSourceException) as e:
            raise TileSourceException(
                'No large image file in this item: %s' % e.message)
