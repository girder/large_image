/* globals girder, girderTest, describe, it, expect, waitsFor, runs */

girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation');

describe('Annotations', function () {
    /**
     * Compute the l_inf distance from a to b.
     */
    function dist(a, b) {
        var i, max = 0, dx, dy;
        if (a.length !== b.length) {
            return Number.POSITIVE_INFINITY;
        }
        for (i = 0; i < a.length; i += 1) {
            dx = a[i][0] - b[i][0];
            dy = a[i][1] - b[i][1];
            max = Math.max(max, dx * dx + dy * dy);
        }
        return Math.sqrt(max);
    }

    function expectClose(a, b, eps) {
        eps = eps || 1e-6;
        var d = dist(a, b);
        if (!(d >= 0) && !(d <= 0)) {
            throw new Error(
                'Vector is invalid'
            );
        }
        if (d >= eps) {
            throw new Error(
                'Vectors are not equal'
            );
        }
    }

    var largeImageAnnotation;
    beforeEach(function () {
        largeImageAnnotation = girder.plugins.large_image_annotation;
    });
    describe('geometry', function () {
        it('rectangle', function () {
            var obj = largeImageAnnotation.annotations.geometry.rectangle({
                type: 'rectangle',
                id: 'a',
                center: [10, 20, 0],
                width: 5,
                height: 10,
                rotation: 0
            });

            expect(obj.type).toBe('Polygon');
            expect(obj.coordinates.length).toBe(1);
            expect(obj.annotationType).toBe('rectangle');
            expectClose(
                obj.coordinates[0], [
                    [7.5, 15], [12.5, 15], [12.5, 25], [7.5, 25], [7.5, 15]
                ]
            );

            obj = largeImageAnnotation.annotations.geometry.rectangle({
                type: 'rectangle',
                id: 'a',
                center: [10, 10, 0],
                width: Math.sqrt(2),
                height: Math.sqrt(2),
                rotation: Math.PI / 4
            });

            expect(obj.type).toBe('Polygon');
            expect(obj.coordinates.length).toBe(1);
            expect(obj.annotationType).toBe('rectangle');
            expectClose(
                obj.coordinates[0], [
                    [10, 9], [11, 10], [10, 11], [9, 10], [10, 9]
                ]
            );
        });

        it('open polyline', function () {
            var obj = largeImageAnnotation.annotations.geometry.polyline({
                type: 'polyline',
                id: 'a',
                points: [
                    [0, 1, 0],
                    [1, 0, 0]
                ],
                closed: false
            });

            expect(obj.type).toBe('LineString');
            expect(obj.coordinates.length).toBe(2);
            expect(obj.annotationType).toBe('line');
            expectClose(
                obj.coordinates, [
                    [0, 1], [1, 0]
                ]
            );
        });

        it('closed polyline', function () {
            var obj = largeImageAnnotation.annotations.geometry.polyline({
                type: 'polyline',
                id: 'a',
                points: [
                    [0, 1, 0],
                    [1, 0, 0],
                    [1, 1, 0]
                ],
                closed: true
            });

            expect(obj.type).toBe('Polygon');
            expect(obj.coordinates.length).toBe(1);
            expect(obj.coordinates[0].length).toBe(4);
            expect(obj.annotationType).toBe('polygon');
            expectClose(
                obj.coordinates[0], [
                    [0, 1], [1, 0], [1, 1], [0, 1]
                ]
            );
        });

        it('point', function () {
            var obj = largeImageAnnotation.annotations.geometry.point({
                type: 'point',
                id: 'a',
                center: [1, 2, 0]
            });
            expect(obj.type).toBe('Point');
            expect(obj.annotationType).toBe('point');
            expect(obj.coordinates).toEqual([1, 2]);
        });

        describe('heatmapColorTable', function () {
            var values = [0.508, 0.806, 0.311, 0.402, 0.535, 0.661, 0.866, 0.31, 0.241, 0.63, 0.555, 0.067, 0.668, 0.164, 0.512, 0.647, 0.501, 0.637, 0.498, 0.658, 0.332, 0.431, 0.053, 0.531];
            var tests = [{
                name: 'no parameters',
                record: {},
                result: {
                    min: 0,
                    max: null,
                    color: {'0': {r: 0, g: 0, b: 0, a: 0}, '1': {r: 1, g: 1, b: 0, a: 1}}
                }
            }, {
                name: 'normalize range, one value',
                record: {normalizeRange: true, colorRange: ['red'], rangeValues: [0.5]},
                result: {
                    min: 0,
                    max: null,
                    color: {'0': {r: 0, g: 0, b: 0, a: 0}, '1': {r: 1, g: 1, b: 0, a: 1}, '0.5': 'red'}
                }
            }, {
                name: 'normalize range, several values',
                record: {
                    normalizeRange: true,
                    colorRange: ['blue', 'red', 'green', 'white', 'black'],
                    rangeValues: [-1, -0.2, 0.5, 1.1, 2]},
                result: {
                    min: 0,
                    max: null,
                    color: {'0': 'red', '0.5': 'green', '1': 'white'}
                }
            }, {
                name: 'no normalize range',
                record: {},
                result: {
                    min: 0,
                    max: null,
                    color: {'0': {r: 0, g: 0, b: 0, a: 0}, '1': {r: 1, g: 1, b: 0, a: 1}}
                }
            }, {
                name: 'set range',
                record: {colorRange: ['red', 'blue'], rangeValues: [0, 1]},
                result: {
                    min: 0,
                    max: 1,
                    color: {'0': 'red', '1': 'blue'}
                }
            }, {
                name: 'set range, more values',
                record: {colorRange: ['red', 'blue', 'green'], rangeValues: [0, 0.2, 0.8]},
                result: {
                    min: 0,
                    max: 0.8,
                    color: {'0': 'red', '0.25': 'blue', '1': 'green'}
                }
            }, {
                name: 'set range, more range',
                record: {colorRange: ['red', 'blue'], rangeValues: [0.8, 0.8]},
                result: {
                    min: 0.8,
                    max: 0.8,
                    color: {'0': {r: 0, g: 0, b: 0, a: 0}, '1': 'red'}
                }
            }];
            tests.forEach(function (test) {
                it(test.name, function () {
                    var heatmapColorTable = largeImageAnnotation.annotations.convertFeatures.heatmapColorTable;
                    var obj = heatmapColorTable(test.record, values);
                    expect(obj.min).toBe(test.result.min);
                    expect(obj.max).toBe(test.result.max);
                    expect(obj.color).toEqual(test.result.color);
                });
            });
        });
    });

    describe('style', function () {
        it('color names', function () {
            var obj = largeImageAnnotation.annotations.style({
                fillColor: 'red',
                lineColor: 'black'
            });
            expect(obj.fillColor).toBe('#ff0000');
            expect(obj.fillOpacity).toBe(1);
            expect(obj.strokeColor).toBe('#000000');
            expect(obj.strokeOpacity).toBe(1);
        });
        it('hex colors', function () {
            var obj = largeImageAnnotation.annotations.style({
                fillColor: '#ff0000',
                lineColor: '#00ff00'
            });
            expect(obj.fillColor).toBe('#ff0000');
            expect(obj.fillOpacity).toBe(1);
            expect(obj.strokeColor).toBe('#00ff00');
            expect(obj.strokeOpacity).toBe(1);
        });
        it('rgba colors', function () {
            var obj = largeImageAnnotation.annotations.style({
                fillColor: 'rgba(255,0,0,0.5)',
                lineColor: 'rgba(0,255,255,0.5)'
            });
            expect(obj.fillColor).toBe('#ff0000');
            expect(obj.fillOpacity).toBe(0.5);
            expect(obj.strokeColor).toBe('#00ffff');
            expect(obj.strokeOpacity).toBe(0.5);
        });
        it('line width, no colors', function () {
            var obj = largeImageAnnotation.annotations.style({
                lineWidth: 2
            });
            expect(obj).toEqual({
                strokeWidth: 2
            });
        });
    });

    describe('convert', function () {
        it('rectangle', function () {
            var element = {
                type: 'rectangle',
                id: 'a',
                center: [10, 20, 0],
                width: 5,
                height: 10,
                rotation: 0
            };
            var obj = largeImageAnnotation.annotations.convert([element]);
            var features = obj.features;

            expect(obj.type).toBe('FeatureCollection');
            expect(features.length).toBe(1);
            expect(features[0].id).toBe('a');

            var properties = features[0].properties;
            expect(properties.strokeWidth).toBe(2);
            expect(properties.fillColor).toBe('#000000');
            expect(properties.fillOpacity).toBe(0);
            expect(properties.strokeColor).toBe('#000000');
            expect(properties.strokeOpacity).toBe(1);
            expect(properties.element.type).toEqual(element.type);
        });

        it('polyline', function () {
            var element = {
                type: 'polyline',
                id: 'a',
                points: [
                    [0, 1, 0],
                    [1, 0, 0]
                ]
            };
            var obj = largeImageAnnotation.annotations.convert([element]);
            var features = obj.features;

            expect(obj.type).toBe('FeatureCollection');
            expect(features.length).toBe(1);
            expect(features[0].id).toBe('a');

            var properties = features[0].properties;
            expect(properties.strokeWidth).toBe(2);
            expect(properties.fillColor).toBe('#000000');
            expect(properties.fillOpacity).toBe(0);
            expect(properties.strokeColor).toBe('#000000');
            expect(properties.strokeOpacity).toBe(1);
            expect(properties.element.type).toEqual(element.type);
        });
    });

    describe('CRUD', function () {
        var item, user, annotationId, annotation;

        it('setup', function () {
            girder.auth.login('admin', 'password').done(function (resp) {
                user = resp;
            }).fail(function (resp) {
                console.error(resp);
            });
            waitsFor(function () {
                return user;
            }, 'admin to login');

            runs(function () {
                girder.rest.restRequest({
                    url: 'item?text=empty'
                }).done(function (l) {
                    expect(l.length).toBeGreaterThan(0);
                    item = l[0];
                });
            });
            waitsFor(function () {
                return item;
            }, 'Get an item id');
        });

        it('create a new annotation', function () {
            var model = new largeImageAnnotation.models.AnnotationModel({itemId: item._id});
            var done;

            model.elements().add({
                center: [5, 5, 0],
                height: 1,
                rotation: 0,
                type: 'rectangle',
                width: 1
            });

            model.save().done(function (resp) {
                expect(model.id).toBeDefined();
                annotationId = model.id;
                expect(resp.annotation).toBeDefined();
                expect(resp.annotation.elements).toBeDefined();
                expect(resp.annotation.elements.length).toBe(1);
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });

            waitsFor(function () {
                return done;
            });
        });

        it('fetch an existing annotation', function () {
            var done;
            annotation = new largeImageAnnotation.models.AnnotationModel({_id: annotationId});
            annotation.fetch().done(function () {
                expect(annotation.get('itemId')).toBeDefined();
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });
            waitsFor(function () {
                return done;
            }, 'fetch to complete');
        });

        it('update an existing annotation', function () {
            var done;
            var elements = annotation.elements();
            elements.add({
                center: [10, 10, 0],
                height: 2,
                rotation: 0,
                type: 'rectangle',
                width: 2,
                label: {}
            });

            annotation.save().done(function (resp) {
                expect(resp.annotation).toBeDefined();
                expect(resp.annotation.elements).toBeDefined();
                expect(resp.annotation.elements.length).toBe(2);
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });

            waitsFor(function () {
                return done;
            }, 'annotation to save');
        });

        it('update a paged annotation', function () {
            var done;

            annotation._pageElements = true;
            annotation.save().done(function (resp) {
                expect(resp.annotation).toBeDefined();
                expect(resp.annotation.elements).not.toBeDefined();
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });

            waitsFor(function () {
                return done;
            }, 'annotation to save');
        });

        it('destroy an existing annotation', function () {
            var done;

            annotation.destroy().done(function () {
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });
            waitsFor(function () {
                return done;
            }, 'annotation to destroy');

            runs(function () {
                // silence rest request error message
                done = false;
                annotation = new largeImageAnnotation.models.AnnotationModel({_id: annotationId});
                annotation.fetch().done(function () {
                    expect(annotation.get('_active')).toBe(false);
                    done = true;
                }).fail(function (resp) {
                    console.error(resp);
                });
            });
            waitsFor(function () {
                return done;
            }, 'fetch to get an inactive annotation');
        });

        it('delete an annotation without unbinding events', function () {
            var model = new largeImageAnnotation.models.AnnotationModel({itemId: item._id});
            var id;
            var done;
            var eventCalled;

            model.listenTo(model, 'change', function () { eventCalled = true; });
            model.save().done(function (resp) {
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });

            waitsFor(function () {
                return done;
            }, 'annotation to save');
            runs(function () {
                id = model.id;
                done = false;
                model.delete().done(function () {
                    done = true;
                });
            });

            waitsFor(function () {
                return done;
            }, 'annotation to delete');
            runs(function () {
                var model2;

                done = false;
                model2 = new largeImageAnnotation.models.AnnotationModel({_id: id});
                model2.fetch().done(function () {
                    expect(annotation.get('_active')).toBe(false);
                    done = true;
                }).fail(function (resp) {
                    console.error(resp);
                });
            });

            waitsFor(function () {
                return done;
            }, 'fetch to return an inactive annotation');
            runs(function () {
                eventCalled = false;
                model.trigger('change');
                expect(eventCalled).toBe(true);
            });
        });

        it('cannot create an annotation without an itemId', function () {
            var model = new largeImageAnnotation.models.AnnotationModel();
            expect(function () {
                model.save();
            }).toThrow();
        });

        it('get an annotation name', function () {
            var model = new largeImageAnnotation.models.AnnotationModel({
                itemId: item._id,
                annotation: {
                    name: 'test annotation'
                }
            });
            expect(model.name()).toBe('test annotation');
        });

        it('create a large annotation', function () {
            var model = new largeImageAnnotation.models.AnnotationModel({itemId: item._id});
            var done;

            for (var i = 0; i < 1000; i += 1) {
                model.elements().add({
                    center: [5 + (i % 100), 5 + Math.round(i / 100), 0],
                    height: 1 + (i % 4),
                    rotation: 0,
                    type: 'rectangle',
                    width: 1 + (i % 5)
                });
            }

            model.save().done(function (resp) {
                expect(model.id).toBeDefined();
                annotationId = model.id;
                expect(resp.annotation).toBeDefined();
                expect(resp.annotation.elements).toBeDefined();
                expect(resp.annotation.elements.length).toBe(1000);
                done = true;
            }).fail(function (resp) {
                console.error(resp);
            });

            waitsFor(function () {
                return done;
            });
        });

        it('fetch a paged annotation', function () {
            var done;
            annotation = new largeImageAnnotation.models.AnnotationModel({_id: annotationId, maxDetails: 100, maxCentroids: 500});
            annotation.once('g:fetched', function () { done = true; });
            annotation.fetch().done(function () {
                expect(annotation.get('itemId')).toBeDefined();
            }).fail(function (resp) {
                console.error(resp);
            });
            waitsFor(function () {
                return done;
            }, 'fetch to complete');
            runs(function () {
                expect(annotation._centroids).toBeDefined();
                expect(annotation._centroids.partial).toBeDefined();
            });
        });
    });
});
