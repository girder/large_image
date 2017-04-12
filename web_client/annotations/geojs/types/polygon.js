import _ from 'underscore';

import common from '../common';
import array from '../coordinates/array';

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
