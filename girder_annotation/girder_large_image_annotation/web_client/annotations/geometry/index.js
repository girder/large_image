import rectangle from './rectangle';
import ellipse from './ellipse';
import circle from './circle';
import polyline from './polyline';
import point from './point';

// element fields that describe the geometry of these shapes
const geometryKeys = ['points', 'closed', 'holes', 'center', 'width', 'height', 'rotation', 'normal', 'radius'];

export {
    rectangle,
    ellipse,
    circle,
    polyline,
    point,
    geometryKeys
};
