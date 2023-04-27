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
            return [x + cx, y + cy, z]
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
