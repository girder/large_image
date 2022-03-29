export default function circle(json) {
    const center = json.center;
    const x = center[0];
    const y = center[1];
    const radius = json.radius;

    const left = x - radius;
    const right = x + radius;
    const top = y - radius;
    const bottom = y + radius;

    return {
        type: 'Polygon',
        coordinates: [[
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom],
            [left, top]
        ]],
        annotationType: 'circle'
    };
}
