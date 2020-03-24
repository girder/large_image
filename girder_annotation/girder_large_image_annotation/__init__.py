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

from girder.exceptions import ValidationException
from girder.plugin import GirderPlugin, getPlugin
from girder.settings import SettingDefault
from girder.utility import setting_utilities
from girder.utility.model_importer import ModelImporter

from . import constants
from .models.annotation import Annotation
from .rest.annotation import AnnotationResource


# Validators

@setting_utilities.validator({
    constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY,
})
def validateBoolean(doc):
    val = doc['value']
    if str(val).lower() not in ('false', 'true', ''):
        raise ValidationException('%s must be a boolean.' % doc['key'], 'value')
    doc['value'] = (str(val).lower() != 'false')


# Defaults

# Defaults that have fixed values can just be added to the system defaults
# dictionary.
SettingDefault.defaults.update({
    constants.PluginSettings.LARGE_IMAGE_ANNOTATION_HISTORY: True,
})


class LargeImageAnnotationPlugin(GirderPlugin):
    DISPLAY_NAME = 'Large Image Annotation'
    CLIENT_SOURCE_PATH = 'web_client'

    def load(self, info):
        getPlugin('large_image').load(info)

        ModelImporter.registerModel('annotation', Annotation, 'large_image')
        info['apiRoot'].annotation = AnnotationResource()
        # Ask for some models to make sure their singletons are initialized.
        # Also migrate the database as a one-time action.
        Annotation()._migrateDatabase()

        # add copyAnnotations option to POST resource/copy, POST item/{id}/copy
        # and POST folder/{id}/copy
        info['apiRoot'].resource.copyResources.description.param(
            'copyAnnotations', 'Copy annotations when copying resources (default true)',
            required=False, dataType='boolean')
        info['apiRoot'].item.copyItem.description.param(
            'copyAnnotations', 'Copy annotations when copying item (default true)',
            required=False, dataType='boolean')
        info['apiRoot'].folder.copyFolder.description.param(
            'copyAnnotations', 'Copy annotations when copying folder (default true)',
            required=False, dataType='boolean')
