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

import json

import cherrypy

from girder import logger
from girder.api import access
from girder.api.describe import describeRoute, autoDescribeRoute, Description
from girder.api.rest import Resource, loadmodel, filtermodel
from girder.constants import AccessType, SortDir
from girder.exceptions import ValidationException, RestException
from girder.models.item import Item
from girder.models.user import User
from ..models.annotation import AnnotationSchema, Annotation


class AnnotationResource(Resource):

    def __init__(self):
        super(AnnotationResource, self).__init__()

        self.resourceName = 'annotation'
        self.route('GET', (), self.find)
        self.route('GET', ('schema',), self.getAnnotationSchema)
        self.route('GET', ('images',), self.findAnnotatedImages)
        self.route('GET', (':id',), self.getAnnotation)
        self.route('GET', (':id', 'history'), self.getAnnotationHistoryList)
        self.route('GET', (':id', 'history', ':version'), self.getAnnotationHistory)
        self.route('PUT', (':id', 'history', 'revert'), self.revertAnnotationHistory)
        self.route('POST', (), self.createAnnotation)
        self.route('POST', (':id', 'copy'), self.copyAnnotation)
        self.route('PUT', (':id',), self.updateAnnotation)
        self.route('DELETE', (':id',), self.deleteAnnotation)
        self.route('GET', (':id', 'access'), self.getAnnotationAccess)
        self.route('PUT', (':id', 'access'), self.updateAnnotationAccess)

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
        query = {'_active': {'$ne': False}}
        if 'itemId' in params:
            item = Item().load(params.get('itemId'), force=True)
            Item().requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.READ)
            query['itemId'] = item['_id']
        if 'userId' in params:
            user = User().load(
                params.get('userId'), user=self.getCurrentUser(),
                level=AccessType.READ)
            query['creatorId'] = user['_id']
        if params.get('text'):
            query['$text'] = {'$search': params['text']}
        if params.get('name'):
            query['annotation.name'] = params['name']
        fields = list(('annotation.name', 'annotation.description', 'access') +
                      Annotation().baseFields)
        return list(Annotation().filterResultsByPermission(
            cursor=Annotation().find(query, sort=sort, fields=fields),
            user=self.getCurrentUser(), level=AccessType.READ, limit=limit, offset=offset
        ))

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
    @access.cookie
    @access.public
    @filtermodel(model='annotation', plugin='large_image')
    def getAnnotation(self, id, params):
        user = self.getCurrentUser()
        annotation = Annotation().load(id, region=params, user=user, level=AccessType.READ)
        if annotation is None:
            raise RestException('Annotation not found', 404)
        # Ensure that we have read access to the parent item.  We could fail
        # faster when there are permissions issues if we didn't load the
        # annotation elements before checking the item access permissions.
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
            return Annotation().createAnnotation(
                item, self.getCurrentUser(), self.getBodyJson())
        except ValidationException as exc:
            logger.exception('Failed to validate annotation')
            raise RestException(
                'Validation Error: JSON doesn\'t follow schema (%r).' % (
                    exc.args, ))

    @describeRoute(
        Description('Copy an annotation from one item to an other.')
        .param('id', 'The ID of the annotation.', paramType='path',
               required=True)
        .param('itemId', 'The ID of the destination item.',
               required=True)
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403)
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image', level=AccessType.READ)
    @filtermodel(model='annotation', plugin='large_image')
    def copyAnnotation(self, annotation, params):
        itemId = params['itemId']
        user = self.getCurrentUser()
        Item().load(annotation.get('itemId'),
                    user=user,
                    level=AccessType.READ)
        item = Item().load(itemId, user=user, level=AccessType.WRITE)
        return Annotation().createAnnotation(
            item, user, annotation['annotation'])

    @describeRoute(
        Description('Update an annotation or move it to a different item.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('itemId', 'Pass this to move the annotation to a new item.',
               required=False)
        .param('body', 'A JSON object containing the annotation.  If the '
               '"annotation":"elements" property is not set, the elements '
               'will not be modified.',
               paramType='body', required=False)
        .errorResponse('Write access was denied for the item.', 403)
        .errorResponse('Invalid JSON passed in request body.')
        .errorResponse('Validation Error: JSON doesn\'t follow schema.')
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image', level=AccessType.WRITE)
    @filtermodel(model='annotation', plugin='large_image')
    def updateAnnotation(self, annotation, params):
        user = self.getCurrentUser()
        item = Item().load(annotation.get('itemId'), force=True)
        if item is not None:
            Item().requireAccess(
                item, user=user, level=AccessType.WRITE)
        # If we have a content length, then we have replacement JSON.  If
        # elements are not included, don't replace them
        returnElements = True
        if cherrypy.request.body.length:
            oldElements = annotation.get('annotation', {}).get('elements')
            annotation['annotation'] = self.getBodyJson()
            if 'elements' not in annotation['annotation'] and oldElements:
                annotation['annotation']['elements'] = oldElements
                returnElements = False
        if params.get('itemId'):
            newitem = Item().load(params['itemId'], force=True)
            Item().requireAccess(
                newitem, user=user, level=AccessType.WRITE)
            annotation['itemId'] = newitem['_id']
        try:
            annotation = Annotation().updateAnnotation(annotation, updateUser=user)
        except ValidationException as exc:
            logger.exception('Failed to validate annotation')
            raise RestException(
                'Validation Error: JSON doesn\'t follow schema (%r).' % (
                    exc.args, ))
        if not returnElements:
            del annotation['annotation']['elements']
        return annotation

    @describeRoute(
        Description('Delete an annotation.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the annotation.', 403)
    )
    @access.user
    # Load with a limit of 1 so that we don't bother getting most annotations
    @loadmodel(model='annotation', plugin='large_image', getElements=False, level=AccessType.WRITE)
    def deleteAnnotation(self, annotation, params):
        # Ensure that we have write access to the parent item
        item = Item().load(annotation.get('itemId'), force=True)
        if item is not None:
            Item().requireAccess(
                item, user=self.getCurrentUser(), level=AccessType.WRITE)
        Annotation().remove(annotation)

    @describeRoute(
        Description('Search for annotated images.')
        .notes(
            'By default, this endpoint will return a list of recently annotated images.  '
            'This list can be further filtered by passing the creatorId and/or imageName '
            'parameters.  The creatorId parameter will limit results to annotations '
            'created by the given user.  The imageName parameter will only include '
            'images whose name (or a token in the name) begins with the given string.')
        .param('creatorId', 'Limit to annotations created by this user', required=False)
        .param('imageName', 'Filter results by image name (case-insensitive)', required=False)
        .pagingParams(defaultSort='updated', defaultSortDir=-1)
        .errorResponse()
    )
    @access.public
    def findAnnotatedImages(self, params):
        limit, offset, sort = self.getPagingParameters(
            params, 'updated', SortDir.DESCENDING)
        user = self.getCurrentUser()

        creator = None
        if 'creatorId' in params:
            creator = User().load(params.get('creatorId'), force=True)

        return Annotation().findAnnotatedImages(
            creator=creator, imageNameFilter=params.get('imageName'),
            user=user, level=AccessType.READ,
            offset=offset, limit=limit, sort=sort)

    @describeRoute(
        Description('Get the access control list for an annotation.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the annotation.', 403)
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image', level=AccessType.ADMIN)
    def getAnnotationAccess(self, annotation, params):
        return Annotation().getFullAccessList(annotation)

    @describeRoute(
        Description('Update the access control list for an annotation.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('access', 'THe JSON-encoded access control list.')
        .errorResponse('ID was invalid.')
        .errorResponse('Admin access was denied for the annotation.', 403)
    )
    @access.user
    @loadmodel(model='annotation', plugin='large_image', level=AccessType.ADMIN)
    @filtermodel(model=Annotation, addFields={'access'})
    def updateAnnotationAccess(self, annotation, params):
        access = json.loads(params['access'])
        return Annotation().setAccessList(
            annotation, access, save=True, user=self.getCurrentUser())

    @autoDescribeRoute(
        Description('Get a list of an annotation\'s history.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .pagingParams(defaultSort='_version', defaultLimit=0,
                      defaultSortDir=SortDir.DESCENDING)
        .errorResponse('Read access was denied for the annotation.', 403)
    )
    @access.cookie
    @access.public
    def getAnnotationHistoryList(self, id, limit, offset, sort):
        return list(Annotation().versionList(id, self.getCurrentUser(), limit, offset, sort))

    @autoDescribeRoute(
        Description('Get a specific version of an annotation\'s history.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('version', 'The version of the annotation.', paramType='path',
               dataType='integer')
        .errorResponse('Annotation history version not found.')
        .errorResponse('Read access was denied for the annotation.', 403)
    )
    @access.cookie
    @access.public
    def getAnnotationHistory(self, id, version):
        result = Annotation().getVersion(id, version, self.getCurrentUser())
        if result is None:
            raise RestException('Annotation history version not found.')
        return result

    @autoDescribeRoute(
        Description('Revert an annotation to a specific version.')
        .notes('This can be used to undelete an annotation by reverting to '
               'the most recent version.')
        .param('id', 'The ID of the annotation.', paramType='path')
        .param('version', 'The version of the annotation.  If not specified, '
               'if the annotation was deleted this undeletes it.  If it was '
               'not deleted, this reverts to the previous version.',
               required=False, dataType='integer')
        .errorResponse('Annotation history version not found.')
        .errorResponse('Read access was denied for the annotation.', 403)
    )
    @access.public
    def revertAnnotationHistory(self, id, version):
        annotation = Annotation().revertVersion(id, version, self.getCurrentUser())
        if not annotation:
            raise RestException('Annotation history version not found.')
        # Don't return the elements -- it can be too verbose
        del annotation['annotation']['elements']
        return annotation
