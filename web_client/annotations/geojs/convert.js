import _ from 'underscore';

import * as types from './types';

function convert(annotation) {
    var type = annotation.type();
    if (!_.has(types, type)) {
        throw new Error(
            `Unknown annotation type "${type}"`
        );
    }
    return types[type](annotation);
}

export default convert;
