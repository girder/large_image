import json
import math


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
