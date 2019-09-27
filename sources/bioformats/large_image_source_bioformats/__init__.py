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
from pkg_resources import DistributionNotFound, get_distribution

from large_image.constants import SourcePriority

from .base import BioFormatsFileTileSource


try:
    __version__ = get_distribution(__name__).version
except DistributionNotFound:
    # package is not installed
    pass


class SimpleBioFormatsFileTileSource(BioFormatsFileTileSource):
    """
    Provides tile access to single image PIL files.
    """

    name = 'bioformats'
    extensions = {
        'jp2': SourcePriority.HIGH,
    }
    mimeTypes = {
        'image/jp2': SourcePriority.HIGH
    }
