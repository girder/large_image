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
import math
import time
from six.moves import range

from girder.constants import AccessType, SortDir
from girder.models.model_base import Model
from girder import logger


class Annotationelement(Model):
    bboxKeys = {
        'left': ('bbox.high.0', '$gte'),
        'right': ('bbox.low.0', '$lt'),
        'top': ('bbox.high.1', '$gte'),
        'bottom': ('bbox.low.1', '$lt'),
        'low': ('bbox.high.2', '$gte'),
        'high': ('bbox.low.2', '$lt'),
        'minimumSize': ('bbox.size', '$gte'),
        'size': ('bbox.size', None),
        'details': ('bbox.details', None),
    }

    def initialize(self):
        self.name = 'annotationelement'
        self.ensureIndices([
            'annotationId', '_version', ([
                ('annotationId', SortDir.ASCENDING),
                ('bbox.low.0', SortDir.ASCENDING),
                ('bbox.low.1', SortDir.ASCENDING),
                ('bbox.size', SortDir.ASCENDING),
            ], {}), ([
                ('annotationId', SortDir.ASCENDING),
                ('bbox.size', SortDir.DESCENDING),
            ], {})
        ])

        # self.model('file').ensureIndices([([
        #     ('isLargeImageThumbnail', pymongo.ASCENDING),
        #     ('attachedToType', pymongo.ASCENDING),
        #     ('attachedToId', pymongo.ASCENDING),
        # ], {})])

        self.exposeFields(AccessType.READ, (
            '_id', '_version', 'annotationId', 'created', 'element'))
        self.versionId = None

    def getNextVersionValue(self):
        """
        Maintain a version number.  This is a single sequence that can be used
        to ensure we have the correct set of elements for an annotation.

        :returns: an integer version number that is strictly increasing.
        """
        version = None
        if self.versionId is not None:
            version = self.collection.find_one_and_update(
                {'_id': self.versionId},
                {'$inc': {'_version': 1}})
        if version is None:
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

    def getElements(self, annotation, region=None):
        """
        Given an annotation, fetch the elements from the database and add them
        to it.

        :param annotation: the annotation to get elements for.  Modified.
        :param region: if present, a dictionary restricting which annotations
            are returned.
        """
        region = region or {}
        query = {
            'annotationId': annotation['_id'],
            '_version': annotation['_version']
        }
        for key in region:
            if key in self.bboxKeys and self.bboxKeys[key][1]:
                query[self.bboxKeys[key][0]] = {
                    self.bboxKeys[key][1]: float(region[key])}
        if region.get('sort') in self.bboxKeys:
            sortkey = self.bboxKeys[region['sort']][0]
        else:
            sortkey = region.get('sort') or '_id'
        sortdir = int(region['sortdir']) if region.get('sortdir') else SortDir.ASCENDING
        limit = int(region['limit']) if region.get('limit') else 0
        offset = int(region['offset']) if region.get('offset') else 0
        elementCursor = self.find(
            query=query, sort=[(sortkey, sortdir)], limit=limit, offset=offset,
            fields={'_id': True, 'element': True, 'bbox.details': True})
        annotation['annotation']['elements'] = []

        _elementQuery = {
            'count': elementCursor.count(),
            'offset': offset,
            'filter': query,
            'sort': [sortkey, sortdir],
        }
        details = 0
        maxDetails = int(region.get('maxDetails') or 0)
        if maxDetails:
            _elementQuery['maxDetails'] = maxDetails
        if limit:
            _elementQuery['limit'] = limit
        for entry in elementCursor:
            element = entry['element']
            element.setdefault('id', entry['_id'])
            annotation['annotation']['elements'].append(element)
            details += entry.get('bbox', {}).get('details', 1)
            if maxDetails and details >= maxDetails:
                break
        _elementQuery['returned'] = len(annotation['annotation']['elements'])
        _elementQuery['details'] = details
        if region != {}:
            annotation['_elementQuery'] = _elementQuery

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

    def _boundingBox(self, element):
        """
        Compute bounding box information for an annotation element.

        This computes the enclosing bounding box of an element.  For points, an
        small non-zero-area region is used centered on the point.
        Additionally, a metric is stored for the complexity of the element.
        The size of the bounding box's x-y diagonal is also stored.

        :param element: the element to compute the bounding box for.
        :returns: the bounding box dictionary.  This contains 'low' and 'high,
            a pair of x-y-z coordinates with the minimum and maximum values in
            each dimension, 'details' with the complexity of the element, and
            'size' with the x-y diagonal size of the bounding box.
        """
        bbox = {}
        if 'points' in element:
            bbox['low'] = [
                min([p[0] for p in element['points']]),
                min([p[1] for p in element['points']]),
                min([p[2] for p in element['points']]),
            ]
            bbox['high'] = [
                max([p[0] for p in element['points']]),
                max([p[1] for p in element['points']]),
                max([p[2] for p in element['points']]),
            ]
            bbox['details'] = len(element['points'])
        else:
            center = element['center']
            if 'width' in element:
                w = element['width'] * 0.5
                h = element['height'] * 0.5
                if element.get('rotation'):
                    absin = abs(math.sin(element['rotation']))
                    abcos = abs(math.cos(element['rotation']))
                    w, h = max(abcos * w, absin * h), max(absin * w, abcos * h)
                bbox['low'] = [center[0] - w, center[1] - h, center[2]]
                bbox['high'] = [center[0] + w, center[1] + h, center[2]]
                bbox['details'] = 4
            elif 'radius' in element:
                rad = element['radius']
                bbox['low'] = [center[0] - rad, center[1] - rad, center[2]]
                bbox['high'] = [center[0] + rad, center[1] + rad, center[2]]
                bbox['details'] = 4
            else:
                # This is a fall back for points.  Although they have no
                # dimension, make the bounding box have some extent.
                rad = 0.5
                bbox['low'] = [center[0] - rad, center[1] - rad, center[2]]
                bbox['high'] = [center[0] + rad, center[1] + rad, center[2]]
                bbox['details'] = 1
        bbox['size'] = (
            (bbox['high'][1] - bbox['low'][1])**2 +
            (bbox['high'][0] - bbox['low'][0])**2) ** 0.5
        return bbox

    def updateElements(self, annotation):
        """
        Given an annotation, extract the elements from it and update the
        database of them.

        :param annotation: the annotation to save elements for.  Modified.`
        """
        startTime = time.time()
        elements = annotation['annotation'].get('elements', [])
        if not len(elements):
            return
        now = datetime.datetime.utcnow()
        chunkSize = 100000
        for chunk in range(0, len(elements), chunkSize):
            chunkStartTime = time.time()
            entries = [{
                'annotationId': annotation['_id'],
                '_version': annotation['_version'],
                'created': now,
                'bbox': self._boundingBox(element),
                'element': element
            } for element in elements[chunk:chunk + chunkSize]]
            prepTime = time.time() - chunkStartTime
            res = self.collection.insert_many(entries)
            for pos in range(len(entries)):
                if 'id' not in entries[pos]['element']:
                    entries[pos]['element']['id'] = str(res.inserted_ids[pos])
            # If the whole insert is slow, log information about it.
            if time.time() - startTime > 10:
                logger.info('insert %d elements in %4.2fs (prep time %4.2fs), done %d/%d' % (
                    len(entries), time.time() - chunkStartTime, prepTime,
                    chunk + len(entries), len(elements)))
        if time.time() - startTime > 10:
            logger.info('inserted %d elements in %4.2fs' % (
                len(elements), time.time() - startTime))
