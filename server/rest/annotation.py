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

import cherrypy

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
        Description('Search for annotations.')
        .responseClass('Annotation')
        .param('itemId', 'List all annotations in this item.', required=False)
        .param('userId', 'List all annotations created by this user.',
               required=False)
        .param('text', 'Pass this to perform a full text search for '
               'annotation names and descriptions.', required=False)
        .param('name', 'Pass to lookup an annotation by exact name match.',
               required=False)
        .pagingParams(defaultSort='lowerName')
        .errorResponse()
        .errorResponse('Read access was denied on the parent item.', 403)
    )
    @access.public
    @filtermodel(model='annotation', plugin='large_image')
    def find(self, params):
        limit, offset, sort = self.getPagingParameters(params, 'lowerName')
        query = {}
        if 'itemId' in params:
            item = self.model('item').load(params.get('itemId'), force=True)
            self.model('item').requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.READ)
            query['itemId'] = item['_id']
        if 'userId' in params:
            user = self.model('user').load(
                params.get('userId'), user=self.getCurrentUser(),
                level=AccessType.READ)
            query['creatorId'] = user['_id']
        if params.get('text'):
            query['$text'] = {'$search': params['text']}
        if params.get('name'):
            query['annotation.name'] = params['name']
        fields = list(('annotation.name', 'annotation.description') +
                      self.model('annotation', 'large_image').baseFields)
        return list(self.model('annotation', 'large_image').find(
            query, limit=limit, offset=offset, sort=sort, fields=fields))

    @describeRoute(
        Description('Get an annotation by id.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the annotation.', 403)
    )
    @access.public
    @loadmodel(model='annotation', plugin='large_image')
    @filtermodel(model='annotation', plugin='large_image')
    def getAnnotation(self, annotation, params):
        # Ensure that we have read access to the parent item
        item = self.model('item').load(annotation.get('itemId'), force=True)
        self.model('item').requireAccess(
            item, user=self.getCurrentUser(), level=AccessType.READ)
        return annotation

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
        except ValidationException as exc:
            logger.exception('Failed to validate annotation')
            raise RestException(
                'Validation Error: JSON doesn\'t follow schema (%s).' % (
                    exc.message, ))

    @describeRoute(
        Description('Update an annotation or move it to a different item.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('itemId', 'Pass this to move the annotation to a new item.',
               required=False)
        .param('body', 'A JSON object containing the annotation.',
               paramType='body', required=False)
        .errorResponse('Write access was denied for the item.', 403)
        .errorResponse('Invalid JSON passed in request body.')
        .errorResponse('Validation Error: JSON doesn\'t follow schema.')
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image')
    @filtermodel(model='annotation', plugin='large_image')
    def updateAnnotation(self, annotation, params):
        user = self.getCurrentUser()
        item = self.model('item').load(annotation.get('itemId'), force=True)
        if item is not None:
            self.model('item').requireAccess(
                item, user=user, level=AccessType.WRITE)
        # If we have a content length, then we have replacement JSON.
        if cherrypy.request.body.length:
            annotation['annotation'] = self.getBodyJson()
        if params.get('itemId'):
            newitem = self.model('item').load(params['itemId'], force=True)
            self.model('item').requireAccess(
                newitem, user=user, level=AccessType.WRITE)
            annotation['itemId'] = newitem['_id']
        try:
            self.model('annotation', 'large_image').updateAnnotation(
                annotation, updateUser=user)
        except ValidationException as exc:
            logger.exception('Failed to validate annotation')
            raise RestException(
                'Validation Error: JSON doesn\'t follow schema (%s).' % (
                    exc.message, ))
        return annotation

    @describeRoute(
        Description('Delete an annotation.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the annotation.', 403)
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image')
    def deleteAnnotation(self, annotation, params):
        # Ensure that we have write access to the parent item
        item = self.model('item').load(annotation.get('itemId'), force=True)
        if item is not None:
            self.model('item').requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.WRITE)
        self.model('annotation', 'large_image').remove(annotation)
