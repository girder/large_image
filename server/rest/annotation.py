#!/usr/bin/env python
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

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, Description
from girder.api.rest import Resource, loadmodel, filtermodel, RestException
from girder.constants import AccessType
from girder.models.model_base import ValidationException


class AnnotationResource(Resource):

    def __init__(self):
        super(AnnotationResource, self).__init__()

        self.resourceName = 'annotation'
        self.route('GET', (), self.find)
        self.route('GET', (':id',), self.getAnnotation)
        self.route('POST', (), self.createAnnotation)
        self.route('PUT', (':id',), self.updateAnnotation)
        self.route('DELETE', (':id',), self.deleteAnnotation)

    @describeRoute(
        Description('Get annotations.')
    )
    @access.public
    def find(self, params):
        # ##DWM::
        return []

    @describeRoute(
        Description('Get an annotation.')
        .param('itemId', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the annotation.', 403)
    )
    @access.public
    def getAnnotation(self, id, params):
        # ##DWM::
        return {}

    @describeRoute(
        Description('Create an annotation.')
        .responseClass('Annotation')
        .param('itemId', 'The ID of the associated item.')
        .param('body', 'A JSON object containing the annotation.',
               paramType='body')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
        .errorResponse('Invalid JSON passed in request body.')
        .errorResponse('Validation Error: JSON doesn\'t follow schema.')
    )
    @access.user
    @loadmodel(map={'itemId': 'item'}, model='item', level=AccessType.WRITE)
    @filtermodel(model='annotation', plugin='large_image')
    def createAnnotation(self, item, params):
        try:
            return self.model('annotation', 'large_image').createAnnotation(
                item, self.getCurrentUser(), self.getBodyJson())
        except ValidationException:
            logger.exception('Failed to validate annotation')
            raise RestException(
                'Validation Error: JSON doesn\'t follow schema.')

    @describeRoute(
        Description('Update an annotation.')
        .param('itemId', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the annotation.', 403)
    )
    @access.user
    def updateAnnotation(self, id, params):
        # ##DWM::
        return None

    @describeRoute(
        Description('Delete an annotation.')
        .param('itemId', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the annotation.', 403)
    )
    @access.user
    def deleteAnnotation(self, id, params):
        # ##DWM::
        return None
