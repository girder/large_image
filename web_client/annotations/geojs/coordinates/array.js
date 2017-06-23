import _ from 'underscore';

import point from './point';

/**
 * Convert an array of point objects to an array of
 * annotation coordinates.
 */
function array(a) {
    return _.map(a, point);
}

export default array;
