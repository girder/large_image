# -*- coding: utf-8 -*-

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

from pkg_resources import DistributionNotFound, get_distribution

from large_image.constants import SourcePriority
from large_image.tilesource import TileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


class DummyTileSource(TileSource):
    name = 'dummy'
    extensions = {
        None: SourcePriority.MANUAL
    }

    def __init__(self, *args, **kwargs):
        super(DummyTileSource, self).__init__()
        self.tileWidth = 0
        self.tileHeight = 0
        self.levels = 0
        self.sizeX = 0
        self.sizeY = 0

    @classmethod
    def canRead(cls, *args, **kwargs):
        return True

    def getTile(self, x, y, z, **kwargs):
        return b''
