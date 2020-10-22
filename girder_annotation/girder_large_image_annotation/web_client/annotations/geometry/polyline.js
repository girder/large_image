import _ from 'underscore';

export default function polyline(json) {
    const points = _.map(json.points, (p) => _.first(p, 2));
    var type;
    var coordinates;
    var annotationType;

    if (json.closed) {
        type = 'Polygon';
        points.push(points[0]);
        coordinates = [points];
        annotationType = 'polygon';
    } else {
        type = 'LineString';
        coordinates = points;
        annotationType = 'line';
    }

    return {
        type,
        coordinates,
        annotationType
    };
}
