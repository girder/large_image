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

import itertools
import math
import time

from girder import logger
from girder.api import access
from girder.api.describe import Description, autoDescribeRoute, describeRoute
from girder.api.rest import boundHandler, loadmodel
from girder.constants import AccessType, TokenScope
from girder.models.item import Item


def convenient_range(minr, maxr, bins, padmax=True, exact=None):
    padval = 0.000001
    if minr > maxr:
        minr, maxr = maxr, minr
    deltar = maxr - minr
    if not deltar:
        stepr = 10 ** math.floor(math.log10(max(abs(minr), abs(maxr)) / bins))
    else:
        if padmax:
            maxr = (maxr + deltar * padval) if math.ceil(
                maxr) == maxr or math.ceil(maxr) > maxr + deltar * padval else math.ceil(maxr)
            deltar = maxr - minr
        stepr = 10 ** math.floor(math.log10(deltar / bins))
    for ex, fac in itertools.product([True, False] if exact else [False], [1, 2, 4, 5, 10]):
        stepc = stepr * fac
        minc = int(math.floor(minr / stepc))
        maxc = int(math.ceil(maxr / stepc))
        binsc = maxc - minc
        if binsc <= bins:
            if not ex or (len(exact) == binsc and all(
                    abs(((((val / stepc) % 1) + 1.5) % 1) - 0.5) < padval for val in exact)):
                break
    minc *= stepc
    maxc *= stepc
    return minc, maxc, stepc, binsc


def _facetMetalist(metalist, query, querysub, limit, start):
    """
    Given a list of metadata to query, an initial filtering query and,
    optionally, a more restrictive subquery, determine the count, min, max, and
    enum grouping of the metadata.  The subquery results should be a subset of
    the main query.

    :param metadata: a list of metadata.  Each entry contains a `key` which is
        the metadata to query (e.g., 'meta.rating').  These can be primary keys
        of items, too.
    :param query: A query that determines which items to facet.
    :param querysub: An optional query that should be a subset of the primary
        query.  None to skip.
    :param limit: The maximum number of values to return for an enum datatype.
    :param start: The start epoch used for logging times.
    :returns: A facet dictionary used for processing internal results, the
        pipeline and subpipeline used for the aggregations, and the result and
        subresult with the query results.
    """
    facet = {}
    for idx, entry in enumerate(metalist):
        facet[f'summary{idx}'] = [
            {'$group': {
                '_id': None,
                'count': {'$sum': 1},
                'max': {'$max': '$' + entry['key']},
                'min': {'$min': '$' + entry['key']},
                # 'sum': {'$sum': '$' + entry['key']},
            }},
        ]
        if True:  # don't do this if numeric
            facet[f'enum{idx}'] = [
                {'$group': {
                    '_id': '$' + entry['key'],
                    'count': {'$sum': 1},
                }},
                # {'$sort': {'count': -1}},
                {'$limit': limit + 1},
            ]
    pipeline = [{'$match': query}, {'$facet': facet}]
    logger.info('Facet pipeline: %r', pipeline)
    result = next(Item().collection.aggregate(pipeline))
    logger.info('Facet time: pipeline - %5.3f', (time.time() - start))
    subresult = None
    subpipeline = None
    if querysub:
        subpipeline = [{'$match': querysub}, {'$facet': facet}]
        subresult = next(Item().collection.aggregate(subpipeline))
        logger.info('Facet time: subpipeline - %5.3f', (time.time() - start))
    return facet, pipeline, subpipeline, result, subresult


def _facetCollectResults(metalist, facet, result, subresult, limit, bins):
    """
    Given the results of the _facetMetalist method, collect it into the
    metalist and generate a new facet aggregation to obtain a histogram.

    :param metalist: the list of metadata that was queried.  Entries get count,
        min, max, and possibly enum added to them.  If a subquery was applied,
        they also have subcount, submin, submax, and subenum.
    :param facet: a facet dictionary that will be reused for histograms.
    :param result: the result from _facetMetalist.
    :param subresult: the subresult from _facetMetalist.
    :param limit: The maximum number of values to return for an enum datatype.
    :param bins: The maximum number of bins for a histogram.
    :param start: The start epoch used for logging times.
    """
    facet.clear()
    for idx, entry in enumerate(metalist):
        if not len(result[f'summary{idx}']):
            continue
        summary = result[f'summary{idx}'][0]
        subsummary = None
        if subresult:
            subsummary = subresult[f'summary{idx}'][0]
        for key in summary:
            if key != '_id':
                entry[key] = summary[key]
                if subsummary:
                    entry[f'sub{key}'] = subsummary[key]
        records = result.get(f'enum{idx}', None)
        if records and len(records) <= limit:
            entry['enum'] = {
                record['_id']: record['count'] for record in records
                if record['_id'] is not None}
            if subsummary:
                subrecords = subresult.get(f'enum{idx}', None)

                subenum = {record['_id']: record['count'] for record in subrecords}
                entry['subenum'] = {key: subenum.get(key, 0) for key in entry['enum']}
        minr = entry['min']
        maxr = entry['max']
        if (minr != maxr and isinstance(minr, (int, float)) and
                isinstance(maxr, (int, float)) and 'enum' not in entry):
            minr, maxr, step, binsr = convenient_range(minr, maxr, bins)
            entry['histrange'] = [minr, maxr, step, binsr]
            entry['histboundaries'] = [minr + step * i for i in range(binsr + 1)]
            facet[f'hist{idx}'] = [
                {'$bucket': {
                    'groupBy': '$' + entry['key'],
                    'boundaries': entry['histboundaries'],
                    'default': maxr,
                }},
            ]


