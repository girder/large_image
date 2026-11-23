/* globals girder, girderTest, describe, it, expect, beforeEach */
/* eslint-disable camelcase */

girderTest.importPlugin('large_image', 'large_image_annotation');

describe('geojs-annotations', function () {
    var large_image_annotation, geojs, convert;
    var fillColor = 'rgba(0,0,0,0)';
    var lineColor = 'rgb(0,0,0)';
    var lineWidth = 2;

    beforeEach(function () {
        large_image_annotation = girder.plugins.large_image_annotation;
        geojs = large_image_annotation.annotations.geojs;
        convert = large_image_annotation.annotations.convert;
    });

    it('convert from', function () {
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

    it('convert to', function () {
        var result;

        result = convert({attributes: {type: 'point', center: [0, 0, 0]}});
        expect(result.type).toBe('FeatureCollection');
        expect(result.features.length).toBe(1);
        result = convert({attributes: {type: 'point', center: [0, 0, 0]}, attributes2: {type: 'point', center: [0, 0, 0]}});
        expect(result.type).toBe('FeatureCollection');
        expect(result.features.length).toBe(2);
        result = convert({attributes: {type: 'point', center: [0, 0, 0]}, _attributes: {type: 'point', center: [0, 0, 0]}});
        expect(result.type).toBe('FeatureCollection');
        expect(result.features.length).toBe(1);
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

    describe('text', function () {
        var text;

        beforeEach(function () {
            text = large_image_annotation.annotations.text;
        });

        it('sanitizeText', function () {
            expect(text.sanitizeText('A comment')).toBe('A comment');
            expect(text.sanitizeText('  trimmed \n')).toBe('trimmed');
            expect(text.sanitizeText('  not trimmed ', false)).toBe('  not trimmed ');
            expect(text.sanitizeText(undefined)).toBe('');
            expect(text.sanitizeText(null)).toBe('');
            expect(text.sanitizeText(5)).toBe('5');
            expect(text.sanitizeText(' \t\n ')).toBe('');
            // line breaks are kept as line feeds, tabs become spaces, and
            // other control characters are removed
            expect(text.sanitizeText('two\nlines')).toBe('two\nlines');
            expect(text.sanitizeText('a\r\nb\rc\n\nd')).toBe('a\nb\nc\n\nd');
            expect(text.sanitizeText('a\tb')).toBe('a b');
            expect(text.sanitizeText('bell\u0007 del\u007f c1\u0085 nul\u0000.')).toBe('bell del c1 nul.');
            // other unicode is kept, including characters outside of the
            // basic multilingual plane and non-breaking spaces within text
            expect(text.sanitizeText('\u00c5ngstr\u00f6m \u65e5\u672c\u8a9e \ud83d\ude03 a\u00a0b')).toBe(
                '\u00c5ngstr\u00f6m \u65e5\u672c\u8a9e \ud83d\ude03 a\u00a0b');
        });
        it('textFont', function () {
            expect(text.textFont({fontSize: 20})).toBe('20px/25px sans-serif');
            expect(text.textFont({})).toBe('16px/20px sans-serif');
            expect(text.textFont()).toBe('16px/20px sans-serif');
            expect(text.textFont({fontSize: -5})).toBe('16px/20px sans-serif');
            expect(text.textFont({fontSize: 12.5})).toBe('12.5px/15.63px sans-serif');
        });
        it('text is not converted to geojson', function () {
            var result = convert({a: {type: 'text', center: [1, 2, 0], text: 'A comment'}});
            expect(result.features.length).toBe(0);
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

            coordinates = [
                {x: 3, y: 2},
                {x: 3, y: 4},
                {x: 1, y: 4},
                {x: 1, y: 2}
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
                rotation: -Math.PI / 4,
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth,
                normal: [0, 0, 1]
            });

            coordinates = [
                {x: 1, y: 2},
                {x: 9, y: 8},
                {x: 5, y: 11},
                {x: -3, y: 5}
            ];
            expect(geojs.types.rectangle(annotation).rotation).toBeCloseTo(Math.atan2(3, 4));
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

        it('ellipse', function () {
            type = 'ellipse';
            coordinates = [
                {x: 1, y: 2},
                {x: 1, y: 4},
                {x: 3, y: 4},
                {x: 3, y: 2}
            ];
            expect(geojs.types.ellipse(annotation)).toEqual({
                type: 'ellipse',
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

        it('circle', function () {
            type = 'circle';
            coordinates = [
                {x: 1, y: 2},
                {x: 1, y: 4},
                {x: 3, y: 4},
                {x: 3, y: 2}
            ];
            expect(geojs.types.circle(annotation)).toEqual({
                type: 'circle',
                center: [2, 3, 0],
                radius: 1,
                fillColor: fillColor,
                lineColor: lineColor,
                lineWidth: lineWidth
            });
        });
    });
});
