import functools
import json
import math
import os
import re
import threading

from bson.objectid import ObjectId

from girder import logger
from girder.constants import AccessType, SortDir
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.item import Item

dataFileExtReaders = {
    '.csv': 'read_csv',
    'text/csv': 'read_csv',
    '.xls': 'read_excel',
    '.xlsx': 'read_excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'read_excel',
    'application/vnd.ms-excel ': 'read_excel',
    'application/msexcel': 'read_excel',
    'application/x-msexcel': 'read_excel',
    'application/x-ms-excel': 'read_excel',
    'application/x-excel': 'read_excel',
    'application/x-dos_ms_excel': 'read_excel',
    'application/xls': 'read_excel',
    'application/x-xls': 'read_excel',
}
scanDatafileRecords = 50


@functools.lru_cache(maxsize=100)
def _dfFromFile(fileid, full=False):
    import pandas as pd

    file = File().load(fileid, force=True)
    ext = os.path.splitext(file['name'])[1]
    reader = dataFileExtReaders.get(
        ext, dataFileExtReaders.get(file.get('mimeType'), None))
    if reader == 'read_excel':
        df = getattr(pd, reader)(File().open(file), sheet_name=None)
    else:
        df = {'entry': getattr(pd, reader)(File().open(file))}
    df = {
        k: sheet.iloc[:None if full else scanDatafileRecords].to_dict('records')
        for k, sheet in df.items()}
    logger.info(f'Read {len(df)} x {len(next(iter(df.values())))} values from '
                f'{file["name"]} {file["size"]}')
    if len(df) == 1:
        df = next(iter(df.values()))
    return df


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
    maxAnnotationElements = 5000
    maxDistinct = 20
    allowedTypes = (str, bool, int, float)

    def __init__(self, user, item, annotations=None, adjacentItems=False, sources=None):
        """
        Get plottable data associated with an item.

        :param user: authenticating user.
        :param item: the item record.
        :param annotations: None, a list of annotation ids, or __all__.  If
            adjacent items are included, the most recent annotation with the
            same name will also be included.
        :param adjacentItems: if True, include data from other items in the
            same folder.  If __all__, include data from other items even if the
            data is not present in the current item.
        :param sources: None for all, or a string with a comma-separated list
            or a list of strings; when a list, the options are folder, item,
            annotation, datafile.
        """
        self.user = user
        self._columns = None
        self._datacolumns = None
        self._data = None
        if sources and not isinstance(sources, (list, tuple)):
            sources = sources.split(',')
        self._sources = tuple(sources) if sources else None
        if self._sources and 'annotation' not in self._sources:
            annotations = None
        self._fullScan = adjacentItems == '__all__'
        self._findItems(item, adjacentItems)
        self._findAnnotations(annotations)
        self._findDataFiles()
        self._dataLock = threading.RLock()

    def _findItems(self, item, adjacentItems=False):
        """
        Find all the large images in the folder.  This only retrieves the first
        self.maxItems entries.  If there are at least this many items, a query
        is stored in self._moreItems.  The items are listed in self.items.

        :param item: the item to use as the base.  If adjacentItems is false,
            this is the entire self.items data set.
        :param adjacentItems: if truthy, find adjacent items.
        """
        self._columns = None
        self.item = item
        self.folder = Folder().load(id=item['folderId'], user=self.user, level=AccessType.READ)
        self.items = [item]
        if adjacentItems:
            query = {
                'filters': {
                    '_id': {'$ne': item['_id']},
                },
                'sort': [('_id', SortDir.ASCENDING)],
            }
            if 'largeImage' in item:
                query['filters']['largeImage.fileId'] = {'$exists': True}
            self.items.extend(list(Folder().childItems(
                self.folder, limit=self.maxItems - 1, **query)))
        self._moreItems = query if len(self.items) == self.maxItems else None
        # TODO: find csv/xlsx/dataframe items in the folder

    def _findAnnotations(self, annotations):
        """
        Find annotations based on a list of annotations ids.  For the current
        item, these are just the listed annotations.  For adjacent items,
        annotations with the same names are located.  A maximum of maxItems
        are examined, so if the number of items in the folder exceeds this,
        some annotations will not be located.  Results are stored in
        self.annotations, which is a list with one entry per item.  Each entry
        is a list of annotations (without elements) or None if there is no
        matching annotation for that item.

        :param annotations: a list of annotation id strings or comma-separated
            string of annotation ids.
        """
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

    def _findDataFiles(self):  # noqa
        """
        Find data files inside the current item.  For adjacent items, the data
        file must have the same name or, if the found file is prefixed with
        the item name excluding the extension, then the adjancant file should
        be similarly prefixed.  Data files must have a known suffix or a known
        mimetype that can be read by pandas (and pandas must be installed).
        """
        self._itemfilelist = [[]] * len(self.items)
        try:
            import pandas as pd  # noqa
        except Exception:
            return
        if self._sources and 'filedata' not in self._sources:
            return
        names0 = {}
        for iidx, item in enumerate(self.items):
            if iidx:
                self._itemfilelist[iidx] = [None] * len(self._itemfilelist[0])
            names = {}
            for file in Item().childFiles(item):
                try:
                    if (file['_id'] == self.item['largeImage']['fileId'] or
                            file['_id'] == self.item['largeImage'].get('originalId')):
                        continue
                except Exception:
                    continue
                ext = os.path.splitext(file['name'])[1]
                if (ext not in dataFileExtReaders and
                        file.get('mimeType') not in dataFileExtReaders):
                    continue
                if file['name'].startswith(item['name'].rsplit('.')[0]):
                    base, name = True, file['name'][len(item['name'].rsplit('.')[0]):]
                else:
                    base, name = False, file['name']
                if (base, name) in names:
                    continue
                if iidx and (base, name) not in names0:
                    continue
                names[(base, name)] = len(names)
                if not iidx:
                    self._itemfilelist[0].append(file)
                else:
                    self._itemfilelist[iidx][names0[(base, name)]] = file
            if not iidx:
                names0 = names

    # Common column keys and titles
    commonColumns = {
        'item.id': 'Item ID',
        'item.name': 'Item Name',
        'item.description': 'Item Description',
        'annotation.id': 'Annotation ID',
        'annotation.name': 'Annotation Name',
        'annotation.description': 'Annotation Description',
        'annotationelement.id': 'Annotation Element ID',
        'annotationelement.group': 'Annotation Element Group',
        'annotationelement.label': 'Annotation Element Label',
        'annotationelement.type': 'Annotation Element Type',
        'bbox.x0': 'Bounding Box Low X',
        'bbox.y0': 'Bounding Box Low Y',
        'bbox.x1': 'Bounding Box High X',
        'bbox.y1': 'Bounding Box High Y',
    }

    def itemNameIDSelector(self, isName, selector):
        """
        Given a data selector that returns something that is either an item id,
        an item name, or an item name prefix, return the canonical item or
        id string from the list of known items.

        :param isName: True to return the canonical name, False for the
            canonical id.
        :param selector: the selector to get the initial value.
        :returns: a function that can be used as an overall selector.
        """

        def itemNameSelector(record, data, row):
            value = selector(record, data, row)
            for item in self.items:
                if str(item['_id']) == value:
                    return item['name']
                if item['name'].lower().startswith(value.lower() + '.'):
                    return item['name']
                if item['name'].lower() == value.lower():
                    return item['name']
            return value

        def itemIDSelector(record, data, row):
            value = selector(record, data, row)
            for item in self.items:
                if str(item['_id']) == value:
                    return str(item['_id'])
                if item['name'].lower().startswith(value.lower() + '.'):
                    return str(item['_id'])
                if item['name'].lower() == value.lower():
                    return str(item['_id'])
            return value

        return itemNameSelector if isName else itemIDSelector

    def datafileAnnotationElementSelector(self, key, cols):

        def annotationElementSelector(record, data, row):
            bbox = [col[1](record, data, row) for col in cols]
            if key in self._datacolumns:
                for row in self._datacolumns[key]:
                    if self._datacolumns[key][row] is not None:
                        for bidx, bkey in enumerate(['bbox.x0', 'bbox.y0', 'bbox.x1', 'bbox.y1']):
                            val = self._datacolumns[bkey].get(row)
                            if val is None or abs(val - bbox[bidx]) > 2:
                                break
                        else:
                            return self._datacolumns[key][row]
            return None

        return annotationElementSelector

    @staticmethod
    def keySelector(mode, key, key2=None):
        """
        Given a pattern for getting data from a dictionary, return a selector
        that gets that piece of data.

        :param mode: one of key, key0, keykey, keykey0, key0key, representing
            key lookups in dictionaries or array indices.
        :param key: the first key.
        :param key2: the second key, if needed.
        :returns: a pair of functions that can be used to select the value from
            the record and data structure.  This takes (record, data, row) and
            returns a value.  The record is the base record used, the data is
            the base dictionary, and the row is the location in the index.  The
            second function takes (record, data) and returns either None or the
            number of rows that are present.
        """
        if mode == 'key0key':

            def key0keySelector(record, data, row):
                return data[key][row][key2]

            def key0keyLength(record, data):
                return len(data[key])

            return key0keySelector, key0keyLength
        if mode == 'keykey0':

            def keykey0Selector(record, data, row):
                return data[key][key2][row]

            def keykey0Length(record, data):
                return len(data[key][key2])

            return keykey0Selector, keykey0Length
        if mode == 'keykey':

            def keykeySelector(record, data, row):
                return data[key][key2]

            return keykeySelector, None
        if mode == 'key0':

            def key0Selector(record, data, row):
                return data[key][row]

            def key0Length(record, data):
                return len(data[key])

            return key0Selector, key0Length

        def keySelector(record, data, row):
            return data[key]

        return keySelector, None

    @staticmethod
    def recordSelector(doctype):
        """
        Given a document type, return a function that returns the main data
        dictionary.

        :param doctype: one of folder, item, annotaiton, annotationelement.
        :returns: a function that takes (record) and returns the data
            dictionary, if any.
        """
        if doctype == 'annotation':

            def annotationGetData(record):
                return record.get('annotation', {}).get('attributes', {})

            return annotationGetData
        if doctype == 'annotationelement':

            def annotationelementGetData(record):
                return record.get('user', {})

            return annotationelementGetData

        if doctype == 'datafile':

            def datafileGetData(record):
                return record

            return datafileGetData

        def getData(record):
            return record.get('meta', {})

        return getData

    def _keysToColumns(self, columns, parts, doctype, getData, selector, length):
        """
        Given a selector and appropriate access information, ensure that an
        appropriate column or columns exist.

        :param columns: the column dictionary to possibly modify.
        :param parts: a tuple of values used to construct a key.
        :param doctype: the base document type.
        :param getData: a function that, given the document record, returns the
            data dictionary.
        :param selector: a function that, given the document record, data
            dictionary, and row, returns a value.
        :param length: None or a function that, given the document record and
            data dictionary, returns the number of rows.
        """
        key = '.'.join(str(v) for v in parts).lower()
        lastpart = parts[-1] if parts[-1] != '0' or len(parts) == 1 else parts[-2]
        title = ' '.join(str(v) for v in parts[1:] if v != '0')
        keymap = {
            r'(?i)(item|image)_(id|name)$': 'item.name',
            r'(?i)((low|min)(_|)x|^x1$)': 'bbox.x0',
            r'(?i)((low|min)(_|)y|^y1$)': 'bbox.y0',
            r'(?i)((high|max)(_|)x|^x2$)': 'bbox.x1',
            r'(?i)((high|max)(_|)y|^y2$)': 'bbox.y1',
        }
        match = False
        for k, v in keymap.items():
            if re.match(k, lastpart):
                if lastpart != parts[1]:
                    doctype = f'{doctype}.{parts[1]}'
                key = v
                title = self.commonColumns[key]
                if key == 'item.name':
                    self._ensureColumn(
                        columns, key, title, doctype, getData,
                        self.itemNameIDSelector(True, selector), length)
                    self._ensureColumn(
                        columns, 'item.id', self.commonColumns['item.id'],
                        doctype, getData,
                        self.itemNameIDSelector(False, selector), length)
                    return
                match = True
                break
        added = self._ensureColumn(
            columns, key, title, doctype, getData, selector, length)
        if match and added and key.startswith('bbox'):
            cols = [columns[bkey]['where'][doctype] for bkey in [
                'bbox.x0', 'bbox.y0', 'bbox.x1', 'bbox.y1']
                if bkey in columns and doctype in columns[bkey]['where']]
            if len(cols) == 4:
                # If we load all of these from annotation elements, use all
                # three keys:
                # for akey in {'annotation.id', 'annotation.name', 'annotationelement.id'}:
                for akey in {'annotationelement.id'}:
                    if self._datacolumns and akey in self._datacolumns:
                        self._requiredColumns.add(akey)
                    self._ensureColumn(
                        columns, akey, self.commonColumns[akey], doctype,
                        getData, self.datafileAnnotationElementSelector(akey, cols),
                        length)

    def _ensureColumn(self, columns, keyname, title, doctype, getData, selector, length):
        """
        Ensure that column exists and the selectors are recorded for the
        doctype.

        :param columns: the column dictionary to possibly modify.
        :param keyname: the key to the column.
        :param title: the title of the column.
        :param doctype: the base document type.
        :param getData: a function that, given the document record, returns the
            data dictionary.
        :param selector: a function that, given the document record, data
            dictionary, and row, returns a value.
        :param length: None or a function that, given the document record and
            data dictionary, returns the number of rows.
        :returns: True if the column where record was added.
        """
        if keyname not in columns:
            columns[keyname] = {
                'key': keyname,
                'title': title,
                'where': {},
                'type': 'number',
                'max': None,
                'min': None,
                'distinct': set(),
                'count': 0,
            }
        if doctype not in columns[keyname]['where']:
            columns[keyname]['where'][doctype] = (getData, selector, length)
            return True
        return False

    def _columnsFromData(self, columns, doctype, getData, record):  # noqa
        """
        Given a sample record, determine what columns could be read.

        :param columns: the column dictionary to possibly modify.
        :param doctype: the base document type.
        :param getData: a function that, given the document record, returns the
            data dictionary.
        :param record: a sample record.
        """
        data = getData(record)
        for key, value in data.items():
            try:
                if isinstance(value, list):
                    if not len(value):
                        continue
                    if isinstance(value[0], dict):
                        for key2, value2 in value[0].items():
                            try:
                                if isinstance(value2, (list, dict)):
                                    continue
                                selector, length = self.keySelector('key0key', key, key2)
                                self._keysToColumns(
                                    columns, ('data', key, '0', key2),
                                    doctype, getData, selector, length)
                            except Exception:
                                continue
                    else:
                        selector, length = self.keySelector('key0', key)
                        self._keysToColumns(
                            columns, ('data', key, '0'),
                            doctype, getData, selector, length)
                elif isinstance(value, dict):
                    for key2, value2 in value.items():
                        try:
                            if isinstance(value2, list):
                                if not len(value2):
                                    continue
                                selector, length = self.keySelector('keykey0', key, key2)
                                self._keysToColumns(
                                    columns, ('data', key, key2, '0'),
                                    doctype, getData, selector, length)
                            else:
                                selector, length = self.keySelector('keykey', key, key2)
                                self._keysToColumns(
                                    columns, ('data', key, key2),
                                    doctype, getData, selector, length)
                        except Exception:
                            continue
                else:
                    selector, length = self.keySelector('key', key)
                    self._keysToColumns(
                        columns, ('data', key),
                        doctype, getData, selector, length)
            except Exception:
                continue

    def _commonColumn(self, columns, keyname, doctype, getData, selector):
        """
        Ensure that column with a commonly used key exists.

        :param columns: the column dictionary to possibly modify.
        :param keyname: the key to the column.
        :param doctype: the base document type.
        :param getData: a function that, given the document record, returns the
            data dictionary.
        :param selector: a function that, given the document record, data
            dictionary, and row, returns a value.
        """
        title = self.commonColumns[keyname]
        self._ensureColumn(columns, keyname, title, doctype, getData, selector, None)

    def _collectRecordRows(
            self, record, data, selector, length, colkey, col, recidx, rows,
            iid, aid, eid):
        """
        Collect statistics and possible data from one data set.  See
        _collectRecords for parameter details.
        """
        count = 0
        for rowidx in range(rows):
            try:
                value = selector(record, data, rowidx)
            except Exception:
                continue
            if value is None or not isinstance(value, self.allowedTypes) or value == '':
                continue
            if col['type'] == 'number':
                try:
                    value = float(value)
                except Exception:
                    col['type'] = 'string'
                    col['distinct'] = {str(v) for v in col['distinct']}
            col['count'] += 1
            if col['type'] == 'number':
                if col['min'] is None:
                    col['min'] = col['max'] = value
                col['min'] = min(col['min'], value)
                col['max'] = max(col['max'], value)
            else:
                value = str(value)
            if len(col['distinct']) <= self.maxDistinct:
                col['distinct'].add(value)
            if self._datacolumns and colkey in self._datacolumns:
                self._datacolumns[colkey][(
                    iid, aid, eid,
                    rowidx if length is not None else -1)] = value
                if not self._requiredColumns or colkey in self._requiredColumns:
                    count += 1
        return count

    def _collectRecords(self, columns, recordlist, doctype, iid='', aid=''):
        """
        Collect statistics and possibly row values from a list of records.

        :param columns: the column dictionary to possibly modify.
        :param recordlist: a list of records to use.
        :param doctype: the base document type.
        :param iid: an optional item id to use for determining distinct rows.
        :param aid: an optional annotation id to use for determining distinct
            rows.
        :return: the number of required data entries added to the data
            collection process.  This will be zero when just listing columns.
            If no required fields were specified, this will be the count of all
            added data entries.
        """
        count = 0
        eid = ''
        for colkey, col in columns.items():
            if self._datacolumns and colkey not in self._datacolumns:
                continue
            for where, (getData, selector, length) in col['where'].items():
                if doctype != where and not where.startswith(doctype + '.'):
                    continue
                for recidx, record in enumerate(recordlist):
                    if doctype == 'item':
                        iid = str(record['_id'])
                    elif doctype == 'annotation':
                        aid = str(record['_id'])
                    elif doctype == 'annotationelement':
                        eid = str(record['id'])
                    data = getData(record)
                    try:
                        rows = 1 if length is None else length(record, data)
                    except Exception:
                        continue
                    count += self._collectRecordRows(
                        record, data, selector, length, colkey, col, recidx,
                        rows, iid, aid, eid)
        return count

    def _collectColumns(self, columns, recordlist, doctype, first=True, iid='', aid=''):
        """
        Collect the columns available for a set of records.

        :param columns: the column dictionary to possibly modify.
        :param recordlist: a list of records to use.
        :param doctype: the base document type.
        :param first: False if this is not the first page of a multi-page list
            of records,
        :param iid: an optional item id to use for determining distinct rows.
        :param aid: an optional annotation id to use for determining distinct
            rows.
        :return: the number of required data entries added to the data
            collection process.  This will be zero when just listing columns.
            If no required fields were specified, this will be the count of all
            added data entries.
        """
        getData = self.recordSelector(doctype.split('.', 1)[0])
        if doctype == 'item':
            self._commonColumn(columns, 'item.id', doctype, getData,
                               lambda record, data, row: str(record['_id']))
            self._commonColumn(columns, 'item.name', doctype, getData,
                               lambda record, data, row: record['name'])
            self._commonColumn(columns, 'item.description', doctype, getData,
                               lambda record, data, row: record['description'])
        if doctype == 'annotation':
            self._commonColumn(columns, 'annotation.id', doctype, getData,
                               lambda record, data, row: str(record['_id']))
            self._commonColumn(columns, 'annotation.name', doctype, getData,
                               lambda record, data, row: record['annotation']['name'])
            self._commonColumn(columns, 'annotation.description', doctype, getData,
                               lambda record, data, row: record['annotation']['description'])
        if doctype == 'annotationelement':
            self._commonColumn(columns, 'annotationelement.id', doctype, getData,
                               lambda record, data, row: str(record['id']))
            self._commonColumn(columns, 'annotationelement.group', doctype, getData,
                               lambda record, data, row: record['group'])
            self._commonColumn(columns, 'annotationelement.label', doctype, getData,
                               lambda record, data, row: record['label']['value'])
            self._commonColumn(columns, 'annotationelement.type', doctype, getData,
                               lambda record, data, row: record['type'])
            self._commonColumn(columns, 'bbox.x0', doctype, getData,
                               lambda record, data, row: record['_bbox']['lowx'])
            self._commonColumn(columns, 'bbox.y0', doctype, getData,
                               lambda record, data, row: record['_bbox']['lowy'])
            self._commonColumn(columns, 'bbox.x1', doctype, getData,
                               lambda record, data, row: record['_bbox']['highx'])
            self._commonColumn(columns, 'bbox.y1', doctype, getData,
                               lambda record, data, row: record['_bbox']['highy'])
        if first or self._fullScan or doctype != 'item':
            for record in recordlist[:None if self._fullScan else 1]:
                self._columnsFromData(columns, doctype, getData, record)
        return self._collectRecords(columns, recordlist, doctype, iid, aid)

    def _getColumnsFromAnnotations(self, columns):
        """
        Collect columns and data from annotations.
        """
        from ..models.annotationelement import Annotationelement

        count = 0
        countsPerAnnotation = {}
        for iidx, annotList in enumerate(self.annotations or []):
            iid = str(self.items[iidx]['_id'])
            for anidx, annot in enumerate(annotList):
                # If the first item's annotation didn't contribute any required
                # data to the data set, skip subsequent items' annotations;
                # they are likely to be discarded.
                if iidx and not countsPerAnnotation.get(anidx, 0) and not self._fullScan:
                    continue
                startcount = count
                if annot is None:
                    continue
                if not self._sources or 'annotation' in self._sources:
                    count += self._collectColumns(columns, [annot], 'annotation', iid=iid)
                # add annotation elements
                if ((not self._sources or 'annotationelement' in self._sources) and
                        Annotationelement().countElements(annot) <= self.maxAnnotationElements):
                    for element in Annotationelement().yieldElements(annot, bbox=True):
                        count += self._collectColumns(
                            columns, [element], 'annotationelement', iid=iid, aid=str(annot['_id']))
                if not iidx:
                    countsPerAnnotation[anidx] = count - startcount
        return count

    def _getColumnsFromDataFiles(self, columns):
        """
        Collect columns and data from data files in items.
        """
        if not len(self._itemfilelist) or not len(self._itemfilelist[0]):
            return 0
        count = 0
        countsPerDataFile = {}
        for iidx, dfList in enumerate(self._itemfilelist or []):
            iid = str(self.items[iidx]['_id'])
            for dfidx, file in enumerate(dfList):
                # If the first item's data file didn't contribute any required
                # data to the data set, skip subsequent items' data files;
                # they are likely to be discarded.
                if iidx and not countsPerDataFile.get(dfidx, 0) and not self._fullScan:
                    continue
                startcount = count
                if file is None:
                    continue
                if not self._sources or 'datafile' in self._sources:
                    try:
                        df = _dfFromFile(file['_id'], bool(self._datacolumns or self._fullScan))
                        count += self._collectColumns(
                            columns, [df] if isinstance(df, dict) else df,
                            f'datafile.{dfidx}', iid=iid)
                    except Exception:
                        logger.info(
                            f'Cannot process file {file["_id"]}: {file["name"]} as a dataframe')
                        raise
                if not iidx:
                    countsPerDataFile[dfidx] = count - startcount
        return count

    def _getColumns(self):
        """
        Get a sorted list of plottable columns with some metadata for each.

        :returns: a sorted list of data entries.
        """
        count = 0
        columns = {}
        if not self._sources or 'folder' in self._sources:
            count += self._collectColumns(columns, [self.folder], 'folder')
        if not self._sources or 'item' in self._sources:
            count += self._collectColumns(columns, self.items, 'item')
            if self._moreItems:
                for item in Folder().childItems(
                        self.folder, offset=len(self.items), **self._moreItems):
                    count += self._collectColumns(columns, [item], 'item', first=False)
        count += self._getColumnsFromAnnotations(columns)
        count += self._getColumnsFromDataFiles(columns)
        for result in columns.values():
            if len(result['distinct']) <= self.maxDistinct:
                result['distinct'] = sorted(result['distinct'])
                result['distinctcount'] = len(result['distinct'])
            else:
                result.pop('distinct', None)
            if result['type'] != 'number' or result['min'] is None:
                result.pop('min', None)
                result.pop('max', None)
        prefixOrder = {'item': 0, 'annotation': 1, 'annotationelement': 2, 'data': 3, 'bbox': 4}
        columns = sorted(columns.values(), key=lambda x: (
            prefixOrder.get(x['key'].split('.', 1)[0], len(prefixOrder)), x['key']))
        return columns

    @property
    def columns(self):
        """
        Get a sorted list of plottable columns with some metadata for each.

        Each data entry contains

            :key: the column key.  For database entries, this is (item|
                annotation|annotationelement).(id|name|description|group|
                label).  For bounding boxes this is bbox.(x0|y0|x1|y1).  For
                data from meta / attributes / user, this is
                data.(key)[.0][.(key2)][.0]
            :type: 'string' or 'number'
            :title: a human readable title
            :count: the number of non-null entries in the column
            :[distinct]: a list of distinct values if there are less than some
                maximum number of distinct values.  This might not include
                values from adjacent items
            :[distinctcount]: if distinct is populated, this is len(distinct)
            :[min]: for number data types, the lowest value present
            :[max]: for number data types, the highest value present

        :returns: a sorted list of data entries.
        """
        if self._columns is not None:
            return self._columns
        columns = self._getColumns()
        self._columns = columns
        return [{k: v for k, v in c.items() if k != 'where'} for c in self._columns if c['count']]

    def _collectData(self, rows, colsout):
        """
        Get data rows and columns.

        :param rows: a list of row id tuples.
        :param colsout: a list of output columns.
        :returns: a data array and an updated row list.
        """
        data = [[None] * len(colsout) for _ in range(len(rows))]
        discard = set()
        for cidx, col in enumerate(colsout):
            colkey = col['key']
            if colkey in self._datacolumns:
                datacol = self._datacolumns[colkey]
                for ridx, rowid in enumerate(rows):
                    value = datacol.get(rowid, None)
                    if value is None and rowid[3] != -1:
                        value = datacol.get((rowid[0], rowid[1], rowid[2], -1), None)
                        if value is not None:
                            discard.add((rowid[0], rowid[1], rowid[2], -1))
                    if value is None and (rowid[3] != -1 or rowid[2]):
                        value = datacol.get((rowid[0], rowid[1], '', -1), None)
                        if value is not None:
                            discard.add((rowid[0], rowid[1], '', -1))
                    if value is None and (rowid[3] != -1 or rowid[2] or rowid[1]):
                        value = datacol.get((rowid[0], '', '', -1), None)
                        if value is not None:
                            discard.add((rowid[0], '', '', -1))
                    if value is None and (rowid[3] != -1 or rowid[2] or rowid[1] or rowid[0]):
                        value = datacol.get(('', '', '', -1), None)
                        if value is not None:
                            discard.add(('', '', '', -1))
                    data[ridx][cidx] = value
        if len(discard):
            data = [row for ridx, row in enumerate(data) if rows[ridx] not in discard]
            rows = [row for ridx, row in enumerate(rows) if rows[ridx] not in discard]
        return data, rows

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
        requiredColumns = set(requiredColumns)
        self._requiredColumns = set(requiredColumns)
        with self._dataLock:
            self._datacolumns = {c: {} for c in columns}
            rows = set()
            # collects data as a side effect
            collist = self._getColumns()
            for coldata in self._datacolumns.values():
                rows |= set(coldata.keys())
            rows = sorted(rows)
            colsout = [col.copy() for col in collist if col['key'] in columns]
            for cidx, col in enumerate(colsout):
                col['index'] = cidx
            logger.info(f'Gathering {len(colsout)} x {len(rows)} data')
            data, rows = self._collectData(rows, colsout)
            self._datacolumns = None
        for cidx, col in enumerate(colsout):
            colkey = col['key']
            numrows = len(data)
            if colkey in requiredColumns:
                data = [row for row in data if row[cidx] is not None]
            if len(data) < numrows:
                logger.info(f'Reduced row count from {numrows} to {len(data)} '
                            f'because of None values in column {colkey}')
        subdata = data
        for cidx, col in enumerate(colsout):
            colkey = col['key']
            numrows = len(data)
            if colkey in self._requiredColumns and colkey not in requiredColumns:
                subdata = [row for row in subdata if row[cidx] is not None]
        if len(subdata) and len(subdata) < len(data):
            logger.info(f'Reduced row count from {len(data)} to {len(subdata)} '
                        f'because of None values in implied columns')
            data = subdata
        # Refresh our count, distinct, distinctcount, min, max for each column
        for cidx, col in enumerate(colsout):
            col['count'] = len([row[cidx] for row in data if row[cidx] is not None])
            if col['type'] == 'number' and col['count']:
                col['min'] = min(row[cidx] for row in data if row[cidx] is not None)
                col['max'] = max(row[cidx] for row in data if row[cidx] is not None)
            distinct = {str(row[cidx]) if col['type'] == 'string' else row[cidx]
                        for row in data if row[cidx] is not None}
            if len(distinct) <= self.maxDistinct:
                col['distinct'] = sorted(distinct)
                col['distinctcount'] = len(distinct)
            else:
                col.pop('distinct', None)
                col.pop('distinctcount', None)
        colsout = [{k: v for k, v in c.items() if k != 'where'} for c in colsout]
        return {
            'columns': colsout,
            'data': data}
