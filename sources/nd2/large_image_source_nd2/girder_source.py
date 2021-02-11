##############################################################################
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
##############################################################################

from girder_large_image.girder_tilesource import GirderTileSource
from . import ND2FileTileSource


class ND2GirderTileSource(ND2FileTileSource, GirderTileSource):
    """
    Provides tile access to Girder items with an ND2 file or other files that
    the nd2reader library can read.
    """

    cacheName = 'tilesource'
    name = 'nd2'
