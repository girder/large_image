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


class SourcePriority(object):
    NAMED = 0    # Explicitly requested
    PREFERRED = 1
    HIGHER = 2
    HIGH = 3
    MEDIUM = 4
    LOW = 5
    LOWER = 6
    FALLBACK = 7
    MANUAL = 8   # Will never be selected automatically


TILE_FORMAT_IMAGE = 'image'
TILE_FORMAT_PIL = 'PIL'
TILE_FORMAT_NUMPY = 'numpy'


TileOutputMimeTypes = {
    # JFIF forces conversion to JPEG through PIL to ensure the image is in a
    # common colorspace.  JPEG colorspace is complex: see
    #   https://docs.oracle.com/javase/8/docs/api/javax/imageio/metadata/
    #                           doc-files/jpeg_metadata.html
    'JFIF': 'image/jpeg',
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'TIFF': 'image/tiff',
}
TileOutputPILFormat = {
    'JFIF': 'JPEG'
}


TileInputUnits = {
    None: 'base_pixels',
    'base': 'base_pixels',
    'base_pixel': 'base_pixels',
    'base_pixels': 'base_pixels',
    'pixel': 'mag_pixels',
    'pixels': 'mag_pixels',
    'mag_pixel': 'mag_pixels',
    'mag_pixels': 'mag_pixels',
    'magnification_pixel': 'mag_pixels',
    'magnification_pixels': 'mag_pixels',
    'mm': 'mm',
    'millimeter': 'mm',
    'millimeters': 'mm',
    'fraction': 'fraction',
}
