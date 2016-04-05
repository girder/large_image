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
import six

from bson import ObjectId

from girder.constants import AccessType
from girder.models.model_base import Model, ValidationException


class Annotation(Model):
    """
    This model is used to represent an annotation that is associated with an
    item.  The annotation can contain any number of annotationshapes, which are
    included because they reference this annoation as a parent.  The annotation
    acts like these are a native part of it, though they are each stored as
    independent models to (eventually) permit faster spatial searching.
    """

    class Skill(enum.Enum):
        NOVICE = 'novice'
        EXPERT = 'expert'

    def initialize(self):
        self.name = 'annotation'
        # self.ensureIndices(['imageId', 'created'])

        self.exposeFields(AccessType.READ, (
            'imageId',
            'skill',
            'creatorId',
            'startTime'
            'stopTime'
            'created'
        ))
        # events.bind('model.item.remove_with_kwargs',
        #             'isic_archive.gc_segmentation',
        #             self._onDeleteItem)

    def createAnnotation(self, image, creator):

        annotation = self.save({
            'imageId': image['_id'],
            'creatorId': creator['_id'],
            'created': datetime.datetime.utcnow()
        })

        return annotation

    def validate(self, doc):

        coordSchema = {
            'type': 'array',
            # TODO: validate that z==0 for now
            'items': {
                'type': 'integer',
                'minimum': 0,
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
            'pattern': '^#[0-9a-fA-F]{6}$'
        }

        baseShapeSchema = {
            '$schema': 'http://json-schema.org/schema#',
            'id': '/girder/plugins/large_image/models/base_shape',
            'type': 'object',
            'properties': {
                '_id': {'type': ObjectId},
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
                            'type': 'integer',
                            'minimum': 0
                        },
                    },
                    'required': ['value'],
                    'additionalProperties': False
                },
                'lineColor': colorSchema,
                'lineWidth': {
                    'type': 'integer',
                    'minimum': 0
                },
                'opacity': {
                    'type': 'number',
                    'minimum': 0.0,
                    'maximum': 1.0
                }
            },
            'required': ['_id', 'type'],
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
                            'enum': ['Point']
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
                            'enum': ['Arrow']
                        },
                        'points': {
                            'type': 'array',
                            'items': coordSchema,
                            'minItems': 2,
                            'maxItems': 2,
                        },
                        'fillColor': colorSchema
                    },
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
                            'enum': ['Circle']
                        },
                        'center': coordSchema,
                        'radius': {
                            'type': 'integer',
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
                            'enum': ['Polyline']
                        },
                        'points': {
                            'type': 'array',
                            'items': coordSchema,
                            'minItems': 2,
                        },
                        'fillColor': colorSchema
                    },
                    'required': ['type', 'points'],
                    'patternProperties': baseShapePatternProperties,
                    'additionalProperties': False
                }
            ]
        }

        rectangleShapeSchema = {
            'allOf': [
                baseShapeSchema,
                {
                    'type': 'object',
                    'properties': {
                        'type': {
                            'type': 'string',
                            'enum': ['Rectangle']
                        },
                        'points': {
                            'type': 'array',
                            'items': coordSchema,
                            # TODO: 4 vs 5?
                            # TODO: validate first == last
                            'minItems': 5,
                            'maxItems': 5
                        },
                        'fillColor': colorSchema
                    },
                    'required': ['type', 'points'],
                    'patternProperties': baseShapePatternProperties,
                    'additionalProperties': False
                }
            ]
        }

        annotationSchema = {
            '$schema': 'http://json-schema.org/schema#',
            'id': '/girder/plugins/large_image/models/annotation',
            'type': 'object',
            'properties': {
                '_id': {'type': ObjectId},
                'name': {
                    'type': 'string',
                    # TODO: Disallow empty?
                    'minLength': 1,
                },
                'description': {'type': 'string'},
                'imageId': {'type': ObjectId},
                'creatorId': {'type': ObjectId},
                'created': {'type': datetime.datetime},
                # 'modifiedTime': {'type': datetime.datetime},
                'attributes': {
                    'type': 'object',
                    'additionalProperties': True,
                    'title': 'Image Attributes',
                    'description': 'Subjective things that apply to the ' +
                                   'entire image.'
                },
                'markup': {
                    'type': 'array',
                    'items': {
                        # Shape subtypes are mutually exclusive, so for
                        #  efficiency. don't use 'oneOf'
                        'anyOf': [
                            baseShapeSchema,
                        ]
                    },
                    'uniqueItems': True,
                    'title': 'Image Markup',
                    'description': 'Subjective things that apply to a ' +
                                   'spatial region.'
                }
            },
            'required': ['_id', 'name', 'description', 'imageId', 'creatorId',
                         'created'],
            'additionalProperties': False
        }
        # remove warnings for now
        _ = circleShapeSchema
        _ = pointShapeSchema
        _ = arrowShapeSchema
        _ = polylineShapeSchema
        _ = rectangleShapeSchema
        _ = annotationSchema
        _ = _

        raise ValidationException('')
        return doc
