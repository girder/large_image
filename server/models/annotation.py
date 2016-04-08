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

import datetime
import enum
import jsonschema
import six

from girder import events
from girder.constants import AccessType
from girder.models.model_base import Model, ValidationException


class AnnotationSchema:
    coordSchema = {
        'type': 'array',
        # TODO: validate that z==0 for now
        'items': {
            'type': 'number'
        },
        'minItems': 3,
        'maxItems': 3,
        'name': 'Coordinate',
        # TODO: define origin for 3D images
        'description': 'An X, Y, Z coordinate tuple, in base layer pixel'
                       ' coordinates, where the origin is the upper-left.'
    }

    colorSchema = {
        'type': 'string',
        # We accept colors of the form
        #   #aabbcc                 six digit RRGGBB hex
        #   #abc                    three digit RGB hex
        #   rgb(255, 255, 255)      rgb decimal triplet
        #   rgba(255, 255, 255, 1)  rgba quad with RGB in the range [0-255] and
        #                           alpha [0-1]
        # TODO: make rgb and rgba spec validate that rgb is [0-255] and a is
        # [0-1], rather than just checking if they are digits and such.
        'pattern': '^(#[0-9a-fA-F]{3,6}|rgb\(\d+,\s*\d+,\s*\d+\)|'
                   'rgba\(\d+,\s*\d+,\s*\d+,\s*(\d?\.|)\d+\))$'
    }

    baseShapeSchema = {
        '$schema': 'http://json-schema.org/schema#',
        'id': '/girder/plugins/large_image/models/base_shape',
        'type': 'object',
        'properties': {
            'type': {'type': 'string'},
            'label': {
                'type': 'object',
                'properties': {
                    'value': {'type': 'string'},
                    'visability': {
                        'type': 'string',
                        # TODO: change to True, False, None?
                        'enum': ['hidden', 'always', 'onhover']
                    },
                    'fontSize': {
                        'type': 'number',
                        'minimum': 0,
                        'exclusiveMinimum': True,
                    },
                    'color': colorSchema,
                },
                'required': ['value'],
                'additionalProperties': False
            },
            'lineColor': colorSchema,
            'lineWidth': {
                'type': 'number',
                'minimum': 0
            }
        },
        'required': ['type'],
        'additionalProperties': True
    }
    baseShapePatternProperties = {
        '^%s$' % properyName: {}
        for properyName in six.viewkeys(baseShapeSchema['properties'])
        if properyName != 'type'
    }

    pointShapeSchema = {
        'allOf': [
            baseShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['point']
                    },
                    'center': coordSchema
                },
                'required': ['type', 'center'],
                'patternProperties': baseShapePatternProperties,
                'additionalProperties': False
            }
        ]
    }

    arrowShapeSchema = {
        'allOf': [
            baseShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['arrow']
                    },
                    'points': {
                        'type': 'array',
                        'items': coordSchema,
                        'minItems': 2,
                        'maxItems': 2,
                    },
                    'fillColor': colorSchema
                },
                'description': 'The first point is the head of the arrow',
                'required': ['type', 'points'],
                'patternProperties': baseShapePatternProperties,
                'additionalProperties': False
            }
        ]
    }

    circleShapeSchema = {
        'allOf': [
            baseShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['circle']
                    },
                    'center': coordSchema,
                    'radius': {
                        'type': 'number',
                        'minimum': 0
                    },
                    'fillColor': colorSchema
                },
                'required': ['type', 'center', 'radius'],
                'patternProperties': baseShapePatternProperties,
                'additionalProperties': False
            }
        ]
    }

    polylineShapeSchema = {
        'allOf': [
            baseShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['polyline']
                    },
                    'points': {
                        'type': 'array',
                        'items': coordSchema,
                        'minItems': 2,
                    },
                    'fillColor': colorSchema,
                    'closed': {
                        'type': 'boolean',
                        'description': 'polyline is open if closed flag is '
                                       'not specified'
                    },
                },
                'required': ['type', 'points'],
                'patternProperties': baseShapePatternProperties,
                'additionalProperties': False
            }
        ]
    }

    baseRectangleShapeSchema = {
        'allOf': [
            baseShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {'type': 'string'},
                    'center': coordSchema,
                    'width': {
                        'type': 'number',
                        'minimum': 0
                    },
                    'height': {
                        'type': 'number',
                        'minimum': 0
                    },
                    'rotation': {
                        'type': 'number',
                        'description': 'radians counterclockwise around normal',
                    },
                    'normal': coordSchema,
                    'fillColor': colorSchema
                },
                'decription': 'normal is the positive z-axis unless otherwise '
                              'specified',
                'required': ['type', 'center', 'width', 'height', 'rotation'],
                # 'patternProperties': baseShapePatternProperties,
                'additionalProperties': True,
            }
        ]
    }
    baseRectangleShapePatternProperties = {
        '^%s$' % properyName: {} for properyName in six.viewkeys(
            baseRectangleShapeSchema['allOf'][1]['properties'])
        if properyName != 'type'
    }
    baseRectangleShapePatternProperties.update(baseShapePatternProperties)
    rectangleShapeSchema = {
        'allOf': [
            baseRectangleShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['rectangle']
                    },
                },
                'required': ['type'],
                'patternProperties': baseRectangleShapePatternProperties,
                'additionalProperties': False
            }
        ]
    }
    rectangleGridShapeSchema = {
        'allOf': [
            baseRectangleShapeSchema,
            {
                'type': 'object',
                'properties': {
                    'type': {
                        'type': 'string',
                        'enum': ['rectanglegrid']
                    },
                    'widthSubdivisions': {
                        'type': 'integer',
                        'minimum': 1
                    },
                    'heightSubdivisions': {
                        'type': 'integer',
                        'minimum': 1
                    },
                },
                'required': ['type', 'widthSubdivisions', 'heightSubdivisions'],
                'patternProperties': baseRectangleShapePatternProperties,
                'additionalProperties': False,
            }
        ]
    }

    annotationSchema = {
        '$schema': 'http://json-schema.org/schema#',
        'id': '/girder/plugins/large_image/models/annotation',
        'type': 'object',
        'properties': {
            'name': {
                'type': 'string',
                # TODO: Disallow empty?
                'minLength': 1,
            },
            'description': {'type': 'string'},
            'attributes': {
                'type': 'object',
                'additionalProperties': True,
                'title': 'Image Attributes',
                'description': 'Subjective things that apply to the entire '
                               'image.'
            },
            'elements': {
                'type': 'array',
                'items': {
                    # Shape subtypes are mutually exclusive, so for
                    #  efficiency. don't use 'oneOf'
                    'anyOf': [
                        # If we include the baseShapeSchema, then shapes that
                        # are as-yet invented can be included.
                        # baseShapeSchema,
                        arrowShapeSchema,
                        circleShapeSchema,
                        pointShapeSchema,
                        polylineShapeSchema,
                        rectangleShapeSchema,
                        rectangleGridShapeSchema,
                    ]
                },
                # I don't think we want to enforce this.  I could see it being
                # valid to have two of the exact same element within an
                # annotation.
                'uniqueItems': True,
                'title': 'Image Markup',
                'description': 'Subjective things that apply to a '
                               'spatial region.'
            }
        },
        'additionalProperties': False
    }


