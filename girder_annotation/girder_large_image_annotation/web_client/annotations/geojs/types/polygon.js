import _ from 'underscore';

import common from '../common';
import array from '../coordinates/array';

/**
 * Convert a geojs polygon annotation to the large_image
 * annotation schema.
 */
function polygon(annotation) {
    const element = common(annotation, 'polyline');
    const coordinates = array(annotation.coordinates());

    return _.extend(element, {
        type: 'polyline',
        closed: true,
        points: coordinates
    });
}

export default polygon;
