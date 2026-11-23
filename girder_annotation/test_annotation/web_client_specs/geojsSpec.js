/* globals beforeEach, afterEach, describe, it, expect, sinon, girder, Backbone, _, girderTest, $, runs, waitsFor */
/* eslint-disable camelcase, no-new */

girderTest.importPlugin('jobs', 'worker', 'large_image', 'large_image_annotation');
girderTest.addScripts([
    '/static/built/plugins/large_image/extra/sinon.js'
]);

girderTest.startApp();

$(function () {
    var itemId, annotationId, overlayAnnotationId, interactor;

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
                girderTest.binaryUpload('${large_image}/../../test/test_files/small_la.tiff'); // eslint-disable-line no-template-curly-in-string
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
            waitsFor(function () {
                return annotationId !== undefined;
            });
            girderTest.waitForLoad();
            runs(function () {
                expect(annotationId).toBeDefined();
            });
        });
        it('upload test overlay annotation', function () {
            runs(function () {
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'test overlay annotation',
                        elements: [{
                            type: 'image',
                            girderId: itemId,
                            opacity: 0.5,
                            transform: {
                                xoffset: 10,
                                yoffset: 15
                            }
                        }]
                    })
                }).then(function (resp) {
                    overlayAnnotationId = resp._id;
                    return null;
                });
            });
            waitsFor(function () {
                return overlayAnnotationId !== undefined;
            });
            girderTest.waitForLoad();
            runs(function () {
                expect(overlayAnnotationId).toBeDefined();
            });
        });
    });

    describe('Geojs viewer', function () {
        var girder, large_image, $el, GeojsViewer, viewer, annotation, overlayAnnotation, featureSpy, largeImageAnnotation;

        beforeEach(function () {
            girder = window.girder;
            large_image = girder.plugins.large_image;
            largeImageAnnotation = girder.plugins.large_image_annotation;
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
                try {
                    window.geo.util.mockWebglRenderer();
                } catch (err) {
                    // if this is already mocked, do nothing.
                }
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
            var setViewSpy, firstCount;
            runs(function () {
                annotation = new largeImageAnnotation.models.AnnotationModel({
                    _id: annotationId
                });
                annotation.fetch();
            });

            girderTest.waitForLoad();
            runs(function () {
                setViewSpy = sinon.spy(annotation, 'setView');
                viewer.drawAnnotation(annotation);
                viewer.viewer.zoom(5);
            });

            girderTest.waitForLoad();
            runs(function () {
                expect(viewer._annotations[annotationId]).toBeDefined();
                // geojs makes two features for a polygon
                expect(viewer._annotations[annotationId].features.length >= 1).toBe(true);

                featureSpy = sinon.spy(viewer._annotations[annotationId].features[0], '_exit');

                sinon.assert.called(annotation.setView);
                firstCount = setViewSpy.callCount;
                viewer.viewer.zoomRange({max: 12});
                viewer.viewer.zoom(12);
                viewer.viewer.zoom(1);
                expect(setViewSpy.callCount).toBe(firstCount + 2);
            });
        });

        it('draw overlay', function () {
            var projStringSpy;
            runs(function () {
                overlayAnnotation = new largeImageAnnotation.models.AnnotationModel({
                    _id: overlayAnnotationId
                });
                overlayAnnotation.fetch();
            });
            girderTest.waitForLoad();
            runs(function () {
                projStringSpy = sinon.spy(viewer, '_getOverlayTransformProjString');
                viewer.drawAnnotation(overlayAnnotation);
            });
            girderTest.waitForLoad();
            runs(function () {
                const annotationRecord = viewer._annotations[overlayAnnotationId] || undefined;
                expect(annotationRecord).toBeDefined();
                expect(projStringSpy.callCount).toBe(1);
            });
        });

        it('set overlay opacity', function () {
            var overlayId = viewer._annotations[overlayAnnotationId].overlays[0].id;
            var layer;
            waitsFor(function () {
                layer = _.find(viewer.viewer.layers(), function (layer) {
                    return layer.id() === overlayId;
                });
                return layer;
            }, 'overlay layer to be created');
            runs(function () {
                expect(layer.opacity()).toBe(0.5);
                viewer.setAnnotationOpacity(overlayAnnotationId, 0.5);
                expect(layer.opacity()).toBe(0.25);
                viewer.setAnnotationOpacity(overlayAnnotationId);
                expect(layer.opacity()).toBe(0.5);
            });
        });

        it('generates pixelmap layer parameters', function () {
            const overlayMetadata = {
                sizeX: 500,
                sizeY: 500,
                tileWidth: 256,
                tileHeight: 256,
                levels: viewer.levels
            };
            const overlayId = '012345678901234567890123';
            const pixelMapElement = {
                type: 'pixelmap',
                id: '00001111222233334444',
                opacity: 0.5,
                girderId: overlayId,
                boundaries: false,
                values: [0, 1, 0, 1, 0, 1],
                categories: [
                    {fillColor: '#000000'},
                    {fillColor: '#ffffff'}
                ]
            };
            const pixelmapLayerParams = viewer._generateOverlayLayerParams(overlayMetadata, overlayId, pixelMapElement);
            const expectedUrl = 'api/v1/item/' + overlayId + '/tiles/zxy/{z}/{x}/{y}?encoding=PNG';
            expect(pixelmapLayerParams.url.endsWith(expectedUrl)).toBe(true);
            expect(pixelmapLayerParams.data).toEqual(pixelMapElement.values);

            pixelMapElement.boundaries = true;
            const pixelmapLayerParamsWithBoundaries = viewer._generateOverlayLayerParams(overlayMetadata, overlayId, pixelMapElement);
            const expectedDataArray = [0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1];
            expect(pixelmapLayerParamsWithBoundaries.data).toEqual(expectedDataArray);
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

        it('fires overlay event', function () {
            const eventType = window.geo.event.feature.mouseclick;
            const mockEvent = {
                event: eventType,
                data: {}
            };
            const mockOverlay = overlayAnnotation.elements().models[0] || {};
            const mockLayer = viewer.viewer.createLayer('osm');
            var mouseclick = false;
            runs(function () {
                function handleOverlayEvent() {
                    mouseclick = true;
                }

                viewer.on('g:mouseClickAnnotationOverlay', handleOverlayEvent);
                viewer._onMouseFeature(mockEvent, mockOverlay, mockLayer);
            });

            waitsFor(function () {
                return mouseclick;
            }, 'event to be fired');

            runs(function () {
                viewer.viewer.deleteLayer(mockLayer);
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
            viewer.removeAnnotation(overlayAnnotation);
            expect(viewer._annotations).toEqual({});
            sinon.assert.calledOnce(featureSpy);
        });

        it('drawAnnotation without fetching', function () {
            var model;
            runs(function () {
                model = new largeImageAnnotation.models.AnnotationModel({
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
                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: pt
                });
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
                    // these could be in any order, so sort them
                    var points = elements[0].points.sort(function (a, b) {
                        if (a[0] !== b[0]) {
                            return a[0] < b[0] ? -1 : 1;
                        }
                        return a[1] < b[1] ? -1 : 1;
                    });
                    closeTo(points[0], [100, 200, 0]);
                    closeTo(points[1], [200, 200, 0]);
                    closeTo(points[2], [200, 300, 0]);
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

        it('draw rectangle', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('rectangle').then(function (elements) {
                    expect(elements.length).toBe(1);
                    closeTo(elements[0].center, [150, 300, 0]);
                    expect(elements[0].width).toBe(100);
                    expect(elements[0].height).toBe(200);
                    created = true;
                    return null;
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
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
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
            });

            waitsFor(function () {
                return created;
            });
        });

        it('draw ellipse', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('ellipse').then(function (elements) {
                    expect(elements.length).toBe(1);
                    closeTo(elements[0].center, [150, 300, 0]);
                    expect(elements[0].width).toBe(100);
                    expect(elements[0].height).toBe(200);
                    created = true;
                    return null;
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 200})
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
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 400})
                });
            });

            waitsFor(function () {
                return created;
            });
        });

        it('draw circle', function () {
            var created;

            runs(function () {
                viewer.startDrawMode('circle').then(function (elements) {
                    expect(elements.length).toBe(1);
                    closeTo(elements[0].center, [200, 200, 0]);
                    expect(elements[0].radius).toBe(100);
                    created = true;
                    return null;
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 100, y: 100})
                });

                interactor.simulateEvent('mousemove', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 500})
                });
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 500})
                });
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: viewer.viewer.gcsToDisplay({x: 200, y: 500})
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

        describe('text elements', function () {
            var model, longText, center1, center2;

            function clickAt(x, y) {
                var pt = viewer.viewer.gcsToDisplay({x: x, y: y});
                interactor.simulateEvent('mousedown', {button: 'left', map: pt});
                interactor.simulateEvent('mouseup', {button: 'left', map: pt});
            }

            function typeText(text) {
                var input = $el.find('.g-li-annotation-text-edit');
                expect(input.length).toBe(1);
                input.val(text).trigger('input');
                return input;
            }

            function key(input, name, ctrl) {
                input.trigger($.Event('keydown', {key: name, ctrlKey: !!ctrl}));
            }

            it('draw text', function () {
                var created, triggered;

                runs(function () {
                    girder.events.once('g:annotationCreated', function (element) {
                        triggered = element;
                    });
                    viewer.startDrawMode('text', {textStyle: {lineColor: '#ff0000', fontSize: 20, lineWidth: 5}}).then(function (elements) {
                        created = elements;
                        return null;
                    });
                    expect(viewer.annotationLayer.mode()).toBe('point');
                    clickAt(100, 200);
                });
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown');
                runs(function () {
                    var input = $el.find('.g-li-annotation-text-edit');
                    var pt = viewer.viewer.gcsToDisplay({x: 100, y: 200});
                    expect(viewer.annotationLayer.mode()).toBe(null);
                    expect(viewer.annotationLayer.annotations().length).toBe(0);
                    expect(document.activeElement).toBe(input[0]);
                    expect(input.val()).toBe('');
                    expect(parseFloat(input.css('left'))).toBeCloseTo(pt.x, 0);
                    expect(parseFloat(input.css('top'))).toBeCloseTo(pt.y, 0);
                    expect(input.css('font-size')).toBe('20px');
                    expect(input.css('line-height')).toBe('25px');
                    expect(input.css('color')).toBe('rgb(255, 0, 0)');
                    expect(input.css('background-color')).toBe('rgba(0, 0, 0, 0)');
                    // tabs and control characters are fixed while typing
                    typeText('  A\tcomment\u0007\r\non two lines ');
                    expect(input.val()).toBe('  A comment\non two lines ');
                    expect(input.attr('rows')).toBe('2');
                    // the editor moves with the map
                    var zoom = viewer.viewer.zoom();
                    viewer.viewer.zoom(zoom + 1);
                    var pt2 = viewer.viewer.gcsToDisplay({x: 100, y: 200});
                    expect(Math.abs(pt2.x - pt.x) + Math.abs(pt2.y - pt.y)).toBeGreaterThan(5);
                    expect(parseFloat(input.css('left'))).toBeCloseTo(pt2.x, 0);
                    expect(parseFloat(input.css('top'))).toBeCloseTo(pt2.y, 0);
                    viewer.viewer.zoom(zoom);
                    // enter adds a line and doesn't finish
                    key(input, 'Enter');
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                    expect(created).toBe(undefined);
                    key(input, 'Enter', true);
                });
                waitsFor(function () {
                    return created;
                }, 'the element to be created');
                runs(function () {
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                    expect(created.length).toBe(1);
                    expect(created[0].type).toBe('text');
                    expect(created[0].text).toBe('A comment\non two lines');
                    expect(created[0].lineColor).toBe('#ff0000');
                    expect(created[0].fontSize).toBe(20);
                    expect(created[0].lineWidth).toBe(undefined);
                    expect(created[0].fillColor).toBe(undefined);
                    expect(created[0].id).toMatch(/^[0-9a-f]{24}$/);
                    closeTo(created[0].center, [100, 200, 0]);
                    expect(triggered).toBe(created[0]);
                });
            });

            it('draw text finishes when focus is lost', function () {
                var created;

                runs(function () {
                    viewer.startDrawMode('text', {trigger: false}).then(function (elements) {
                        created = elements;
                        return null;
                    });
                    clickAt(150, 250);
                });
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown');
                runs(function () {
                    typeText('Blurred').trigger('blur');
                });
                waitsFor(function () {
                    return created;
                }, 'the element to be created');
                runs(function () {
                    expect(created[0].text).toBe('Blurred');
                    expect(created[0].lineColor).toBe('rgb(0,0,0)');
                    expect(created[0].fontSize).toBe(16);
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                });
            });

            it('empty text is discarded', function () {
                var created, rejected = 0;

                function draw() {
                    viewer.startDrawMode('text').then(function (elements) {
                        created = elements;
                        return null;
                    }, function () {
                        rejected += 1;
                    });
                    clickAt(100, 200);
                }
                runs(draw);
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown');
                runs(function () {
                    key(typeText(' \n\t  '), 'Enter', true);
                });
                waitsFor(function () {
                    return rejected === 1;
                }, 'the whitespace element to be discarded');
                runs(function () {
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                    draw();
                });
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown again');
                runs(function () {
                    // escape cancels even if there is text
                    key(typeText('Canceled'), 'Escape');
                });
                waitsFor(function () {
                    return rejected === 2;
                }, 'the canceled element to be discarded');
                runs(function () {
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                    expect(created).toBe(undefined);
                });
            });

            it('restarting text draw mode abandons text entry', function () {
                var settled = false;

                runs(function () {
                    viewer.startDrawMode('text', {trigger: false}).always(function () {
                        settled = true;
                    });
                    clickAt(100, 200);
                });
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown');
                runs(function () {
                    typeText('Abandoned');
                    viewer.startDrawMode('text', {trigger: false});
                    // a new point is placed before the text is typed
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                    expect(viewer.annotationLayer.mode()).toBe('point');
                    expect(settled).toBe(false);
                    viewer.startDrawMode(null);
                });
            });

            it('starting another draw mode abandons text entry', function () {
                var settled = false;

                runs(function () {
                    viewer.startDrawMode('text').always(function () {
                        settled = true;
                    });
                    clickAt(100, 200);
                });
                waitsFor(function () {
                    return $el.find('.g-li-annotation-text-edit').length === 1;
                }, 'the text editor to be shown');
                runs(function () {
                    typeText('Abandoned');
                    viewer.startDrawMode('point');
                    expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                    expect(settled).toBe(false);
                    viewer.startDrawMode(null);
                });
            });

            it('startTextEdit and finishTextEdit', function () {
                var results = [];

                longText = [];
                for (var i = 0; i < 200; i += 1) {
                    var words = [];
                    for (var j = 0; j < 15; j += 1) {
                        words.push('word' + (i * 15 + j));
                    }
                    longText.push(words.join(' '));
                }
                longText = longText.join('\n');

                function record(name) {
                    // done and fail are called synchronously
                    return viewer.startTextEdit({center: [100, 100, 0], text: name, fontSize: 12}).done(function (text) {
                        results.push(['resolved', text]);
                    }).fail(function () {
                        results.push(['rejected', name]);
                    });
                }
                record('first');
                expect($el.find('.g-li-annotation-text-edit').val()).toBe('first');
                // starting a second edit finishes the first
                record('second');
                expect(results).toEqual([['resolved', 'first']]);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                typeText('changed');
                viewer.finishTextEdit();
                expect(results[1]).toEqual(['resolved', 'changed']);
                record('third');
                viewer.finishTextEdit(false);
                expect(results[2]).toEqual(['rejected', 'third']);
                record('fourth');
                viewer.finishTextEdit(null);
                expect(results.length).toBe(3);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                // nothing happens if there is no editor
                viewer.finishTextEdit();
                expect(results.length).toBe(3);
                // a comment of a few thousand words can be edited
                record(longText);
                expect($el.find('.g-li-annotation-text-edit').val()).toBe(longText);
                expect($el.find('.g-li-annotation-text-edit').attr('rows')).toBe('200');
                typeText(longText + '\nand one more line');
                expect($el.find('.g-li-annotation-text-edit').attr('rows')).toBe('201');
                viewer.finishTextEdit();
                expect(results[3]).toEqual(['resolved', longText + '\nand one more line']);
            });

            it('the enter key can finish editing', function () {
                var results = [], input;

                function record(text, options) {
                    viewer.startTextEdit({center: [100, 100, 0], text: text}, options).done(function (text) {
                        results.push(text);
                    });
                    return $el.find('.g-li-annotation-text-edit');
                }
                // by default, enter doesn't finish and control-enter does
                input = record('default');
                key(input, 'Enter');
                expect(results).toEqual([]);
                input.trigger($.Event('keydown', {key: 'Enter', shiftKey: true}));
                expect(results).toEqual([]);
                key(input, 'Enter', true);
                expect(results).toEqual(['default']);
                input = record('explicit', {enterKey: 'newline'});
                key(input, 'Enter');
                expect(results.length).toBe(1);
                input.trigger($.Event('keydown', {key: 'Enter', metaKey: true}));
                expect(results).toEqual(['default', 'explicit']);
                // when enter finishes, the modified keys add lines
                input = record('first', {enterKey: 'finish'});
                expect(input.attr('title')).toMatch(/^Enter or click elsewhere/);
                input.trigger($.Event('keydown', {key: 'Enter', shiftKey: true}));
                expect(results.length).toBe(2);
                input[0].setSelectionRange(5, 5);
                key(input, 'Enter', true);
                expect(results.length).toBe(2);
                expect(input.val()).toBe('first\n');
                expect(input.attr('rows')).toBe('2');
                input.val('first\nsecond').trigger('input');
                input[0].setSelectionRange(2, 4);
                input.trigger($.Event('keydown', {key: 'Enter', metaKey: true}));
                expect(input.val()).toBe('fi\nt\nsecond');
                expect(input[0].selectionStart).toBe(3);
                key(input, 'Enter');
                expect(results).toEqual(['default', 'explicit', 'fi\nt\nsecond']);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
            });

            it('move text by dragging and edit it by clicking', function () {
                var results = [], handle, offset, pt, center;

                function record(options) {
                    viewer.startTextEdit({center: [100, 200, 0], text: 'Movable\ntext', fontSize: 20, lineColor: '#0000ff'}, options).done(function (text, center) {
                        results.push(['resolved', text, center]);
                    }).fail(function () {
                        results.push(['rejected']);
                    });
                    return $el.find('.g-li-annotation-text-move');
                }
                function mouse(target, name, dx, dy) {
                    target.trigger($.Event(name, {which: 1, pageX: offset.left + dx, pageY: offset.top + dy}));
                }
                // without the option, the text is edited immediately
                viewer.startTextEdit({center: [100, 200, 0], text: 'Not movable'});
                expect($el.find('.g-li-annotation-text-move').length).toBe(0);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                viewer.finishTextEdit(null);

                handle = record({movable: true});
                expect(handle.length).toBe(1);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                expect(handle.text()).toBe('Movable\ntext');
                expect(handle.css('font-size')).toBe('20px');
                expect(handle.css('color')).toBe('rgb(0, 0, 255)');
                expect(handle.css('white-space')).toBe('pre');
                expect(document.activeElement).toBe(handle[0]);
                pt = viewer.viewer.gcsToDisplay({x: 100, y: 200});
                expect(parseFloat(handle.css('left'))).toBeCloseTo(pt.x, 0);
                expect(parseFloat(handle.css('top'))).toBeCloseTo(pt.y, 0);
                offset = handle.offset();
                // drag it
                mouse(handle, 'mousedown', 5, 5);
                mouse($(document), 'mousemove', 6, 6);
                // a tiny movement doesn't move it
                expect(parseFloat(handle.css('left'))).toBeCloseTo(pt.x, 0);
                mouse($(document), 'mousemove', 35, 25);
                expect(parseFloat(handle.css('left'))).toBeCloseTo(pt.x + 30, 0);
                expect(parseFloat(handle.css('top'))).toBeCloseTo(pt.y + 20, 0);
                mouse($(document), 'mouseup', 35, 25);
                // it is still there and wasn't switched to editing
                expect($el.find('.g-li-annotation-text-move').length).toBe(1);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                expect(results).toEqual([]);
                // moving the mouse without the button down does nothing
                mouse($(document), 'mousemove', 100, 100);
                expect(parseFloat(handle.css('left'))).toBeCloseTo(pt.x + 30, 0);
                // it can be dragged again, and releasing over the text works
                offset = handle.offset();
                mouse(handle, 'mousedown', 5, 5);
                mouse($(document), 'mousemove', 15, -5);
                mouse(handle, 'mouseup', 15, -5);
                expect(parseFloat(handle.css('left'))).toBeCloseTo(pt.x + 40, 0);
                expect(parseFloat(handle.css('top'))).toBeCloseTo(pt.y + 10, 0);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(0);
                center = viewer.viewer.displayToGcs({x: pt.x + 40, y: pt.y + 10});
                // finishing without editing reports the new location
                viewer.finishTextEdit();
                expect(results.length).toBe(1);
                expect(results[0][1]).toBe('Movable\ntext');
                closeTo(results[0][2], [center.x, center.y, 0], 3);
                expect($el.find('.g-li-annotation-text-move').length).toBe(0);

                // a click switches to editing
                handle = record({movable: true});
                offset = handle.offset();
                mouse(handle, 'mousedown', 5, 5);
                mouse(handle, 'mouseup', 5, 5);
                expect($el.find('.g-li-annotation-text-move').length).toBe(0);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                expect($el.find('.g-li-annotation-text-edit').val()).toBe('Movable\ntext');
                expect(document.activeElement).toBe($el.find('.g-li-annotation-text-edit')[0]);
                expect(results.length).toBe(1);
                key(typeText('Edited'), 'Enter', true);
                expect(results[1]).toEqual(['resolved', 'Edited', [100, 200, 0]]);

                // drag and then click to edit; both changes are reported
                handle = record({movable: true, enterKey: 'finish'});
                offset = handle.offset();
                mouse(handle, 'mousedown', 5, 5);
                mouse($(document), 'mousemove', 35, 25);
                mouse($(document), 'mouseup', 35, 25);
                offset = handle.offset();
                mouse(handle, 'mousedown', 5, 5);
                mouse($(document), 'mouseup', 5, 5);
                expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                pt = viewer.viewer.gcsToDisplay({x: 100, y: 200});
                expect(parseFloat($el.find('.g-li-annotation-text-edit').css('left'))).toBeCloseTo(pt.x + 30, 0);
                key(typeText('Moved and edited'), 'Enter');
                center = viewer.viewer.displayToGcs({x: pt.x + 30, y: pt.y + 20});
                expect(results[2][1]).toBe('Moved and edited');
                closeTo(results[2][2], [center.x, center.y, 0], 3);

                // enter switches to editing and escape cancels a move
                handle = record({movable: true});
                key(handle, 'Enter');
                expect($el.find('.g-li-annotation-text-edit').length).toBe(1);
                viewer.finishTextEdit(null);
                handle = record({movable: true});
                offset = handle.offset();
                mouse(handle, 'mousedown', 5, 5);
                mouse($(document), 'mousemove', 35, 25);
                mouse($(document), 'mouseup', 35, 25);
                key(handle, 'Escape');
                expect(results[3]).toEqual(['rejected']);
                expect($el.find('.g-li-annotation-text-move').length).toBe(0);
                // losing focus finishes
                handle = record({movable: true});
                handle.trigger('blur');
                expect(results[4]).toEqual(['resolved', 'Movable\ntext', [100, 200, 0]]);
                expect(results.length).toBe(5);
            });

            it('draw text elements', function () {
                runs(function () {
                    // place the text so that it doesn't overlap on screen
                    center1 = viewer.viewer.displayToGcs({x: 100, y: 80});
                    center2 = viewer.viewer.displayToGcs({x: 250, y: 200});
                    model = new largeImageAnnotation.models.AnnotationModel({
                        _id: 'textannotation',
                        annotation: {
                            name: 'text',
                            elements: [{
                                id: 'a00000000000000000000001',
                                type: 'text',
                                center: [center1.x, center1.y, 0],
                                text: 'A comment'
                            }, {
                                id: 'a00000000000000000000002',
                                type: 'text',
                                center: [center2.x, center2.y, 0],
                                text: 'long first line\nshort',
                                lineColor: 'rgba(255, 0, 0, 0.5)',
                                fontSize: 24
                            }, {
                                id: 'a00000000000000000000004',
                                type: 'rectangle',
                                center: [300, 300, 0],
                                rotation: 0,
                                width: 10,
                                height: 10
                            }]
                        }
                    });
                    expect(viewer.textLayer).toBe(null);
                    viewer.drawAnnotation(model, {fetch: false});
                });
                girderTest.waitForLoad();
                runs(function () {
                    var features = viewer._annotations[model.id].features;
                    var text = features.filter(function (feature) {
                        return feature.featureType === 'text';
                    });
                    expect(viewer.textLayer).not.toBe(null);
                    expect(viewer.textLayer.features().length).toBe(1);
                    // drawn annotations are above the text
                    expect(viewer.annotationLayer.zIndex()).toBeGreaterThan(viewer.textLayer.zIndex());
                    expect(text.length).toBe(1);
                    expect(features.length).toBe(2);
                    text = text[0];
                    expect(text.data().length).toBe(2);
                    expect(text.style.get('text')(text.data()[1], 1)).toBe('long first line\nshort');
                    expect(text.style.get('font')(text.data()[0], 0)).toBe('16px/20px sans-serif');
                    expect(text.style.get('font')(text.data()[1], 1)).toBe('24px/30px sans-serif');
                    expect(text.style('color')(text.data()[0], 0)).toBe('#000000');
                    expect(text.style('color')(text.data()[1], 1)).toBe('#ff0000');
                    expect(text.style.get('textOpacity')(text.data()[0], 0)).toBe(1);
                    expect(text.style.get('textOpacity')(text.data()[1], 1)).toBe(0.5);
                    expect(text.position()(text.data()[1], 1)).toEqual({x: center2.x, y: center2.y});
                    // redrawing replaces the feature
                    viewer.drawAnnotation(model, {fetch: false});
                });
                girderTest.waitForLoad();
                runs(function () {
                    expect(viewer.textLayer.features().length).toBe(1);
                });
            });

            it('draw a long comment', function () {
                var longModel;
                runs(function () {
                    longModel = new largeImageAnnotation.models.AnnotationModel({
                        _id: 'longtextannotation',
                        annotation: {
                            name: 'long text',
                            elements: [{
                                id: 'b00000000000000000000001',
                                type: 'text',
                                center: [100, 300, 0],
                                text: longText
                            }]
                        }
                    });
                    viewer.drawAnnotation(longModel, {fetch: false});
                });
                girderTest.waitForLoad();
                runs(function () {
                    var text = viewer._annotations[longModel.id].features[0];
                    expect(viewer.textLayer.features().length).toBe(2);
                    expect(text.featureType).toBe('text');
                    expect(text.style.get('text')(text.data()[0], 0)).toBe(longText);
                    // the text is drawn and can be found
                    viewer.viewer.draw();
                    var found = text.pointSearch({x: 100, y: 300});
                    expect(found.found.length).toBe(1);
                    expect(found.found[0].id).toBe('b00000000000000000000001');
                    viewer.removeAnnotation(longModel);
                    expect(viewer.textLayer.features().length).toBe(1);
                });
            });

            it('text opacity, highlighting, and hiding', function () {
                var text = viewer.textLayer.features()[0];

                function opacities() {
                    return text.data().map(function (d, i) {
                        return text.style.get('textOpacity')(d, i);
                    });
                }
                viewer.highlightAnnotation(model.id, 'a00000000000000000000001');
                expect(opacities()).toEqual([1, 0.5 * 0.33]);
                viewer.highlightAnnotation(model.id);
                expect(opacities()).toEqual([1, 0.5]);
                viewer.highlightAnnotation('otherannotation');
                expect(opacities()).toEqual([0.33, 0.5 * 0.33]);
                viewer.highlightAnnotation();
                expect(opacities()).toEqual([1, 0.5]);
                viewer.hideAnnotation(model.id, 'a00000000000000000000002');
                expect(opacities()).toEqual([1, 0]);
                viewer.hideAnnotation();
                expect(opacities()).toEqual([1, 0.5]);
                viewer.setGlobalAnnotationOpacity(0.5);
                expect(viewer.textLayer.opacity()).toBe(0.5);
                expect(opacities()).toEqual([1, 0.5]);
                viewer.setAnnotationOpacity(model.id, 0.25);
                expect(viewer.textLayer.opacity()).toBe(0.5);
                expect(opacities()).toEqual([0.5, 0.25]);
                viewer.setAnnotationOpacity(model.id);
                viewer.setGlobalAnnotationOpacity(1);
                expect(viewer.textLayer.opacity()).toBe(1);
                expect(opacities()).toEqual([1, 0.5]);
            });

            it('text mouse events', function () {
                var over = [], out = [], clicked = [], context = {};

                viewer.on('g:mouseOverAnnotation', function (element, annotation) {
                    expect(annotation).toBe(model.id);
                    over.push(element.id);
                }, context);
                viewer.on('g:mouseOutAnnotation', function (element) {
                    out.push(element.id);
                }, context);
                viewer.on('g:mouseClickAnnotation', function (element) {
                    clicked.push(element.id);
                }, context);

                function moveTo(x, y, dx, dy) {
                    var pt = viewer.viewer.gcsToDisplay({x: x, y: y});
                    pt = {x: pt.x + (dx || 0), y: pt.y + (dy || 0)};
                    interactor.simulateEvent('mousemove', {map: pt});
                    return pt;
                }
                interactor.simulateEvent('mousemove', {map: {x: 390, y: 10}});
                moveTo(center1.x, center1.y);
                expect(over).toEqual(['a00000000000000000000001']);
                moveTo(center1.x, center1.y, 0, 30);
                expect(out).toEqual(['a00000000000000000000001']);
                // each line of multiline text is checked separately.  The
                // second line is shorter than the first.
                moveTo(center2.x, center2.y, -70, -15);
                expect(over).toEqual(['a00000000000000000000001', 'a00000000000000000000002']);
                moveTo(center2.x, center2.y, -70, 15);
                expect(out).toEqual(['a00000000000000000000001', 'a00000000000000000000002']);
                var pt = moveTo(center2.x, center2.y, 0, 15);
                expect(over.length).toBe(3);
                interactor.simulateEvent('mousedown', {button: 'left', map: pt});
                interactor.simulateEvent('mouseup', {button: 'left', map: pt});
                expect(clicked).toEqual(['a00000000000000000000002']);
                // hidden text doesn't get events
                interactor.simulateEvent('mousemove', {map: {x: 390, y: 10}});
                viewer.hideAnnotation(model.id, 'a00000000000000000000002');
                moveTo(center2.x, center2.y, 0, 15);
                expect(over.length).toBe(3);
                viewer.hideAnnotation();
                interactor.simulateEvent('mousemove', {map: {x: 390, y: 10}});
                viewer.off(null, null, context);
            });

            it('remove text elements', function () {
                viewer.removeAnnotation(model);
                expect(viewer.textLayer.features().length).toBe(0);
                expect(viewer._annotations[model.id]).toBe(undefined);
            });
        });

        describe('global annotation opacity', function () {
            var opacity, opacityFunction;
            beforeEach(function () {
                opacity = null;
                opacityFunction = viewer.featureLayer.opacity;
                viewer.featureLayer.opacity = function (_opacity) {
                    opacity = _opacity;
                };
            });
            afterEach(function () {
                viewer.featureLayer.opacity = opacityFunction;
            });
            it('set global annotation opacity', function () {
                viewer.setGlobalAnnotationOpacity(0.5);
                expect(opacity).toBe(0.5);
            });
        });

        describe('global annotation fill opacity', function () {
            var annotation1;
            var element1 = '111111111111111111111111';

            it('generate test annotations', function () {
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'annotation1',
                        elements: [{
                            id: element1,
                            type: 'rectangle',
                            center: [200, 200, 0],
                            width: 400,
                            height: 400,
                            rotation: 0,
                            fillColor: '#000'
                        }]
                    })
                }).done(function (resp) {
                    annotation1 = new largeImageAnnotation.models.AnnotationModel({
                        _id: resp._id
                    });
                });
                waitsFor(function () {
                    return annotation1;
                }, 'annotations to be created');
                runs(function () {
                    viewer.drawAnnotation(annotation1);
                });
                girderTest.waitForLoad();
            });
            it('set global fill annotation opacity', function () {
                var polygonFeature = viewer.viewer.layers()[1].features()[2];
                expect(polygonFeature.style.get('fillOpacity')(null, 0, null, 0)).toBe(1);
                viewer.setGlobalAnnotationFillOpacity(0.5);
                expect(polygonFeature.style.get('fillOpacity')(null, 0, null, 0)).toBe(0.5);
                viewer.setGlobalAnnotationFillOpacity(1);
                expect(polygonFeature.style.get('fillOpacity')(null, 0, null, 0)).toBe(1);
            });
        });

        describe('highlight and hide annotations', function () {
            var annotation1, annotation2;
            var element11 = '111111111111111111111111';
            var element12 = '222222222222222222222222';
            var element21 = '333333333333333333333333';
            var element22 = '444444444444444444444444';

            it('generate test annotations', function () {
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'annotation1',
                        elements: [{
                            id: element11,
                            type: 'rectangle',
                            center: [200, 200, 0],
                            width: 400,
                            height: 400,
                            rotation: 0,
                            fillColor: 'rgba(0, 0, 0, 0.5)'
                        }, {
                            id: element12,
                            type: 'rectangle',
                            center: [300, 300, 0],
                            width: 100,
                            height: 100,
                            rotation: 0,
                            fillColor: 'rgba(0, 0, 0, 0.5)'
                        }]
                    })
                }).done(function (resp) {
                    annotation1 = new largeImageAnnotation.models.AnnotationModel({
                        _id: resp._id
                    });
                });
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'annotation2',
                        elements: [{
                            id: element21,
                            type: 'rectangle',
                            center: [200, 200, 0],
                            width: 400,
                            height: 400,
                            rotation: 0,
                            fillColor: 'rgba(0, 0, 0, 0.5)'
                        }, {
                            id: element22,
                            type: 'point',
                            center: [300, 300, 0],
                            fillColor: 'rgba(0, 0, 0, 0.5)'
                        }]
                    })
                }).done(function (resp) {
                    annotation2 = new largeImageAnnotation.models.AnnotationModel({
                        _id: resp._id
                    });
                });

                waitsFor(function () {
                    return annotation1 && annotation2;
                }, 'annotations to be created');
                runs(function () {
                    viewer.drawAnnotation(annotation1);
                    viewer.drawAnnotation(annotation2);
                });

                girderTest.waitForLoad();
            });

            function checkFeatureOpacity(annotationId, fillOpacity, strokeOpacity, filter) {
                filter = filter || _.constant(true);
                _.each(viewer._annotations[annotationId].features, function (feature, findex) {
                    var fillOpacityFunction = feature.style.get('fillOpacity');
                    var strokeOpacityFunction = feature.style.get('strokeOpacity');
                    var allData = feature.data();
                    _.each(_.filter(allData, filter), function (data, index) {
                        expect(fillOpacityFunction(allData, findex, data, index)).toBe(fillOpacity);
                        expect(strokeOpacityFunction(allData, findex, data, index)).toBe(strokeOpacity);
                    });
                });
            }

            it('highlight a full annotation', function () {
                viewer.highlightAnnotation(annotation1.id);

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5 * 0.33, 0.33);
            });

            it('highlight a single element', function () {
                viewer.highlightAnnotation(annotation2.id, element21);

                checkFeatureOpacity(annotation1.id, 0.5 * 0.33, 0.33);
                checkFeatureOpacity(annotation2.id, 0.5 * 0.33, 0.33, function (data) {
                    return data.id !== element21;
                });
                checkFeatureOpacity(annotation2.id, 0.5, 1, function (data) {
                    return data.id === element21;
                });
            });

            it('reset opacities', function () {
                viewer.highlightAnnotation();

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5, 1);
            });

            it('handles custom unselected opacity multiplier', function () {
                viewer.setUnselectedOpacityMultiplier(0.5);
                viewer.highlightAnnotation(annotation1.id);

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5 * 0.5, 0.5);

                viewer.highlightAnnotation();
                viewer.setUnselectedOpacityMultiplier();

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5, 1);
            });

            it('hide an element', function () {
                viewer.hideAnnotation(annotation2.id, element21);

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5, 1, function (data) {
                    return data.id !== element21;
                });
                checkFeatureOpacity(annotation2.id, 0, 0, function (data) {
                    return data.id === element21;
                });
            });

            it('reset opacities', function () {
                viewer.hideAnnotation();

                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5, 1);
            });

            it('set annotation opacity', function () {
                viewer.setGlobalAnnotationOpacity(0.5);
                viewer.setAnnotationOpacity(annotation1.id, 0.25);
                expect(viewer.featureLayer.opacity()).toBe(0.5);
                checkFeatureOpacity(annotation1.id, 0.25, 0.5);
                checkFeatureOpacity(annotation2.id, 0.5, 1);

                viewer.setAnnotationOpacity(annotation1.id, 1);
                expect(viewer.featureLayer.opacity()).toBe(1);
                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.25, 0.5);

                viewer.setAnnotationOpacity(annotation1.id);
                expect(viewer.featureLayer.opacity()).toBe(0.5);
                checkFeatureOpacity(annotation1.id, 0.5, 1);
                checkFeatureOpacity(annotation2.id, 0.5, 1);
            });
        });

        describe('heatmap opacity', function () {
            var heatmapAnnotation;

            it('generate a heatmap annotation', function () {
                girder.rest.restRequest({
                    url: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'heatmap',
                        elements: [{
                            type: 'heatmap',
                            points: [[100, 100, 0, 1], [200, 200, 0, 2]]
                        }]
                    })
                }).done(function (resp) {
                    heatmapAnnotation = new largeImageAnnotation.models.AnnotationModel({
                        _id: resp._id
                    });
                });
                waitsFor(function () {
                    return heatmapAnnotation;
                }, 'annotation to be created');
                runs(function () {
                    viewer.drawAnnotation(heatmapAnnotation);
                });
                waitsFor(function () {
                    return (viewer._annotations[heatmapAnnotation.id] || {features: []}).features.length;
                }, 'heatmap to be drawn');
            });

            it('set heatmap opacity', function () {
                var layer = viewer._annotations[heatmapAnnotation.id].features[0].layer();
                viewer.setGlobalAnnotationOpacity(0.5);
                expect(layer.opacity()).toBe(0.5);
                viewer.setAnnotationOpacity(heatmapAnnotation.id, 0.25);
                expect(layer.opacity()).toBe(0.25);
                viewer.setAnnotationOpacity(heatmapAnnotation.id);
                expect(layer.opacity()).toBe(0.5);
                viewer.removeAnnotation(heatmapAnnotation);
            });
        });
        describe('large annotations', function () {
            var annotations = [], count = 0;
            it('generate several sizes of annotations', function () {
                [0, 1, 2].forEach(function (i) {
                    var elements = new Array(Math.pow(10, i + 1)).fill(0).map(function (_elem, idx) {
                        return {
                            type: 'rectangle',
                            center: [0.2 + (idx % 100) * 0.1, 0.2 + (Math.floor(idx / 100)) * 0.1, 0],
                            width: 0.12 + (idx % 40) * 0.01,
                            height: 0.12 + (idx % 51) * 0.01,
                            rotation: 0,
                            fillColor: 'rgba(0, 0, 0, 0.5)'
                        };
                    });
                    girder.rest.restRequest({
                        url: 'annotation?itemId=' + itemId,
                        contentType: 'application/json',
                        processData: false,
                        type: 'POST',
                        data: JSON.stringify({
                            name: 'annotation' + i,
                            elements: elements
                        })
                    }).done(function (resp) {
                        annotations[i] = new largeImageAnnotation.models.AnnotationModel({
                            _id: resp._id,
                            maxDetails: 50,
                            minElements: 1,
                            maxCentroids: 500
                        });
                        count += 1;
                    });
                });
                waitsFor(function () {
                    return count === 3;
                }, 'annotations to be created');
                runs(function () {
                    annotations.forEach(function (annot) {
                        return viewer.drawAnnotation(annot);
                    });
                });
                girderTest.waitForLoad();
            });
            it('check that annotations are using centroids when appropriate', function () {
                runs(function () {
                    expect(annotations[0]._centroids).not.toBeDefined();
                    expect(annotations[1]._centroids).toBeDefined();
                    expect(annotations[1]._centroids.partial).not.toBeDefined();
                    expect(annotations[2]._centroids).toBeDefined();
                    expect(annotations[2]._centroids.partial).toBeDefined();
                    viewer.viewer.zoom(viewer.viewer.zoom() + 1);
                    expect(annotations[1]._lastZoom).toBeDefined();
                });
            });
            it('set opacity of an annotation using centroids', function () {
                var feature = _.find(viewer._annotations[annotations[1].id].features, function (feature) {
                    return feature._centroidFeature;
                });
                var fillOpacity = feature.style.get('fillOpacity');
                viewer.setGlobalAnnotationOpacity(0.5);
                var opacity = fillOpacity(feature.data()[0], 0);
                viewer.setAnnotationOpacity(annotations[1].id, 0.25);
                expect(fillOpacity(feature.data()[0], 0)).toBe(opacity * 0.5);
                viewer.setAnnotationOpacity(annotations[1].id);
                expect(fillOpacity(feature.data()[0], 0)).toBe(opacity);
            });
        });
        it('destroy the viewer', function () {
            viewer.destroy();
            expect($('.geojs-layer').length).toBe(0);
        });

        it('scale', function () {
            viewer = new GeojsViewer({
                el: $el,
                itemId: itemId,
                parentView: null,
                scale: {position: {bottom: 20, right: 10}, scale: 0.0005}
            });
            viewer.once('g:beforeFirstRender', function () {
                try {
                    window.geo.util.mockWebglRenderer();
                } catch (err) {
                    // if this is already mocked, do nothing.
                }
            });
            waitsFor(function () {
                return $('.geojs-layer.active').length >= 1 && viewer.scaleWidget;
            }, 'viewer and scale to load');
            runs(function () {
                expect(viewer.scaleWidget instanceof window.geo.gui.scaleWidget).toBe(true);
                viewer.destroy();
            });
        });
    });
});