class Annotation(Model):
    """
    This model is used to represent an annotation that is associated with an
    item.  The annotation can contain any number of annotationelements, which
    are included because they reference this annoation as a parent.  The
    annotation acts like these are a native part of it, though they are each
    stored as independent models to (eventually) permit faster spatial
    searching.
    """

    class Skill(enum.Enum):
        NOVICE = 'novice'
        EXPERT = 'expert'

    # This is everything except the annotation field, and is used, in part, to
    # determine what gets returned in a general find.
    baseFields = (
        '_id',
        'itemId',
        'creatorId',
        'created',
        'updated',
        'updatedId',
        # 'skill',
        # 'startTime'
        # 'stopTime'
    )

    def initialize(self):
        self.name = 'annotation'
        self.ensureIndices(['itemId', 'created'])
        self.ensureTextIndex({
            'annotation.name': 10,
            'annotation.description': 1,
        })

        self.exposeFields(AccessType.READ, (
            'annotation',
        ) + self.baseFields)
        events.bind('model.item.remove', 'large_image', self._onItemRemove)

    def _onItemRemove(self, event):
        """
        When an item is removed, also delete associated annotations.

        :param event: the event with the item information.
        """
        item = event.info
        annotations = self.model('annotation', 'large_image').find({
            'itemId': item['_id']
        })
        for annotation in annotations:
            self.model('annotation', 'large_image').remove(annotation)

    def createAnnotation(self, item, creator, annotation):
        now = datetime.datetime.utcnow()
        doc = {
            'itemId': item['_id'],
            'creatorId': creator['_id'],
            'created': now,
            'updatedId': creator['_id'],
            'updated': now,
            'annotation': annotation,
        }
        return self.save(doc)

    def load(self, *args, **kwargs):
        """
        Load an annotation, adding all of the elements to it.

        :returns: the matching annotation or none.
        """
        annotation = super(Annotation, self).load(*args, **kwargs)
        if annotation is not None:
            self.model('annotationelement', 'large_image').getElements(
                annotation)
        return annotation

    def remove(self, annotation, *args, **kwargs):
        """
        When removing an annotation, remove all element associated with it.
        This overrides the collection delete_one method so that all of the
        triggers are fired as expectd and cancelling from an event will work
        as needed.

        :param annotation: the annotation document to remove.
        """
        delete_one = self.collection.delete_one

        def deleteElements(query, *args, **kwargs):
            ret = delete_one(query, *args, **kwargs)
            self.model('annotationelement', 'large_image').removeElements(
                annotation)
            return ret

        self.collection.delete_one = deleteElements
        result = super(Annotation, self).remove(annotation, *args, **kwargs)
        self.collection.delete_one = delete_one
        return result

    def save(self, annotation, *args, **kwargs):
        """
        When saving an annotation, override the collection insert_one and
        replace_one methods so that we don't save the elements with the main
        annotation.  Still use the super class's save method, os that all of
        the triggers are fired as expected and cancelling and modifications can
        be done as needed.

        :param annotation: the annotation document to save.
        :returns: the saved document.  If it is a new document, the _id has
                  been added.
        """
        replace_one = self.collection.replace_one
        insert_one = self.collection.insert_one

        def replaceElements(query, doc, *args, **kwargs):
            elements = doc['annotation'].pop('elements', None)
            ret = replace_one(query, doc, *args, **kwargs)
            if elements is not None:
                doc['annotation']['elements'] = elements
                self.model('annotationelement', 'large_image').updateElements(
                    annotation)
            return ret

        def insertElements(doc, *args, **kwargs):
            elements = doc['annotation'].pop('elements', None)
            ret = insert_one(doc, *args, **kwargs)
            if elements is not None:
                doc['annotation']['elements'] = elements
                self.model('annotationelement', 'large_image').updateElements(
                    annotation)
            return ret

        self.collection.replace_one = replaceElements
        self.collection.insert_one = insertElements
        result = super(Annotation, self).save(annotation, *args, **kwargs)
        self.collection.replace_one = replace_one
        self.collection.insert_one = insert_one
        return result

    def updateAnnotation(self, annotation, updateUser=None):
        """
        Update an annotation.

        :param annotation: the annotation document to update.
        :param updateUser: the user who is creating the update.
        :returns: the annotation document that was updated.
        """
        annotation['updated'] = datetime.datetime.utcnow()
        annotation['updatedId'] = updateUser['_id']
        return self.save(annotation)

    def validate(self, doc):
        try:
            jsonschema.validate(doc.get('annotation'),
                                AnnotationSchema.annotationSchema)
        except jsonschema.ValidationError as exp:
            raise ValidationException(exp)
        return doc
