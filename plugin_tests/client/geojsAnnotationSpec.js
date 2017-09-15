/* globals girder, girderTest, describe, it, expect, waitsFor, runs */
/* eslint-disable camelcase */

girderTest.addScripts([
    '/clients/web/static/built/plugins/jobs/plugin.min.js',
    '/clients/web/static/built/plugins/worker/plugin.min.js',
    '/clients/web/static/built/plugins/large_image/plugin.min.js'
]);

describe('geojs-annotations', function () {
    var large_image, geojs;
    var fillColor = 'rgba(0,0,0,0)';
    var lineColor = 'rgb(0,0,0)';
    var lineWidth = 2;

    beforeEach(function () {
        large_image = girder.plugins.large_image;
        geojs = large_image.annotations.geojs;
    });

    it('convert', function () {
        var type;
        var coordinates;

        var annotation = {
            type: function () {
                return type;
            },
            coordinates: function () {
                return coordinates;
            }
        };

        // invalid type
        type = 'not valid';
        expect(function () {
            geojs.convert(annotation);
        }).toThrow();

        type = 'point';
        coordinates = [{x: 0, y: 0}];
        expect(geojs.convert(annotation)).toEqual({
            type: 'point',
            center: [0, 0, 0],
            fillColor: fillColor,
            lineColor: lineColor,
            lineWidth: lineWidth
        });
    });

    describe('coordinates', function () {
        it('point', function () {
            expect(geojs.coordinates.point({x: 1, y: 2})).toEqual([1, 2, 0]);
            expect(geojs.coordinates.point({x: 1, y: 2, z: 3})).toEqual([1, 2, 3]);
        });

        it('array', function () {
            expect(geojs.coordinates.array([{x: 1, y: 2}])).toEqual([[1, 2, 0]]);
            expect(geojs.coordinates.array([
                {x: 1, y: 2, z: 3},
                {x: 2, y: 3, z: 4}
            ])).toEqual([[1, 2, 3], [2, 3, 4]]);
        });
    });

    describe('types', function () {
        var style = {
            fill: false,
            stroke: false
        };
        var coordinates;
        var type;
        var annotation = {
            type: function () {
                return type;
            },
            options: function () {
                return {
                    style: style
                };
            },
            coordinates: function () {
                return coordinates;
            },
            style: function (key) {
                return style[key];
            }
        };

        it('point', function () {
            type = 'point';
            coordinates = [{x: 1, y: 2}];
            expect(geojs.types.point(annotation)).toEqual({
                type: 'point',
                center: [1, 2, 0],
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth
            });
        });

        it('rectangle', function () {
            type = 'rectangle';
            coordinates = [
                {x: 1, y: 2},
                {x: 1, y: 4},
                {x: 3, y: 4},
                {x: 3, y: 2}
            ];
            expect(geojs.types.rectangle(annotation)).toEqual({
                type: 'rectangle',
                center: [2, 3, 0],
                width: 2,
                height: 2,
                rotation: 0,
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth,
                normal: [0, 0, 1]
            });
        });

        it('rotated rectangle', function () {
            type = 'rectangle';
            coordinates = [
                {x: 0, y: -1},
                {x: -1, y: 0},
                {x: 0, y: 1},
                {x: 1, y: 0}
            ];
            expect(geojs.types.rectangle(annotation)).toEqual({
                type: 'rectangle',
                center: [0, 0, 0],
                width: Math.sqrt(2),
                height: Math.sqrt(2),
                rotation: Math.PI / 4,
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth,
                normal: [0, 0, 1]
            });
        });

        it('polygon', function () {
            type = 'polygon';
            coordinates = [
                {x: 0, y: 0},
                {x: 1, y: 0},
                {x: 1, y: 1},
                {x: 0, y: 1}
            ];
            expect(geojs.types.polygon(annotation)).toEqual({
                type: 'polyline',
                closed: true,
                points: [
                    [0, 0, 0],
                    [1, 0, 0],
                    [1, 1, 0],
                    [0, 1, 0]
                ],
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth
            });
        });

        it('line', function () {
            type = 'line';
            coordinates = [
                {x: 0, y: 0},
                {x: 1, y: 0}
            ];
            expect(geojs.types.line(annotation)).toEqual({
                type: 'polyline',
                closed: false,
                points: [
                    [0, 0, 0],
                    [1, 0, 0]
                ],
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth
            });
        });
    });
});
