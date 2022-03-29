import rectangle from './rectangle';

/**
 * Convert a geojs ellipse annotation to the large_image
 * annotation schema.
 */
function ellipse(annotation) {
    const element = rectangle(annotation);
    element.type = 'ellipse';
    return element;
}

export default ellipse;
