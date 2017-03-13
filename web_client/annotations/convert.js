import _ from 'underscore';

import * as geometry from './geometry';
import style from './style';

function convertOne(annotation) {
    const type = annotation.type;
    if (!_.has(geometry, type)) {
        return;
    }
    return {
        type: 'Feature',
        id: annotation.id,
        geometry: geometry[type](annotation),
        properties: style(annotation)
    };
}

export default function convert(json) {
    const features = _.chain(json)
        .map(convertOne)
        .compact()
        .value();

    return {
        type: 'FeatureCollection',
        features
    };
}
