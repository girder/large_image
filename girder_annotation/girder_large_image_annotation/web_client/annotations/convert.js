import _ from 'underscore';

import * as geometry from './geometry';
import * as defaults from './defaults';
import style from './style';

function convertOne(properties) {
    return function (annotation) {
        const type = annotation.type;
        annotation = _.defaults({}, annotation, defaults[type] || {});
        if (!_.has(geometry, type)) {
            return;
        }
        return {
            type: 'Feature',
            id: annotation.id,
            geometry: geometry[type](annotation),
            properties: _.extend({element: annotation}, properties, style(annotation))
        };
    };
}

export default function convert(json, properties = {}) {
    const features = _.chain(json)
        .map(convertOne(properties))
        .compact()
        .value();

    return {
        type: 'FeatureCollection',
        features
    };
}
