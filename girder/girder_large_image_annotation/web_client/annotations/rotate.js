/**
 * Returns a function that rotates a coordinate the given
 * amount about a center point.
 */
export default function rotate(rotation, center) {
    const cos = Math.cos(rotation);
    const sin = Math.sin(rotation);
    center = center || [0, 0];

    return function (point) {
        const x = point[0] - center[0];
        const y = point[1] - center[1];
        return [
            x * cos - y * sin + center[0],
            x * sin + y * cos + center[1]
        ];
    };
}
