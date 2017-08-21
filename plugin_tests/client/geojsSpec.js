/* globals beforeEach, afterEach, describe, it, expect, sinon, girder, Backbone */
/* eslint-disable camelcase, no-new */

girderTest.addScripts([
    '/clients/web/static/built/plugins/large_image/extra/sinon.js',
    '/clients/web/static/built/plugins/large_image/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    var itemId, annotationId, interactor;

    function closeTo(a, b, tol) {
        var i;
        tol = tol || 6;
        expect(a.length).toBe(b.length);
        for (i = 0; i < a.length; i += 1) {
            expect(a[i]).toBeCloseTo(b[i], tol);
        }
    }

    describe('setup', function () {
        it('create the admin user', function () {
            girderTest.createUser(
                'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
        });
        it('go to collections page', function () {
            runs(function () {
                $("a.g-nav-link[g-target='collections']").click();
            });

            waitsFor(function () {
                return $('.g-collection-create-button:visible').length > 0;
            }, 'navigate to collections page');

            runs(function () {
                expect($('.g-collection-list-entry').length).toBe(0);
            });
        });
        it('create collection', girderTest.createCollection('test', '', 'image'));
        it('upload test file', function () {
            girderTest.waitForLoad();
            runs(function () {
                $('.g-folder-list-link:first').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('plugins/large_image/plugin_tests/test_files/small_la.tiff');
            });
            girderTest.waitForLoad();
            runs(function () {
                itemId = $('.large_image_thumbnail img').prop('src').match(/\/item\/([^/]*)/)[1];
            });
        });
        it('upload test annotation', function () {
            runs(function () {
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'test annotation',
                        elements: [{
                            type: 'rectangle',
                            center: [200, 200, 0],
                            width: 400,
                            height: 400,
                            rotation: 0
                        }]
                    })
                }).then(function (resp) {
                    annotationId = resp._id;
                    return null;
                });
            });

            girderTest.waitForLoad();
            runs(function () {
                expect(annotationId).toBeDefined();
            });
        });
    });

    describe('Geojs viewer', function () {
        var girder, large_image, $el, GeojsViewer, viewer, annotation, layerSpy;

        beforeEach(function () {
            girder = window.girder;
            large_image = girder.plugins.large_image;
            GeojsViewer = large_image.views.imageViewerWidget.geojs;
        });

        it('script is loaded', function () {
            $el = $('<div/>').appendTo('body')
                .css({
                    width: '400px',
                    height: '300px'
                });
            viewer = new GeojsViewer({
                el: $el,
                itemId: itemId,
                parentView: null,
                hoverEvents: true
            });
            viewer.once('g:beforeFirstRender', function () {
                window.geo.util.mockVGLRenderer();
            });
            waitsFor(function () {
                return $('.geojs-layer.active').length >= 1;
            }, 'viewer to load');
            runs(function () {
                expect(viewer.viewer.size()).toEqual({
                    width: 400,
                    height: 300
                });
                interactor = viewer.viewer.interactor();
            });
        });

        it('drawAnnotation', function () {
            runs(function () {
                annotation = new large_image.models.AnnotationModel({
                    _id: annotationId
                });
                annotation.fetch();
            });

            girderTest.waitForLoad();
            runs(function () {
                sinon.spy(annotation, 'setView');
                viewer.drawAnnotation(annotation);
                viewer.viewer.zoom(5);
            });

            girderTest.waitForLoad();
            runs(function () {
                expect(viewer._layers[annotationId]).toBeDefined();
                // geojs makes two features for a polygon
                expect(viewer._layers[annotationId].features().length >= 1).toBe(true);

                layerSpy = sinon.spy(viewer._layers[annotationId], '_exit');

                sinon.assert.called(annotation.setView);
                viewer.viewer.zoom(1);
            });
        });

        it('mouse over events', function () {
            var mouseon, mouseover, context = {};
            runs(function () {
                function onMouseOn(element, annotation) {
                    expect(annotation).toBe(annotationId);
                    mouseon = true;
                }
                function onMouseOver(element, annotation) {
                    expect(annotation).toBe(annotationId);
                    mouseover = true;
                }
                viewer.on('g:mouseOnAnnotation', onMouseOn, context);
                viewer.on('g:mouseOverAnnotation', onMouseOver, context);
                interactor.simulateEvent('mousemove', {
                    map: viewer.viewer.gcsToDisplay({x: 1000, y: 1000})
                });
                interactor.simulateEvent('mousemove', {
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });
            });

            waitsFor(function () {
                return mouseon && mouseover;
            }, 'events to be fired');

            runs(function () {
                viewer.off(null, null, context);
            });
        });

        it('mouse out events', function () {
            var mouseout, mouseoff, context = {};
            runs(function () {
                function onMouseOut(element, annotation) {
                    expect(annotation).toBe(annotationId);
                    mouseout = true;
                }
                function onMouseOff(element, annotation) {
                    expect(annotation).toBe(annotationId);
                    mouseoff = true;
                }
                viewer.on('g:mouseOutAnnotation', onMouseOut, context);
                viewer.on('g:mouseOffAnnotation', onMouseOff, context);
                interactor.simulateEvent('mousemove', {
                    map: viewer.viewer.gcsToDisplay({x: 1000, y: 1000})
                });
            });

            waitsFor(function () {
                return mouseoff && mouseout;
            }, 'events to be fired');

            runs(function () {
                viewer.off(null, null, context);
            });
        });

        it('mouse click events', function () {
            var mouseclick, context = {};
            runs(function () {
                function onMouseClick(element, annotation) {
                    expect(annotation).toBe(annotationId);
                    mouseclick = true;
                }
                viewer.on('g:mouseClickAnnotation', onMouseClick, context);
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });
            });

            waitsFor(function () {
                return mouseclick;
            }, 'event to be fired');

            runs(function () {
                viewer.off(null, null, context);
            });
        });

        it('mouse reset events', function () {
            var mousereset, context = {};
            runs(function () {
                function onMouseReset(annotation) {
                    expect(annotation.id).toBe(annotationId);
                    mousereset = true;
                }
                viewer.on('g:mouseResetAnnotation', onMouseReset, context);
                annotation.trigger('g:fetched');
            });

            waitsFor(function () {
                return mousereset;
            }, 'event to be fired');

            runs(function () {
                viewer.off(null, null, context);
                viewer.viewer.zoom(1);
            });
        });

        it('removeAnnotation', function () {
            viewer.removeAnnotation(annotation);
            expect(viewer._layers).toEqual({});
            sinon.assert.calledOnce(layerSpy);
        });

        it('drawAnnotation without fetching', function () {
            var model;
            runs(function () {
                model = new large_image.models.AnnotationModel({
                    _id: 'invalid',
                    annotation: {
                        name: 'no fetch',
                        elements: [{
                            type: 'rectangle',
                            center: [100, 100, 0],
                            rotation: 0,
                            width: 10,
                            height: 10
                        }]
                    }
                });
                sinon.spy(model, 'setView');
                viewer.drawAnnotation(model, {fetch: false});
                viewer.viewer.zoom(5);
            });

            girderTest.waitForLoad();
            runs(function () {
                sinon.assert.notCalled(model.setView);
                viewer.viewer.zoom(1);
            });
        });

        it('drawRegion', function () {
            var model = new Backbone.Model();
            runs(function () {
                var pt = viewer.viewer.gcsToDisplay({x: 100, y: 100});
                viewer.drawRegion(model);
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: pt
                });
            });
            runs(function () {
                var pt = viewer.viewer.gcsToDisplay({x: 115, y: 115});
                // Due to a bug in geojs, this raises an error, but it is required to simulate
                // a drag event on the map.
                try {
                    interactor.simulateEvent('mousemove', {
                        button: 'left',
                        map: pt
                    });
                } catch (e) {
                }
            });
            runs(function () {
                var pt = viewer.viewer.gcsToDisplay({x: 115, y: 115});
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: pt
                });
            });
            waitsFor(function () {
                return !!model.get('value');
            });

            runs(function () {
                expect(model.get('value')).toEqual([100, 100, 15, 15]);
            });
        });

        it('draw point', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('point').then(function (elements) {
                    expect(elements.length).toBe(1);
                    expect(elements[0].type).toBe('point');
                    closeTo(elements[0].center, [100, 200, 0]);
                    created = true;
                    return null;
                });
                var pt = viewer.viewer.gcsToDisplay({x: 100, y: 200});
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: pt
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: pt
                });
            });

            waitsFor(function () {
                return created;
            });
        });

        it('draw polygon', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('polygon').then(function (elements) {
                    expect(elements.length).toBe(1);
                    expect(elements[0].type).toBe('polyline');
                    expect(elements[0].closed).toBe(true);
                    expect(elements[0].points.length).toBe(3);
                    closeTo(elements[0].points[0], [100, 200, 0]);
                    closeTo(elements[0].points[1], [200, 200, 0]);
                    closeTo(elements[0].points[2], [200, 300, 0]);
                    created = true;
                    return null;
                });

                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });

                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
            });

            waitsFor(function () {
                return created;
            });
        });

        it('draw line', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('line').then(function (elements) {
                    expect(elements.length).toBe(1);
                    expect(elements[0].type).toBe('polyline');
                    expect(elements[0].closed).toBe(false);
                    expect(elements[0].points.length).toBe(3);
                    closeTo(elements[0].points[0], [100, 200, 0]);
                    closeTo(elements[0].points[1], [200, 200, 0]);
                    closeTo(elements[0].points[2], [200, 300, 0]);
                    created = true;
                    return null;
                });

                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 200})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });

                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 300})
                });
            });

            waitsFor(function () {
                return created;
            });
        });

        it('destroy the viewer', function () {
            viewer.destroy();
            expect($('.geojs-layer').length).toBe(0);
        });
    });
});
