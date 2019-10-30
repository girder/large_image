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

import collections
import functools
from .base import TileSource, getTileSourceFromDict, TileSourceException, \
    TileSourceAssetstoreException, TileOutputMimeTypes, TILE_FORMAT_IMAGE, \
    TILE_FORMAT_PIL, TILE_FORMAT_NUMPY
try:
    import girder
    from girder import logprint
    from .base import GirderTileSource  # noqa
except ImportError:
    import logging as logprint
    girder = None


AvailableTileSources = collections.OrderedDict()
# Create a partial function that will work through the known functions to get a
# tile source.
getTileSource = functools.partial(getTileSourceFromDict,
                                  AvailableTileSources)

__all__ = [
    'TileSource', 'TileSourceException', 'TileSourceAssetstoreException',
    'AvailableTileSources', 'TileOutputMimeTypes', 'TILE_FORMAT_IMAGE',
    'TILE_FORMAT_PIL', 'TILE_FORMAT_NUMPY', 'getTileSource']

if girder:
    __all__.append('GirderTileSource')

sourceList = [
    {'moduleName': '.tiff', 'className': 'TiffFileTileSource'},
    {'moduleName': '.tiff', 'className': 'TiffGirderTileSource',
     'girder': True},
    {'moduleName': '.svs', 'className': 'SVSFileTileSource'},
    {'moduleName': '.svs', 'className': 'SVSGirderTileSource', 'girder': True},
    {'moduleName': '.ometiff', 'className': 'OMETiffFileTileSource'},
    {'moduleName': '.ometiff', 'className': 'OMETiffGirderTileSource',
     'girder': True},
    {'moduleName': '.mapniksource', 'className': 'MapnikTileSource'},
    {'moduleName': '.mapniksource', 'className': 'MapnikGirderTileSource', 'girder': True},
    {'moduleName': '.openjpeg', 'className': 'OpenjpegFileTileSource'},
    {'moduleName': '.openjpeg', 'className': 'OpenjpegGirderTileSource',
     'girder': True},
    {'moduleName': '.pil', 'className': 'PILFileTileSource'},
    {'moduleName': '.pil', 'className': 'PILGirderTileSource', 'girder': True},
    {'moduleName': '.test', 'className': 'TestTileSource'},
    {'moduleName': '.dummy', 'className': 'DummyTileSource'}
]

for source in sourceList:
    try:
        # Don't try to load girder sources if we couldn't import girder
        if not girder and source.get('girder'):
            continue
        # For each of our sources, try to import the named class from the
        # source module
        className = source['className']
        sourceModule = __import__(
            source['moduleName'].lstrip('.'), globals(), locals(), [className],
            len(source['moduleName']) - len(source['moduleName'].lstrip('.')))
        sourceClass = getattr(sourceModule, className)
        # Add the source class to the locals name so that it can be reached by
        # importing the tilesource module
        locals().update({className: sourceClass})
        # add it to our list of exports
        __all__.append(className)
        # add it to our dictionary of available sources if it has a name
        if getattr(sourceClass, 'name', None):
            AvailableTileSources[sourceClass.name] = sourceClass
    except (ImportError, OSError):
        logprint.info('Notice: Could not import %s' % className)
