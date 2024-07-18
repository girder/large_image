import itertools
import json
import math
import re

from bson.objectid import ObjectId

from girder import logger
from girder.constants import AccessType
from girder.models.folder import Folder


class AnnotationGeoJSON:
    """
    Generate GeoJSON for an annotation via an iterator.
    """

    def __init__(self, annotationId, asFeatures=False, mustConvert=False):
        """
        Return an itertor for converting an annotation into geojson.

        :param annotatioId: the id of the annotation.  No permissions checks
            are performed.
        :param asFeatures: if False, return a geojson string.  If True, return
            the features of the geojson.  This can be wrapped in
            `{'type': 'FeatureCollection', 'features: [...output...]}`
            to make it a full geojson object.
        :param mustConvert: if True, raise an exception if any annotation
            elements cannot be converted.  Otherwise, skip those elements.
        """
        from ..models.annotation import Annotation
        from ..models.annotationelement import Annotationelement

        self._id = annotationId
        self.annotation = Annotation().load(id=self._id, force=True, getElements=False)
        self.elemIterator = Annotationelement().yieldElements(self.annotation)
        self.stage = 'header'
        self.first = self.annotation['annotation']
        self.asFeatures = asFeatures
        self.mustConvert = mustConvert

    def __iter__(self):
        from ..models.annotationelement import Annotationelement

        self.elemIterator = Annotationelement().yieldElements(self.annotation)
        self.stage = 'header'
        return self

    def __next__(self):
        if self.stage == 'header':
            self.stage = 'firstelement'
            if not self.asFeatures:
                return '{"type":"FeatureCollection","features":['
        if self.stage == 'done':
            raise StopIteration
        try:
            while True:
                element = next(self.elemIterator)
                result = self.elementToGeoJSON(element)
                if result is not None:
                    break
                if self.mustConvert:
                    msg = f'Element of type {element["type"]} cannot be represented as geojson'
                    raise Exception(msg)
            prefix = ''
            if self.stage == 'firstelement':
                result['properties']['annotation'] = self.first
                self.stage = 'elements'
            else:
                prefix = ','
            if not self.asFeatures:
                return prefix + json.dumps(result, separators=(',', ':'))
            return result
        except StopIteration:
            self.stage = 'done'
            if not self.asFeatures:
                return ']}'
            raise

    def rotate(self, r, cx, cy, x, y, z):
        if not r:
            return [x, y, z]
        cosr = math.cos(r)
        sinr = math.sin(r)
        x -= cx
        y -= cy
        return [x * cosr - y * sinr + cx, x * sinr + y * sinr + cy, z]

    def circleType(self, element, geom, prop):
        x, y, z = element['center']
        r = element['radius']
        geom['type'] = 'Polygon'
        geom['coordinates'] = [[
            [x - r, y - r, z],
            [x + r, y - r, z],
            [x + r, y + r, z],
            [x - r, y + r, z],
            [x - r, y - r, z],
        ]]

    def ellipseType(self, element, geom, prop):
        return self.rectangleType(element, geom, prop)

    def pointType(self, element, geom, prop):
        geom['type'] = 'Point'
        geom['coordinates'] = element['center']

    def polylineType(self, element, geom, prop):
        if element['closed']:
            geom['type'] = 'Polygon'
            geom['coordinates'] = [element['points'][:]]
            geom['coordinates'][0].append(geom['coordinates'][0][0])
            if element.get('holes'):
                for hole in element['holes']:
                    hole = hole[:]
                    hole.append(hole[0])
                    geom['coordinates'].append(hole)
        else:
            geom['type'] = 'LineString'
            geom['coordinates'] = element['points']

    def rectangleType(self, element, geom, prop):
        x, y, z = element['center']
        width = element['width']
        height = element['height']
        rotation = element.get('rotation', 0)
        left = x - width / 2
        right = x + width / 2
        top = y - height / 2
        bottom = y + height / 2

        geom['type'] = 'Polygon'
        geom['coordinates'] = [[
            self.rotate(rotation, x, y, left, top, z),
            self.rotate(rotation, x, y, right, top, z),
            self.rotate(rotation, x, y, right, bottom, z),
            self.rotate(rotation, x, y, left, bottom, z),
            self.rotate(rotation, x, y, left, top, z),
        ]]

    # not represented
    # heatmap, griddata, image, pixelmap, arrow, rectanglegrid
    # heatmap could be MultiPoint, griddata could be rectangle with lots of
    # properties, image and pixelmap could be rectangle with the image id as a
    # property, arrow and rectangelgrid aren't really supported

    def elementToGeoJSON(self, element):
        elemType = element.get('type', '')
        funcName = elemType + 'Type'
        if not hasattr(self, funcName):
            return None
        result = {
            'type': 'Feature',
            'geometry': {},
            'properties': {
                k: v if k != 'id' else str(v)
                for k, v in element.items() if k in {
                    'id', 'label', 'group', 'user', 'lineColor', 'lineWidth',
                    'fillColor', 'radius', 'width', 'height', 'rotation',
                    'normal',
                }
            },
        }
        getattr(self, funcName)(element, result['geometry'], result['properties'])
        if result['geometry']['type'].lower() != element['type']:
            result['properties']['type'] = element['type']
        return result

    @property
    def geojson(self):
        return ''.join(self)


