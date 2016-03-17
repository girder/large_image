#!/usr/bin/env python
# -*- coding: utf-8 -*-

#############################################################################
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
#############################################################################

import math

from girder import logger
from girder.models.model_base import ValidationException
from girder.utility import assetstore_utilities
from girder.utility.model_importer import ModelImporter
from six import BytesIO

from ..models.base import TileGeneralException

# Not having PIL disables thumbnail creation, but isn't fatal
try:
    import PIL
    if int(PIL.PILLOW_VERSION.split('.')[0]) < 3:
        logger.warning('Error: Pillow v3.0 or later is required')
        PIL = None
except ImportError:
    logger.warning('Error: Could not import PIL')
    PIL = None


class TileSourceException(TileGeneralException):
    pass


class TileSourceAssetstoreException(TileSourceException):
    pass


class TileSource(object):
    def __init__(self):
        self.tileWidth = None
        self.tileHeight = None
        self.levels = None
        self.sizeX = None
        self.sizeY = None

    def getMetadata(self):
        return {
            'levels': self.levels,
            'sizeX': self.sizeX,
            'sizeY': self.sizeY,
            'tileWidth': self.tileWidth,
            'tileHeight': self.tileHeight,
        }

    def getTile(self, x, y, z):
        raise NotImplementedError()

    def getTileMimeType(self):
        return 'image/jpeg'

    def getThumbnail(self, width=None, height=None, **kwargs):
        mimeTypes = {
            'JPEG': 'image/jpeg',
            'PNG': 'image/png'
        }
        encoding = kwargs.get('encoding', 'JPEG')
        if encoding not in mimeTypes:
            raise ValueError('Invalid encoding "%s"' % encoding)
        if ((width is not None and width < 2) or
                (height is not None and height < 2)):
            raise ValueError('Invalid width or height.  Minimum value is 2.')

        metadata = self.getMetadata()
        tileData = self.getTile(0, 0, 0)
        image = PIL.Image.open(BytesIO(tileData))
        imageWidth = int(math.floor(
            metadata['sizeX'] * 2 ** -(metadata['levels'] - 1)))
        imageHeight = int(math.floor(
            metadata['sizeY'] * 2 ** -(metadata['levels'] - 1)))
        image = image.crop((0, 0, imageWidth, imageHeight))

        # If we wanted to return a default thumbnail of the level 0 tile,
        # disable this conditional.
        if width is None and height is None:
            width = height = 256

        # Constrain the maximum size if both width and height weren't
        # specified, in case the image is very short or very narrow.
        if height and not width:
            width = height * 16
        if width and not height:
            height = width * 16

        if width and height:
            if width * imageHeight > height * imageWidth:
                width = max(1, int(imageWidth * height / imageHeight))
            else:
                height = max(1, int(imageHeight * width / imageWidth))

            image = image.resize(
                (width, height),
                PIL.Image.BICUBIC if width > imageWidth else PIL.Image.LANCZOS)

        output = BytesIO()
        image.save(output, encoding, quality=kwargs.get('jpegQuality', 95),
                   subsampling=kwargs.get('jpegSubsampling', 0))
        tileData = output.getvalue()
        return tileData, mimeTypes[encoding]


class GirderTileSource(TileSource):
    def __init__(self, item, **kwargs):
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
                raise TileSourceAssetstoreException(
                    'Non-filesystem assetstores are not supported')

            largeImagePath = adapter.fullPath(largeImageFile)
            return largeImagePath

        except TileSourceAssetstoreException:
            raise
        except (KeyError, ValidationException, TileSourceException) as e:
            raise TileSourceException(
                'No large image file in this item: %s' % e.message)
