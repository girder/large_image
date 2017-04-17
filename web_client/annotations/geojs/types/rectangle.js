import _ from 'underscore';

import common from '../common';

/**
 * Convert a geojs rectangle annotation to the large_image
 * annotation schema.
 */
function rectangle(annotation) {
    const element = common(annotation);
    const [p1, p2, p3, p4] = annotation.coordinates();
    const top = [p3.x - p2.x, p3.y - p2.y];
    const left = [p2.x - p1.x, p2.y - p1.y];

    // determine the rotation of the top line of the rectangle
    const rotation = Math.atan2(top[1], top[0]);
    const height = Math.sqrt(left[0] * left[0] + left[1] * left[1]);
    const width = Math.sqrt(top[0] * top[0] + top[1] * top[1]);
    const center = [
        0.25 * (p1.x + p2.x + p3.x + p4.x),
        0.25 * (p1.y + p2.y + p3.y + p4.y),
        0
    ];

    return _.extend(element, {
        type: 'rectangle',
        center,
        width,
        height,
        rotation
    });
}

export default rectangle;