class GeoJSONAnnotation:
    def __init__(self, geojson):
        if not isinstance(geojson, (dict, list, tuple)):
            geojson = json.loads(geojson)
        self._elements = []
        self._annotation = {'elements': self._elements}
        self._parseFeature(geojson)

    def _parseFeature(self, geoelem):
        if isinstance(geoelem, (list, tuple)):
            for entry in geoelem:
                self._parseFeature(entry)
        if not isinstance(geoelem, dict) or 'type' not in geoelem:
            return
        if geoelem['type'] == 'FeatureCollection':
            return self._parseFeature(geoelem.get('features', []))
        if geoelem['type'] == 'GeometryCollection' and isinstance(geoelem.get('geometries'), list):
            for entry in geoelem['geometry']:
                self._parseFeature({'type': 'Feature', 'geometry': entry})
            return
        if geoelem['type'] in {'Point', 'LineString', 'Polygon', 'MultiPoint',
                               'MultiLineString', 'MultiPolygon'}:
            geoelem = {'type': 'Feature', 'geometry': geoelem}
        element = {k: v for k, v in geoelem.get('properties', {}).items() if k in {
            'id', 'label', 'group', 'user', 'lineColor', 'lineWidth',
            'fillColor', 'radius', 'width', 'height', 'rotation',
            'normal',
        }}
        if 'annotation' in geoelem.get('properties', {}):
            self._annotation.update(geoelem['properties']['annotation'])
            self._annotation['elements'] = self._elements
        elemtype = geoelem.get('properties', {}).get('type', '') or geoelem['geometry']['type']
        func = getattr(self, elemtype.lower() + 'Type', None)
        if func is not None:
            result = func(geoelem['geometry'], element)
            if isinstance(result, list):
                self._elements.extend(result)
            else:
                self._elements.append(result)

    def circleType(self, elem, result):
        cx = sum(e[0] for e in elem['coordinates'][0][:4]) / 4
        cy = sum(e[1] for e in elem['coordinates'][0][:4]) / 4
        try:
            cz = elem['coordinates'][0][0][2]
        except Exception:
            cz = 0
        radius = (max(e[0] for e in elem['coordinates'][0][:4]) -
                  min(e[0] for e in elem['coordinates'][0][:4])) / 2
        result['type'] = 'circle'
        result['radius'] = radius
        result['center'] = [cx, cy, cz]
        return result

    def ellipseType(self, elem, result):
        result = self.rectangleType(elem, result)
        result['type'] = 'ellipse'
        return result

    def rectangleType(self, elem, result):
        coor = elem['coordinates'][0]
        cx = sum(e[0] for e in coor[:4]) / 4
        cy = sum(e[1] for e in coor[:4]) / 4
        try:
            cz = elem['coordinates'][0][0][2]
        except Exception:
            cz = 0
        width = ((coor[0][0] - coor[1][0]) ** 2 + (coor[0][1] - coor[1][1]) ** 2) ** 0.5
        height = ((coor[1][0] - coor[2][0]) ** 2 + (coor[1][1] - coor[2][1]) ** 2) ** 0.5
        rotation = math.atan2(coor[1][1] - coor[0][1], coor[1][0] - coor[0][0])
        result['center'] = [cx, cy, cz]
        result['width'] = width
        result['height'] = height
        result['rotation'] = rotation
        result['type'] = 'rectangle'
        return result

    def pointType(self, elem, result):
        result['center'] = (elem['coordinates'] + [0, 0, 0])[:3]
        result['type'] = 'point'
        return result

    def multipointType(self, elem, result):
        results = []
        result['type'] = 'point'
        for entry in elem['coordinates']:
            subresult = result.copy()
            subresult['center'] = (entry + [0, 0, 0])[:3]
            results.append(subresult)
        return results

    def polylineType(self, elem, result):
        if elem.get('type') == 'LineString':
            return self.linestringType(elem, result)
        return self.polygonType(elem, result)

    def polygonType(self, elem, result):
        result['points'] = [(pt + [0])[:3] for pt in elem['coordinates'][0][:-1]]
        if len(elem['coordinates']) > 1:
            result['holes'] = [
                [(pt + [0])[:3] for pt in loop[:-1]]
                for loop in elem['coordinates'][1:]
            ]
        result['closed'] = True
        result['type'] = 'polyline'
        return result

    def multipolygonType(self, elem, result):
        results = []
        result['closed'] = True
        result['type'] = 'polyline'
        for entry in elem['coordinates']:
            subresult = result.copy()
            subresult['points'] = [(pt + [0])[:3] for pt in entry[0][:-1]]
            if len(entry) > 1:
                subresult['holes'] = [
                    [(pt + [0])[:3] for pt in loop[:-1]]
                    for loop in entry[1:]
                ]
            results.append(subresult)
        return results

    def linestringType(self, elem, result):
        result['points'] = [(pt + [0])[:3] for pt in elem['coordinates']]
        result['closed'] = False
        result['type'] = 'polyline'
        return result

    def multilinestringType(self, elem, result):
        results = []
        result['closed'] = False
        result['type'] = 'polyline'
        for entry in elem['coordinates']:
            subresult = result.copy()
            subresult['points'] = [(pt + [0])[:3] for pt in entry]
            results.append(subresult)
        return results

    def annotationToJSON(self):
        return json.dumps(self._annotation)

    @property
    def annotation(self):
        return self._annotation

    @property
    def elements(self):
        return self._elements

    @property
    def elementCount(self):
        return len(self._elements)


