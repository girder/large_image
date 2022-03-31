import rectangle from './rectangle';

/**
 * Convert a geojs circle annotation to the large_image
 * annotation schema.
 */
function circle(annotation) {
    const element = rectangle(annotation);
    element.type = 'circle';
    element.radius = Math.max(element.width, element.height) / 2;
    delete element.width;
    delete element.height;
    delete element.rotation;
    delete element.normal;
    return element;
}

export default circle;
