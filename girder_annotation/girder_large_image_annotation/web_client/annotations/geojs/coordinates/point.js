/**
 * Convert a geojs point object to an annotation
 * coordinate.
 */
function point(pt) {
    return [pt.x, pt.y, pt.z || 0];
}

export default point;
