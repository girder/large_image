import _ from 'underscore';

export default function polyline(json) {
    const points = _.map(json.points, (p) => _.first(p, 2));
    var type;
    var coordinates;

    if (json.closed) {
        type = 'Polygon';
        points.push(points[0]);
        coordinates = [points];
    } else {
        type = 'LineString';
        coordinates = points;
    }

    return {
        type,
        coordinates
    };
}
