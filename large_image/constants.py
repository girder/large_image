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

import enum


class SourcePriority(enum.IntEnum):
    NAMED = 0    # Explicitly requested
    PREFERRED = 1
    HIGHER = 2
    HIGH = 3
    MEDIUM = 4
    LOW = 5
    LOWER = 6
    IMPLICIT_HIGH = 7
    IMPLICIT = 8
    IMPLICIT_LOW = 9
    FALLBACK_HIGH = 10
    FALLBACK = 11
    MANUAL = 12  # This and higher values will never be selected automatically


TILE_FORMAT_IMAGE = 'image'
TILE_FORMAT_PIL = 'PIL'
TILE_FORMAT_NUMPY = 'numpy'


NEW_IMAGE_PATH_FLAG = '__new_image__'


PROJECTION_SENTINEL = '__default__'


TileOutputMimeTypes = {
    'JPEG': 'image/jpeg',
    'PNG': 'image/png',
    'TIFF': 'image/tiff',
    # TILED indicates the region output should be generated as a tiled TIFF
    'TILED': 'image/tiff',
    # JFIF forces conversion to JPEG through PIL to ensure the image is in a
    # common colorspace.  JPEG colorspace is complex: see
    #   https://docs.oracle.com/javase/8/docs/api/javax/imageio/metadata/
    #                           doc-files/jpeg_metadata.html
    'JFIF': 'image/jpeg',
}
TileOutputPILFormat = {
    'JFIF': 'JPEG',
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
    'nm': 'nm',
    'nanometer': 'nm',
    'nanometers': 'nm',
    'mm': 'mm',
    'millimeter': 'mm',
    'millimeters': 'mm',
    'm': 'm',
    'meter': 'm',
    'meters': 'm',
    'km': 'km',
    'kilometer': 'km',
    'kilometers': 'km',
    'fraction': 'fraction',
    'projection': 'projection',
    'proj': 'projection',
    'wgs84': 'proj4:EPSG:4326',
    '4326': 'proj4:EPSG:4326',
}

# numpy dtype to pyvips GValue
dtypeToGValue = {
    'b': 'char',
    'B': 'uchar',
    'd': 'double',
    'D': 'dpcomplex',
    'f': 'float',
    'F': 'complex',
    'h': 'short',
    'H': 'ushort',
    'i': 'int',
    'I': 'uint',
}
GValueToDtype = {v: k for k, v in dtypeToGValue.items()}