def isGeoJSON(annotation):
    """
    Check if a list or dictionary appears to contain a GeoJSON record.

    :param annotation: a list or dictionary.
    :returns: True if this appears to be GeoJSON
    """
    if isinstance(annotation, list):
        if len(annotation) < 1:
            return False
        annotation = annotation[0]
    if not isinstance(annotation, dict) or 'type' not in annotation:
        return False
    return annotation['type'] in {
        'Feature', 'FeatureCollection', 'GeometryCollection', 'Point',
        'LineString', 'Polygon', 'MultiPoint', 'MultiLineString',
        'MultiPolygon'}


class PlottableItemData:
    maxItems = 1000
    maxAnnotationElements = 10000
    maxDistinct = 20
    allowedTypes = (str, bool, int, float)

    def __init__(self, user, item, annotations=None, adjacentItems=False):
        """
        Get plottable data associated with an item.

        :param user: authenticating user.
        :param item: the item record.
        :param annotations: None, a list of annotation ids, or __all__.  If
            adjacent items are included, the most recent annotation with the
            same name will also be included.
        :param adjacentItems: if True, include data other items in the same
            folder.
        """
        self.user = user
        self._columns = None
        self._datacolumns = None
        self._data = None
        self._findItems(item, adjacentItems)
        self._findAnnotations(annotations)

    def _findItems(self, item, adjacentItems=False):
        self._columns = None
        self.item = item
        self.folder = Folder().load(id=item['folderId'], user=self.user, level=AccessType.READ)
        self.items = [item]
        if adjacentItems:
            for entry in Folder().childItems(self.folder):
                if len(self.items) >= self.maxItems:
                    break
                if entry['_id'] != item['_id']:
                    # skip if item doesn't have appropriate metadata or
                    # annotations.  If skipping, add to list to check if
                    # dataframe
                    self.items.append(entry)
        # TODO: find csv/xlsx/dataframe items in the folder, exclude them from
        # the item list but include them in general

    def _findAnnotations(self, annotations):
        from ..models.annotation import Annotation

        self._columns = None
        if isinstance(annotations, str):
            annotations = annotations.split(',')
        self.annotations = None
        if annotations and len(annotations):
            self.annotations = []
            query = {'_active': {'$ne': False}, 'itemId': self.item['_id']}
            if annotations[0] != '__all__':
                query['_id'] = {'$in': [ObjectId(annotId) for annotId in annotations]}
            self.annotations.append(list(Annotation().find(
                query, limit=0, sort=[('_version', -1)])))
            if not len(self.annotations[0]):
                self.annotations = None
        # Find adjacent annotations
        if annotations and len(self.items) > 1:
            names = {}
            for idx, annot in enumerate(self.annotations[0]):
                if annot['annotation']['name'] not in names:
                    names[annot['annotation']['name']] = idx
            for adjitem in self.items[1:]:
                query = {'_active': {'$ne': False}, 'itemId': adjitem['_id']}
                annotList = [None] * len(self.annotations[0])
                for annot in Annotation().find(query, limit=0, sort=[('_version', -1)]):
                    if annot['annotation']['name'] in names and annotList[
                            names[annot['annotation']['name']]] is None:
                        annotList[names[annot['annotation']['name']]] = annot
                self.annotations.append(annotList)

    def _addColumn(self, columns, fullkey, title, root, key, source):
        # Root should probably only be part of this at folder/csv level
        distinct = [source] if source not in {'folder'} else [source, root]
        if fullkey not in columns:
            columns[fullkey] = {
                'key': fullkey,
                'type': 'number',
                'where': [[distinct, key]], 'title': title,
                'count': 0, 'distinct': set(), 'min': None,
                'max': None}
            return (tuple(distinct), 0)
        elif [root, key, source] not in columns[fullkey]['where']:
            columns[fullkey]['where'].append([distinct, key])
        where = -1
        for colwhere in columns[fullkey]['where']:
            if tuple(colwhere[0]) == tuple(distinct):
                where += 1
                if colwhere[1] == key:
                    return (tuple(distinct), where)
        return (tuple(distinct), where)

    def _columnKey(self, source, root, key):
        if not hasattr(self, '_columnKeyCache'):
            self._columnKeyCache = {}
        hashkey = (source, root, key)
        if hashkey in self._columnKeyCache:
            return self._columnKeyCache[hashkey]
        fullkey = f'{root}.{key}.{source}'.lower()
        title = f'{root} {key}' if root is not None and root != '' else f'{key}'
        keymap = {
            r'(?i)(item|image)_(id|name)$': {'key': '_0_item.name', 'title': 'Item Name'},
            r'(?i)(low|min)(_|)x': {'key': '_bbox.x0', 'title': 'Bounding Box Low X'},
            r'(?i)(low|min)(_|)y': {'key': '_bbox.y0', 'title': 'Bounding Box Low Y'},
            r'(?i)(high|max)(_|)x': {'key': '_bbox.x1', 'title': 'Bounding Box High X'},
            r'(?i)(high|max)(_|)y': {'key': '_bbox.y1', 'title': 'Bounding Box High Y'},
        }
        for k, v in keymap.items():
            if re.match(k, key):
                fullkey = v['key']
                title = v['title']
                break
        self._columnKeyCache[hashkey] = fullkey, title
        return fullkey, title

    def _scanColumnByKey(self, result, key, entry, where=0, auxidx=0,
                         auxidx2=0, item=None, annotation=None):
        if result['type'] == 'number':
            try:
                [float(record[key]) for record in entry
                 if isinstance(record.get(key), self.allowedTypes)]
            except Exception:
                result['type'] = 'string'
                result['distinct'] = {str(v) for v in result['distinct']}
        for ridx, record in enumerate(entry):
            v = record.get(key)
            if not isinstance(v, self.allowedTypes):
                continue
            result['count'] += 1
            v = float(v) if result['type'] == 'number' else str(v)
            if len(result['distinct']) <= self.maxDistinct:
                result['distinct'].add(v)
            if result['type'] == 'number':
                if result['min'] is None:
                    result['min'] = result['max'] = v
                result['min'] = min(result['min'], v)
                result['max'] = max(result['max'], v)
            if self._datacolumns and result['key'] in self._datacolumns:
                self._datacolumns[result['key']][(where, (auxidx, auxidx2, ridx))] = v
                if item is not None:
                    self._datacolumns.get('_0_item.name', {})[
                        (where, (auxidx, auxidx2, ridx))] = item['name']
                    self._datacolumns.get('_2_item.id', {})[
                        (where, (auxidx, auxidx2, ridx))] = str(item['_id'])
                if annotation is not None:
                    self._datacolumns.get('_1_annotation.name', {})[
                        (where, (auxidx, auxidx2, ridx))] = annotation.get(
                            'annotation', {}).get('name')
                    self._datacolumns.get('_3_annotation.id', {})[
                        (where, (auxidx, auxidx2, ridx))] = str(annotation['_id'])
                    self._datacolumns.get('_4_annotation.description', {})[
                        (where, (auxidx, auxidx2, ridx))] = annotation.get(
                            'annotation', {}).get('description')

    def _scanColumn(self, meta, source, columns, auxmeta=None, auxidx2=0,
                    items=None, annotations=None):
        for root, entry in (list(meta.items()) + [(None, [meta])]):
            if not isinstance(entry, list) or not len(entry) or not isinstance(entry[0], dict):
                continue
            for key in entry[0]:
                if not isinstance(entry[0][key], self.allowedTypes):
                    continue
                fullkey, title = self._columnKey(source, root, key)
                where = self._addColumn(
                    columns, fullkey, title, root, key, source)
                result = columns[fullkey]
                self._scanColumnByKey(
                    result, key, entry, where, 0, auxidx2,
                    items[0] if items and len(items) > 0 else None,
                    annotations[0] if annotations and len(annotations) > 0 else None)
                if auxmeta:
                    for auxidx, aux in enumerate(auxmeta):
                        if root is None:
                            if isinstance(aux, dict) and key in aux:
                                self._scanColumnByKey(
                                    result, key, [aux], where, auxidx + 1, auxidx2,
                                    items[auxidx + 1] if items and len(items) > auxidx + 1 else
                                    None,
                                    annotations[auxidx + 1]
                                    if annotations and len(annotations) > auxidx + 1 else
                                    None)
                        elif (isinstance(aux.get(root), list) and
                                len(aux[root]) and
                                isinstance(aux[root][0], dict) and
                                key in aux[root][0]):
                            self._scanColumnByKey(
                                result, key, aux[root], where, auxidx + 1, auxidx2,
                                items[auxidx + 1] if items and len(items) > auxidx + 1 else None,
                                annotations[auxidx + 1] if annotations and
                                len(annotations) > auxidx + 1 else None)

    def _scanElementColumns(self, source, columns, elems, auxidx, items, annotations, keys):
        rows = {}
        for ridx, elem in enumerate(elems):
            if auxidx < len(items) and items[auxidx]:
                rows.setdefault('_0_item.name', []).append(items[auxidx]['name'])
                rows.setdefault('_2_item.id', []).append(str(items[auxidx]['_id']))
            if auxidx < len(annotations) and annotations[auxidx]:
                rows.setdefault('_1_annotation.name', []).append(
                    annotations[auxidx].get('annotation', {}).get('name'))
                rows.setdefault('_3_annotation.id', []).append(str(annotations[auxidx]['_id']))
                rows.setdefault('_4_annotation.description', []).append(
                    annotations[auxidx].get('annotation', {}).get('description'))
            rows.setdefault('_5_annotationelement.id', []).append(str(elem['id']))
            rows.setdefault('annotationelement.group', []).append(
                elem.get('group') or None)
            rows.setdefault('annotationelement.label', []).append(
                elem.get('label', {}).get('value') or None)
            if '_bbox' in elem:
                rows.setdefault('_bbox.x0', []).append(elem['_bbox']['lowx'])
                rows.setdefault('_bbox.y0', []).append(elem['_bbox']['lowy'])
                rows.setdefault('_bbox.x1', []).append(elem['_bbox']['highx'])
                rows.setdefault('_bbox.y1', []).append(elem['_bbox']['highy'])
            # TODO: Add group and label
            if not auxidx and not ridx and 'user' in elem:
                for key, entry in elem['user'].items():
                    if not isinstance(entry, self.allowedTypes):
                        continue
                    root = ''
                    fullkey, title = self._columnKey(source, root, key)
                    colwhere = self._addColumn(
                        columns, fullkey, title, root, key, source)
                    keys[key] = (fullkey, colwhere)
            # TODO: Populate group and label
            for key, (fullkey, _keywhere) in keys.items():
                entry = elem.get('user', {}).get(key)
                if not isinstance(entry, self.allowedTypes):
                    entry = None
                rows.setdefault(fullkey, []).append(entry)
        return rows

    def _scanElements(self, elements, source, columns, auxidx2, items, annotations):
        where = self._addColumn(
            columns, '_0_item.name', 'Item Name', '', 'name', 'annotationelement')
        self._addColumn(
            columns, '_2_item.id', 'Item ID', '', '_id', 'annotationelement')
        self._addColumn(
            columns, '_1_annotation.name', 'Annotation Name', '', 'name', 'annotationelement')
        self._addColumn(
            columns, '_3_annotation.id', 'Annotation ID', '', '_id', 'annotationelement')
        self._addColumn(
            columns, '_4_annotation.description', 'Annotation Description', '',
            'description', 'annotationelement')
        self._addColumn(
            columns, '_5_annotationelement.id', 'Annotation Element ID', '',
            'element_id', 'annotationelement')
        self._addColumn(
            columns, '_bbox.x0', 'Bounding Box Low X', '', 'lowx', 'annotationelement')
        self._addColumn(
            columns, '_bbox.y0', 'Bounding Box Low Y', '', 'lowy', 'annotationelement')
        self._addColumn(
            columns, '_bbox.x1', 'Bounding Box High X', '', 'highx', 'annotationelement')
        self._addColumn(
            columns, '_bbox.y1', 'Bounding Box High Y', '', 'highy', 'annotationelement')
        self._addColumn(
            columns, 'annotationelement.group', 'Annotation Group', '',
            'group', 'annotationelement')
        self._addColumn(
            columns, 'annotationelement.label', 'Annotation Label', '',
            'group', 'annotationelement')
        keys = {}
        for auxidx, elems in enumerate(elements):
            if not elems:
                continue
            rows = self._scanElementColumns(
                source, columns, elems, auxidx, items, annotations, keys)
            for fullkey, entry in rows.items():
                result = columns[fullkey]
                if result['type'] == 'number':
                    try:
                        [float(v) for v in entry if isinstance(v, self.allowedTypes)]
                    except Exception:
                        result['type'] = 'string'
                        result['distinct'] = {str(v) for v in result['distinct']}
                for ridx, v in enumerate(entry):
                    if not isinstance(v, self.allowedTypes):
                        continue
                    result['count'] += 1
                    v = float(v) if result['type'] == 'number' else str(v)
                    if len(result['distinct']) <= self.maxDistinct:
                        result['distinct'].add(v)
                    if result['type'] == 'number':
                        if result['min'] is None:
                            result['min'] = result['max'] = v
                        result['min'] = min(result['min'], v)
                        result['max'] = max(result['max'], v)
                    if self._datacolumns and fullkey in self._datacolumns:
                        self._datacolumns[fullkey][(where, (auxidx, auxidx2, ridx))] = v

    @property
    def columns(self):
        """
        Get a sorted list of plottable columns with some metadata for each.

        Each data entry contains

            :fullkey: a unique string.  This is a good first-order sort
            :root: the root data array
            :key: the specific data tag
            :source: the source of the data (folder, item, annotation,
                annotationelement, file)
            :type: string or number
            :title: a human readable title
            :[distinct]: a list of distinct values if there are less than some
                maximum number of distinct values.  This might not include i
                values from adjacent items
            :[min]: for number data types, the lowest value present
            :[max]: for number data types, the highest value present

        :returns: a sorted list of data entries.
        """
        from ..models.annotationelement import Annotationelement

        if self._columns is not None:
            return self._columns
        columns = {}
        self._addColumn(
            columns, '_0_item.name', 'Item Name', 'Item', 'name', 'base')
        self._addColumn(
            columns, '_2_item.id', 'Item ID', 'Item', '_id', 'base')
        self._scanColumn(self.folder.get('meta', {}), 'folder', columns)
        self._scanColumn(self.item.get('meta', {}), 'item', columns,
                         [item.get('meta', {}) for item in self.items[1:]],
                         items=self.items)
        for anidx, annot in enumerate(self.annotations[0] if self.annotations is not None else []):
            self._scanColumn(
                annot.get('annotation', {}).get('attributes', {}),
                'annotation', columns,
                [itemannot[anidx].get('annotation').get('attributes', {})
                 for itemannot in self.annotations[1:]
                 if itemannot[anidx] is not None],
                anidx, items=self.items,
                annotations=[a[anidx] for a in self.annotations])
            if not anidx:
                self._addColumn(
                    columns, '_1_annotation.name', 'Annotation Name',
                    'Annotation', 'name', 'base')
                self._addColumn(
                    columns, '_3_annotation.id', 'Annotation ID',
                    'Annotation', '_id', 'base')
                self._addColumn(
                    columns, '_4_annotation.description', 'Annotation Description',
                    'Annotation', 'description', 'base')
            # add annotation elements
            firstelem = next(Annotationelement().yieldElements(annot), None)
            if firstelem is not None:
                self._scanElements(
                    [list(itertools.islice(
                        Annotationelement().yieldElements(a[anidx], bbox=True), 10000))
                        if a[anidx] else None for a in self.annotations],
                    'annotationelement', columns,
                    anidx,
                    items=self.items,
                    annotations=[a[anidx] for a in self.annotations],
                )
        # TODO: Add csv
        for result in columns.values():
            if len(result['distinct']) <= self.maxDistinct:
                result['distinct'] = sorted(result['distinct'])
                result['distinctcount'] = len(result['distinct'])
            else:
                result.pop('distinct', None)
            if result['type'] != 'number' or result['min'] is None:
                result.pop('min', None)
                result.pop('max', None)
        self._columns = sorted(columns.values(), key=lambda x: x['key'])
        return self._columns

    def data(self, columns, requiredColumns=None):
        """
        Get plottable data.

        :param columns: the columns to return.  Either a list of column names
            or a comma-delimited string.
        :param requiredColumns: only return data rows where all of these
            columns are non-None.  Either a list of column names of a
            comma-delimited string.
        """
        if not isinstance(columns, list):
            columns = columns.split(',')
        if not isinstance(requiredColumns, list):
            requiredColumns = requiredColumns.split(',') if requiredColumns is not None else []
        self._datacolumns = {c: {} for c in columns}
        rows = set()
        # collects data as a side effect
        collist = self.columns
        for coldata in self._datacolumns.values():
            rows |= set(coldata.keys())
        rows = sorted(rows, key=lambda row: (
            tuple(x if x is not None else '' for x in row[0]), row[1]))
        colsout = [col.copy() for col in collist if col['key'] in columns]
        for cidx, col in enumerate(colsout):
            col['index'] = cidx
        logger.info(f'Gathering {len(self._datacolumns)} x {len(rows)} data')
        data = [[None] * len(self._datacolumns) for _ in range(len(rows))]
        for cidx, col in enumerate(colsout):
            colkey = col['key']
            if colkey in self._datacolumns:
                datacol = self._datacolumns[colkey]
                for ridx, rowid in enumerate(rows):
                    data[ridx][cidx] = datacol.get(rowid, None)
        for cidx, col in enumerate(colsout):
            colkey = col['key']
            numrows = len(data)
            if colkey in requiredColumns:
                data = [row for row in data if row[cidx] is not None]
            if len(data) < numrows:
                logger.info(f'Reduced row count from {numrows} to {len(data)} '
                            f'because of None values in column {colkey}')
        # Refresh our count, distinct, distinctcount, min, max for each column
        for cidx, col in enumerate(colsout):
            col['count'] = len([row[cidx] for row in data if row[cidx] is not None])
            if col['type'] == 'number' and col['count']:
                col['min'] = min(row[cidx] for row in data if row[cidx] is not None)
                col['max'] = max(row[cidx] for row in data if row[cidx] is not None)
            distinct = {str(row[cidx]) for row in data if row[cidx] is not None}
            if len(distinct) <= self.maxDistinct:
                col['distinct'] = sorted(distinct)
                col['distinctcount'] = len(distinct)
            else:
                col.pop('distinct', None)
                col.pop('distinctcount', None)
        return {
            'columns': colsout,
            'data': data}
