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


# Constants representing the setting keys for this plugin
class PluginSettings(object):
    LARGE_IMAGE_SHOW_THUMBNAILS = 'large_image.show_thumbnails'
    LARGE_IMAGE_SHOW_EXTRA_PUBLIC = 'large_image.show_extra_public'
    LARGE_IMAGE_SHOW_EXTRA = 'large_image.show_extra'
    LARGE_IMAGE_SHOW_EXTRA_ADMIN = 'large_image.show_extra_admin'
    LARGE_IMAGE_SHOW_ITEM_EXTRA_PUBLIC = 'large_image.show_item_extra_public'
    LARGE_IMAGE_SHOW_ITEM_EXTRA = 'large_image.show_item_extra'
    LARGE_IMAGE_SHOW_ITEM_EXTRA_ADMIN = 'large_image.show_item_extra_admin'
    LARGE_IMAGE_SHOW_VIEWER = 'large_image.show_viewer'
    LARGE_IMAGE_DEFAULT_VIEWER = 'large_image.default_viewer'
    LARGE_IMAGE_AUTO_SET = 'large_image.auto_set'
    LARGE_IMAGE_MAX_THUMBNAIL_FILES = 'large_image.max_thumbnail_files'
    LARGE_IMAGE_MAX_SMALL_IMAGE_SIZE = 'large_image.max_small_image_size'
