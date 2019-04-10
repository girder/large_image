girderTest.importPlugin('large_image', 'large_image_annotation');
girderTest.startApp();

function waitForLargeImageViewer(viewerName) {
    waitsFor(function () {
        return !$('.image-viewer:empty').not('.hidden').length &&
               !$('.image-viewer.hidden').not(':empty').length &&
               $('.image-viewer').not('.hidden').not(':empty').length &&
               $('.image-viewer').not('.hidden').length === 1 &&
               $('.image-viewer').not('.hidden').attr('id') === viewerName;
    }, 'wait for ' + viewerName + ' to be visible');
}

describe('AnnotationListWidget', function () {
    var girder;
    var largeImage;
    var largeImageAnnotation;
    var item;
    var drawnAnnotations;

    beforeEach(function () {
        girder = window.girder;
        largeImage = girder.plugins.large_image;
        largeImageAnnotation = girder.plugins.large_image_annotation;
        drawnAnnotations = {};
    });

    describe('setup', function () {
        it('mock Webgl', function () {
            var GeojsViewer = largeImage.views.imageViewerWidget.geojs;
            girder.utilities.PluginUtils.wrap(GeojsViewer, 'initialize', function (initialize) {
                this.drawAnnotation = function (annotation) {
                    drawnAnnotations[annotation.id] = annotation;
                };
                this.removeAnnotation = function (annotation) {
                    delete drawnAnnotations[annotation.id];
                };

                this.once('g:beforeFirstRender', function () {
                    window.geo.util.mockWebglRenderer();
                });
                initialize.apply(this, _.rest(arguments));
            });
        });
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
        it('make collection and folder public', function () {
            var done;
            var collectionId;

            girder.rest.restRequest({
                url: 'collection'
            }).then(function (collections) {
                expect(collections.length).toBe(1);
                collectionId = collections[0]._id;
                return girder.rest.restRequest({
                    url: 'collection/' + collectionId + '/access',
                    method: 'PUT',
                    data: {public: true, access: '{}'}
                });
            }).then(function () {
                return girder.rest.restRequest({
                    url: 'folder',
                    data: {parentType: 'collection', parentId: collectionId}
                });
            }).then(function (folders) {
                expect(folders.length).toBe(1);
                return girder.rest.restRequest({
                    url: 'folder/' + folders[0]._id + '/access',
                    method: 'PUT',
                    data: {public: true, access: '{}'}
                });
            }).done(function (folder) {
                done = true;
            }).fail(function (err) {
                throw err;
            });

            waitsFor(function () {
                return done;
            }, 'requests to return');
        });
        it('upload test file', function () {
            girderTest.waitForLoad();
            runs(function () {
                $('.g-folder-list-link:first').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('${large_image}/../../test/test_files/yb10kx5k.png');
            });
            girderTest.waitForLoad();
        });
        it('navigate to item and make a large image', function () {
            runs(function () {
                $('a.g-item-list-link').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-large-image-create').length !== 0;
            });
            runs(function () {
                $('.g-large-image-create').click();
            });
            girderTest.waitForLoad();
            // wait for job to complete
            waitsFor(function () {
                return $('.g-item-image-viewer-select').length !== 0;
            }, 15000);
            girderTest.waitForLoad();
            runs(function () {
                expect($('.g-annotation-list-container *').length).toBe(0);
            });
        });
        it('get item model', function () {
            item = new girder.models.ItemModel();
            girder.rest.restRequest({url: 'item', data: {text: 'yb10kx5k.png'}}).done(function (resp) {
                item.set(resp[0]);
            });
            waitsFor(function () {
                return item.id;
            }, 'item to be returned');
        });
        it('create annotations', function () {
            var index;
            var annotation;
            var promises = [];
            var done;

            for (index = 1; index < 11; index += 1) {
                annotation = new largeImageAnnotation.models.AnnotationModel({
                    itemId: item.id,
                    annotation: {
                        name: 'annotation ' + index
                    }
                });
                promises.push(annotation.save());
            }

            $.when.apply($, promises).done(function () {
                done = true;
            });

            waitsFor(function () {
                return done;
            }, 'annotations to be created');
        });
        it('reload the item page', function () {
            girder.router.navigate('', {trigger: true});
            girderTest.waitForLoad();
            runs(function () {
                girder.router.navigate('item/' + item.id, {trigger: true});
            });
            girderTest.waitForLoad();
            waitForLargeImageViewer('geojs');
        });
    });

    describe('Test annotation list widget as admin', function () {
        it('select the openseadragon viewer', function () {
            runs(function () {
                $('.g-item-image-viewer-select select').val('openseadragon').trigger('change');
            });
            waitForLargeImageViewer('openseadragon');
        });
        it('select the geojs viewer', function () {
            runs(function () {
                $('.g-item-image-viewer-select select').val('geojs').trigger('change');
            });
            waitForLargeImageViewer('geojs');
        });
        it('check that all annotations are displayed', function () {
            var $el;
            waitsFor(function () {
                $el = $('.g-annotation-list .g-annotation-row');
                return $el.length > 0;
            }, 'annotations list to load');
            runs(function () {
                expect($el.length).toBe(10);
                $el.each(function () {
                    expect($(this).find('.g-annotation-name').text()).toMatch(/annotation [0-9]+/);
                });
            });
        });
        it('check download link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            var id = $el.data('annotationId');
            expect($el.find('.g-annotation-download').prop('href')).toMatch(new RegExp('.*annotation/' + id + '$'));
        });
        it('test delete link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            var id = $el.data('annotationId');
            expect($el.find('.g-annotation-delete').length).toBe(1);
            $el.find('.g-annotation-delete').click();

            girderTest.waitForDialog();
            runs(function () {
                $('#g-dialog-container #g-confirm-button').click();
            });

            waitsFor(function () {
                return $('.g-annotation-list .g-annotation-row[data-annotation-id="' + id + '"]').length === 0;
            }, 'annotation to be removed');
        });
        it('test permission editor link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            expect($el.find('.g-annotation-permissions').length).toBe(1);
            $el.find('.g-annotation-permissions').click();

            girderTest.waitForDialog();
            runs(function () {
                expect($('#g-dialog-container .modal-title').text()).toBe('Access control');
                $('#g-dialog-container .g-save-access-list').click();
            });
            girderTest.waitForLoad();
        });
    });
    describe('Test annotation list widget as user', function () {
        it('logout', girderTest.logout('log out admin'));
        it('login as a normal user', girderTest.createUser(
            'user', 'user@email.com', 'User', 'User', 'testpassword'));
        it('reload the item page', function () {
            runs(function () {
                girder.router.navigate('', {trigger: true});
            });
            girderTest.waitForLoad();
            runs(function () {
                girder.router.navigate('item/' + item.id, {trigger: true});
            });
            girderTest.waitForLoad();
            waitForLargeImageViewer('geojs');
        });
        it('check that all annotations are displayed', function () {
            var $el = $('.g-annotation-list .g-annotation-row');
            waitsFor(function () {
                return $el.length > 0;
            }, 'annotations list to load');
            runs(function () {
                expect($el.length).toBe(9);
                $el.each(function () {
                    expect($(this).find('.g-annotation-name').text()).toMatch(/annotation [0-9]+/);
                });
            });
        });
        it('check download link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            var id = $el.data('annotationId');
            expect($el.find('.g-annotation-download').prop('href')).toMatch(new RegExp('.*annotation/' + id + '$'));
        });
        it('test delete link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            expect($el.find('.g-annotation-delete').length).toBe(0);
        });
        it('test permission editor link', function () {
            var $el = $('.g-annotation-list .g-annotation-row:first');
            expect($el.find('.g-annotation-permissions').length).toBe(0);
        });
        it('check visibility checkbox tooltip', function () {
            expect($('.g-annotation-list .g-annotation-toggle input:first').prop('title')).toBe(
                'Show annotation');
        });
        it('toggle annotation visibility', function () {
            var id = $('.g-annotation-list .g-annotation-row:first').data('annotationId');
            $('.g-annotation-list .g-annotation-row:first').click();

            waitsFor(function () {
                return drawnAnnotations[id];
            }, 'annotation to draw');
            runs(function () {
                expect($('.g-annotation-list .g-annotation-toggle input:first').prop('checked')).toBe(true);
                $('.g-annotation-list .g-annotation-row:first').click();
                expect($('.g-annotation-list .g-annotation-toggle input:first').prop('checked')).toBe(false);
                expect(drawnAnnotations[id]).toBeUndefined();
            });
        });
        it('switch to a viewer that does not support annotations', function () {
            $('.g-item-image-viewer-select select').val('leaflet').trigger('change');
            waitForLargeImageViewer('leaflet');
            runs(function () {
                expect($('.g-annotation-list .g-annotation-toggle input:first').prop('disabled')).toBe(true);
            });
        });
    });
});
