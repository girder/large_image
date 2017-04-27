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
from girder.constants import AccessType, SortDir
from girder.models.model_base import ValidationException
from ..models.annotation import AnnotationSchema


class AnnotationResource(Resource):

    def __init__(self):
        super(AnnotationResource, self).__init__()

        self.resourceName = 'annotation'
        self.route('GET', (), self.find)
        self.route('GET', ('schema',), self.getAnnotationSchema)
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
        Description('Get the official Annotation schema')
        .notes('In addition to the schema, if IDs are specified on elements, '
               'all IDs must be unique.')
        .errorResponse()
    )
    @access.public
    def getAnnotationSchema(self, params):
        return AnnotationSchema.annotationSchema

    @describeRoute(
        Description('Get an annotation by id.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('left', 'The left column of the area to fetch.',
               required=False, dataType='float')
        .param('right', 'The right column (exclusive) of the area to fetch.',
               required=False, dataType='float')
        .param('top', 'The top row of the area to fetch.',
               required=False, dataType='float')
        .param('bottom', 'The bottom row (exclusive) of the area to fetch.',
               required=False, dataType='float')
        .param('low', 'The lowest z value of the area to fetch.',
               required=False, dataType='float')
        .param('high', 'The highest z value (exclusive) of the area to fetch.',
               required=False, dataType='float')
        .param('minimumSize', 'Only annotations larger than or equal to this '
               'size in pixels will be returned.  Size is determined by the '
               'length of the diagonal of the bounding box of an element.  '
               'This probably should be 1 at the maximum zoom, 2 at the next '
               'level down, 4 at the next, etc.', required=False,
               dataType='float')
        .param('maxDetails', 'Limit the number of annotations returned based '
               'on complexity.  The complexity of an annotation is how many '
               'points are used to defined it.  This is applied in addition '
               'to the limit.  Using maxDetails helps ensure results will be '
               'able to be rendered.', required=False, dataType='int')
        .pagingParams(defaultSort='_id', defaultLimit=None,
                      defaultSortDir=SortDir.ASCENDING)
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the annotation.', 403)
        .notes('Use "size" or "details" as possible sort keys.')
    )
    @access.public
    @filtermodel(model='annotation', plugin='large_image')
    def getAnnotation(self, id, params):
        annotation = self.model('annotation', 'large_image').load(id, region=params)
        # Ensure that we have read access to the parent item.  We could fail
        # faster when there are permissions issues if we didn't load the
        # annotation elements before checking the item access permissions.
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
    # Load with a limit of 1 so that we don't bother getting most annotations
    @loadmodel(model='annotation', plugin='large_image', getElements=False)
    def deleteAnnotation(self, annotation, params):
        # Ensure that we have write access to the parent item
        item = self.model('item').load(annotation.get('itemId'), force=True)
        if item is not None:
            self.model('item').requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.WRITE)
        self.model('annotation', 'large_image').remove(annotation)
