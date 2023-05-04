/* globals girder, girderTest, describe, it, expect, waitsFor, runs, $ */

girderTest.importPlugin('jobs', 'worker', 'large_image');

girderTest.startApp();

describe('Test the large image plugin', function () {
    it('create the admin user', function () {
        girderTest.createUser(
            'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
    });
    it('change the large_image settings', function () {
        var settings;

        waitsFor(function () {
            return $('a.g-nav-link[g-target="admin"]').length > 0;
        }, 'admin console link to load');
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').click();
        });
        waitsFor(function () {
            return $('.g-plugins-config').length > 0;
        }, 'the admin console to load');
        runs(function () {
            $('.g-plugins-config').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-plugin-config-link').length > 0;
        }, 'the plugins page to load');
        runs(function () {
            expect($('.g-plugin-config-link[g-route="plugins/large_image/config"]').length > 0);
            $('.g-plugin-config-link[g-route="plugins/large_image/config"]').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('#g-large-image-form input').length > 0;
        }, 'resource list setting to be shown');
        runs(function () {
            $('.g-large-image-thumbnails-hide').trigger('click');
            $('.g-large-image-viewer-hide').trigger('click');
            $('.g-large-image-default-viewer').val('geojs');
            $('.g-large-image-auto-set-off').trigger('click');
            $('.g-large-image-max-thumbnail-files').val('5');
            $('.g-large-image-max-small-image-size').val('1024');
            $('.g-large-image-show-extra-public').val('{}');
            $('.g-large-image-show-extra').val('{}');
            $('.g-large-image-show-extra-admin').val('{"images": ["label", "macro"]}');
            $('.g-large-image-show-item-extra-public').val('{}');
            $('.g-large-image-show-item-extra').val('{}');
            $('.g-large-image-show-item-extra-admin').val('{"metadata": ["tile", "internal"], "images": ["label", "macro", "*"]}');
            $('.g-large-image-icc-correction-off').trigger('click');
            $('#g-large-image-form input.btn-primary').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            var resp = girder.rest.restRequest({
                url: 'large_image/settings',
                type: 'GET',
                async: false
            });
            settings = resp.responseJSON;
            return settings['large_image.max_thumbnail_files'] === 5;
        }, 'large_image settings to change');
        runs(function () {
            expect(settings['large_image.show_thumbnails']).toBe(false);
            expect(settings['large_image.show_viewer']).toBe(false);
            expect(settings['large_image.auto_set']).toBe(false);
            expect(settings['large_image.default_viewer']).toBe('geojs');
            expect(settings['large_image.max_thumbnail_files']).toBe(5);
            expect(settings['large_image.max_small_image_size']).toBe(1024);
            expect(settings['large_image.show_extra_public']).toBe('{}');
            expect(settings['large_image.show_extra']).toBe('{}');
            expect(settings['large_image.show_extra_admin']).toBe('{"images": ["label", "macro"]}');
            expect(settings['large_image.show_item_extra_public']).toBe('{}');
            expect(settings['large_image.show_item_extra']).toBe('{}');
            expect(JSON.parse(settings['large_image.show_item_extra_admin'])).toEqual({metadata: ['tile', 'internal'], images: ['label', 'macro', '*']});
            expect(settings['large_image.icc_correction']).toBe(false);
        });
        girderTest.waitForLoad();
        runs(function () {
            $('.g-large-image-icc-correction').trigger('click');
            $('#g-large-image-form input.btn-primary').click();
        });
        girderTest.waitForLoad();
    });
    it('change the config folder', function () {
        runs(function () {
            $('.g-open-browser').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            $('#g-root-selector').val($('#g-root-selector')[0].options[1].value).trigger('change');
        });
        waitsFor(function () {
            return $('.g-folder-list-link').length >= 2;
        });
        runs(function () {
            $('.g-folder-list-link').click();
        });
        waitsFor(function () {
            return $('#g-selected-model').val() !== '';
        });
        runs(function () {
            $('.g-submit-button').click();
        });
        girderTest.waitForLoad();
    });
});
