/* globals beforeEach, afterEach, describe, it, expect, sinon, girder, Backbone */
/* eslint-disable camelcase, no-new */

girderTest.addScripts([
    '/clients/web/static/built/plugins/large_image/extra/sinon.js',
    '/clients/web/static/built/plugins/large_image/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    var itemId, annotationId, interactor;

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
                    path: 'annotation?itemId=' + itemId,
                    contentType: 'application/json',
                    processData: false,
                    type: 'POST',
                    data: JSON.stringify({
                        name: 'test annotation',
                        elements: [{
                            type: 'rectangle',
                            center: [10, 10, 0],
                            width: 2,
                            height: 2,
                            rotation: 0
                        }]
                    })
                }).then(function (resp) {
                    annotationId = resp._id;
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
                parentView: null
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
                viewer.drawAnnotation(annotation);
            });

            girderTest.waitForLoad();
            runs(function () {
                expect(viewer._layers[annotationId]).toBeDefined();
                // geojs makes to features for a polygon
                expect(viewer._layers[annotationId].features().length >= 1).toBe(true);

                layerSpy = sinon.spy(viewer._layers[annotationId], '_exit');
            });
        });

        it('removeAnnotation', function () {
            viewer.removeAnnotation(annotation);
            expect(viewer._layers).toEqual({});
            sinon.assert.calledOnce(layerSpy);
        });

        it('drawRegion', function () {
            var model = new Backbone.Model();
            runs(function () {
                viewer.drawRegion(model);
                interactor.simulateEvent('mousedown', {
                    button: 'left',
                    map: {
                        x: 10,
                        y: 10
                    }
                });
            });
            runs(function () {
                // Due to a bug in geojs, this raises an error, but it is required to simulate
                // a drag event on the map.
                try {
                    interactor.simulateEvent('mousemove', {
                        button: 'left',
                        map: {
                            x: 1500,
                            y: 1500
                        }
                    });
                } catch (e) {
                }
            });
            runs(function () {
                interactor.simulateEvent('mouseup', {
                    button: 'left',
                    map: {
                        x: 3000,
                        y: 3000
                    }
                });
            });
            waitsFor(function () {
                return !!model.get('value');
            });

            runs(function () {
                expect(model.get('value')).toEqual([0, 0, 15, 15]);
            });
        });

        it('destroy the viewer', function () {
            viewer.destroy();
            expect($('.geojs-layer').length).toBe(0);
            expect(window.geo).toBe(undefined);
        });
    });
});
