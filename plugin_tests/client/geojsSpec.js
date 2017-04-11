/* globals beforeEach, afterEach, describe, it, expect, sinon */
/* eslint-disable camelcase, no-new */

girderTest.addScripts([
    '/clients/web/static/built/plugins/large_image/extra/sinon.js',
    '/clients/web/static/built/plugins/large_image/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    var itemId;

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
    });

    describe('Geojs viewer', function () {
        var girder, large_image, $el, GeojsViewer, viewer, geo, annotation, layer;

        beforeEach(function () {
            geo = window.geo;
            girder = window.girder;
            large_image = girder.plugins.large_image;
            GeojsViewer = large_image.views.imageViewerWidget.geojs;
            $el = $('<div/>').appendTo('body')
                .css({
                    width: '400px',
                    height: '300px'
                });
        });

        afterEach(function () {
            $el.remove();
        });

        it('script is loaded', function () {
            viewer = new GeojsViewer({
                el: $el,
                itemId: itemId,
                parentView: null
            });
            waitsFor(function () {
                return $('.geojs-layer.active').length >= 1;
            }, 'viewer to load');
            runs(function () {
                expect(viewer.viewer.size()).toEqual({
                    width: 400,
                    height: 300
                });
            });
        });

        it('drawAnnotation', function () {
            // doesn't work without webgl so mock some methods
            layer = {
                _exit: sinon.stub()
            };
            sinon.stub(viewer.viewer, 'createLayer').returns(layer);
            sinon.spy(viewer.viewer, 'deleteLayer');
            sinon.stub(geo, 'createFileReader').returns({
                read: sinon.stub().callsArg(1)
            });

            annotation = new large_image.models.AnnotationModel({
                _id: 'a',
                annotation: {
                    name: 'test annotation',
                    elements: [{
                        type: 'Rectangle',
                        id: 'aaa',
                        center: [10, 10, 0],
                        width: 2,
                        height: 2,
                        rotation: 0
                    }]
                }
            });
            viewer.drawAnnotation(annotation);
            expect(viewer._layers[annotation.id]).toBe(layer);
        });

        it('removeAnnotation', function () {
            viewer.removeAnnotation(annotation);
            sinon.assert.calledOnce(viewer.viewer.deleteLayer);
        });

        it('destroy the viewer', function () {
            viewer.destroy();
            expect($('.geojs-layer').length).toBe(0);
            expect(window.geo).toBe(undefined);
        });
    });
});
