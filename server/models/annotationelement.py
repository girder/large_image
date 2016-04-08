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

from girder.constants import AccessType, SortDir
from girder.models.model_base import Model  # ##DWM::, ValidationException


class Annotationelement(Model):
    def initialize(self):
        self.name = 'annotationelement'
        self.ensureIndices(['annotationId', 'created'])

        self.exposeFields(AccessType.READ, (
            '_id', 'annotationId', 'created', 'element'))

    def getElements(self, annotation):
        """
        Given an annotation, fetch the elements from the database and add them
        to it.

        :param annotation: the annotation to get elements for.  Modified.
        """
        elements = self.find({'annotationId': annotation['_id']},
                             sort=[('_id', SortDir.ASCENDING)])
        annotation['annotation']['elements'] = [
            entry['element'] for entry in elements]

    def removeElements(self, annotation):
        """
        Remove all elements related to the specified annoation.
        """
        self.model('annotationelement', 'large_image').removeWithQuery({
            'annotationId': annotation['_id']
        })

    def updateElements(self, annotation):
        """
        Given an annotation, extract the elements from it and update the
        database of them.

        :param annotation: the annotation to save elements for.  Modified.
        """
        # TODO: modify or maintain existing elements to reduce database churn
        self.model('annotationelement', 'large_image').removeWithQuery({
            'annotationId': annotation['_id']
        })
        elements = annotation['annotation'].get('elements', [])
        now = datetime.datetime.utcnow()
        self.collection.insert_many([{
            'annotationId': annotation['_id'],
            'created': now,
            'element': element
        } for element in elements])