def _facetHistogram(metalist, pipeline, subpipeline, start):
    """
    Perform an aggregation to get appropriate histograms and add them to the
    metalist.

    :param metalist: the list of metadata that was queried.  Entries may have
        hist and subhist added to them.  They will also have histrange and
        histboundaries, where histrange is the min, max, step, and number of
        bins used for the histogram, and histboundaries is a list of the
        histogram edges.
    :param pipeline: The aggregation pipeline which uses the query and facet to
        get the histogram.
    :param subpipleine: The aggregation pipeline for the subquery, or None.
    :param start: The start epoch used for logging times.
    """
    logger.info('Facet histogram pipeline: %r', pipeline)
    result = next(Item().collection.aggregate(pipeline))
    logger.info('Facet time: histogram - %5.3f', (time.time() - start))
    if subpipeline:
        subresult = next(Item().collection.aggregate(subpipeline))
        logger.info('Facet time: subhistogram - %5.3f', (time.time() - start))
    for idx, entry in enumerate(metalist):
        hist = result.get(f'hist{idx}', None)
        if hist:
            entry['hist'] = {record['_id']: record['count'] for record in hist
                             if record['_id'] != entry['histboundaries'][-1]}
            if subpipeline:
                subhist = subresult.get(f'hist{idx}', None)
                entry['subhist'] = {record['_id']: record['count'] for record in subhist}


def addItemEndpoints(apiRoot):  # noqa
    @boundHandler(apiRoot.item)
    @describeRoute(
        Description('Get the value for a single internal metadata key on this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key to retrieve.',
            paramType='path',
            default='meta',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Read access was denied for the item.', 403),
    )
    @access.public()
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def getMetadataKey(self, item, key, params):
        if key not in item:
            return None
        return item[key]

    @boundHandler(apiRoot.item)
    @describeRoute(
        Description(
            'Overwrite the value for a single internal metadata key on this item.',
        )
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key which should have a new value. \
                The default key, "meta" is equivalent to the external metadata. \
                Editing the "meta" key is equivalent to using PUT /item/{id}/metadata.',
            paramType='path',
            default='meta',
        )
        .param(
            'value',
            'The new value that should be written for the chosen metadata key',
            paramType='body',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403),
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.WRITE)
    def updateMetadataKey(self, item, key, params):
        item[key] = self.getBodyJson()
        self._model.save(item)

    @boundHandler(apiRoot.item)
    @describeRoute(
        Description('Delete a single internal metadata key on this item.')
        .param('itemId', 'The ID of the item.', paramType='path')
        .param(
            'key',
            'The metadata key to delete.',
            paramType='path',
            default='meta',
        )
        .errorResponse('ID was invalid.')
        .errorResponse('Write access was denied for the item.', 403),
    )
    @access.user(scope=TokenScope.DATA_WRITE)
    @loadmodel(model='item', map={'itemId': 'item'}, level=AccessType.READ)
    def deleteMetadataKey(self, item, key, params):
        if key in item:
            del item[key]
        self._model.save(item)

    @boundHandler(apiRoot.item)
    @access.public(scope=TokenScope.DATA_READ)
    @autoDescribeRoute(
        Description('Get facet information for items based on metadata.')
        .notes('You must pass either a "folderId" or "text" field '
               'to specify how you are searching for items.  '
               'If you omit one of these parameters the request will fail and respond : '
               '"Invalid search mode."')
        .param('folderId', 'Pass this to list all items in a folder.',
               required=False)
        .param('text', 'Pass this to perform a full text search for items.',
               required=False)
        .param('textsub', 'Pass this to perform a sub query.',
               required=False)
        .jsonParam('metalist', 'A JSON-encoded list of metadata keys to facet.',
                   requireObject=False)
        .errorResponse()
        .errorResponse('Read access was denied on the parent folder.', 403),
    )
    def facetMetadata(self, folderId, text, textsub, metalist):
        """
        See find for how folderId and text are used.
        """
        start = time.time()
        query = self._find(folderId, text, None, 0, 0, None)._Cursor__spec
        logger.info('Facet time: first query - %5.3f', (time.time() - start))
        querysub = None
        if textsub and textsub != text:
            querysub = self._find(folderId, textsub, None, 0, 0, None)._Cursor__spec
            logger.info('Facet time: subquery - %5.3f', (time.time() - start))
        metalist = [entry if isinstance(entry, dict) else {'key': entry} for entry in metalist]
        limit = 20
        bins = 20
        facet, pipeline, subpipeline, result, subresult = _facetMetalist(
            metalist, query, querysub, limit, start)
        _facetCollectResults(metalist, facet, result, subresult, limit, bins)
        if len(facet):
            _facetHistogram(metalist, pipeline, subpipeline, start)
        logger.info('Facet time: total - %5.3f', (time.time() - start))
        return metalist

    apiRoot.item.route(
        'GET', (':itemId', 'internal_metadata', ':key'), getMetadataKey,
    )
    apiRoot.item.route(
        'PUT', (':itemId', 'internal_metadata', ':key'), updateMetadataKey,
    )
    apiRoot.item.route(
        'DELETE', (':itemId', 'internal_metadata', ':key'), deleteMetadataKey,
    )
    apiRoot.item.route('GET', ('facet', ), facetMetadata)
