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
from six.moves import range

from girder.constants import AccessType, SortDir
from girder.models.model_base import Model  # ##DWM::, ValidationException


class Annotationelement(Model):
    def initialize(self):
        self.name = 'annotationelement'
        self.ensureIndices(['annotationId', '_version'])

        self.exposeFields(AccessType.READ, (
            '_id', '_version', 'annotationId', 'created', 'element'))
        self.versionId = None

    def getNextVersionValue(self):
        """
        Maintain a version number.  This is a single sequence that can be used
        to ensure we have the correct set of elements for an annotation.

        :returns: an integer version number that is strictly increasing.
        """
        if self.versionId is None:
            versionObject = self.collection.find_one(
                {'annotationId': 'version_sequence'})
            if versionObject is None:
                self.versionId = self.collection.insert_one(
                    {'annotationId': 'version_sequence', '_version': 0}
                ).inserted_id
            else:
                self.versionId = versionObject['_id']
        version = self.collection.find_one_and_update(
            {'_id': self.versionId},
            {'$inc': {'_version': 1}})
        return version['_version']

    def getElements(self, annotation):
        """
        Given an annotation, fetch the elements from the database and add them
        to it.

        :param annotation: the annotation to get elements for.  Modified.
        """
        elementCursor = self.find({'annotationId': annotation['_id'],
                                   '_version': annotation['_version']},
                                  sort=[('_id', SortDir.ASCENDING)])
        annotation['annotation']['elements'] = []
        for entry in elementCursor:
            entry['element'].setdefault('id', entry['_id'])
            annotation['annotation']['elements'].append(entry['element'])

    def removeElements(self, annotation):
        """
        Remove all elements related to the specified annoation.

        :param annotation: the annotation to remove elements from.
        """
        self.model('annotationelement', 'large_image').removeWithQuery({
            'annotationId': annotation['_id']
        })

    def removeOldElements(self, annotation, oldversion=None):
        """
        Remove all elements related to the specified annoation.

        :param annotation: the annotation to remove elements from.
        :param oldversion: if present, remove versions up to this number.  If
                           none, remove versions earlier than the version in
                           the annotation record.
        """
        query = {'annotationId': annotation['_id']}
        if oldversion is None or oldversion >= annotation['_version']:
            query['_version'] = {'$lt': annotation['_version']}
        else:
            query['_version'] = {'$lte': oldversion}
        self.model('annotationelement', 'large_image').removeWithQuery(query)

    def updateElements(self, annotation):
        """
        Given an annotation, extract the elements from it and update the
        database of them.

        :param annotation: the annotation to save elements for.  Modified.
        """
        elements = annotation['annotation'].get('elements', [])
        if len(elements):
            now = datetime.datetime.utcnow()
            res = self.collection.insert_many([{
                'annotationId': annotation['_id'],
                '_version': annotation['_version'],
                'created': now,
                'element': element
            } for element in elements])
            for pos in range(len(elements)):
                if 'id' not in elements[pos]:
                    elements[pos]['id'] = str(res.inserted_ids[pos])
