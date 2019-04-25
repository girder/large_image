/* globals girder, girderTest, describe, it, expect, waitsFor, runs */

girderTest.addScripts([
    '/static/built/plugins/jobs/plugin.min.js',
    '/static/built/plugins/worker/plugin.min.js',
    '/static/built/plugins/large_image/plugin.min.js'
]);

girderTest.startApp();

$(function () {
    describe('Test the large image plugin', function () {
        it('create the admin user', function () {
            girderTest.createUser(
                'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
        });
        it('change the large_image settings', function () {
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
                $('#g-large-image-form input.btn-primary').click();
            });
            waitsFor(function () {
                var resp = girder.rest.restRequest({
                    url: 'large_image/settings',
                    type: 'GET',
                    async: false
                });
                var settings = resp.responseJSON;
                return (settings['large_image.show_thumbnails'] === false &&
                        settings['large_image.show_viewer'] === false &&
                        settings['large_image.auto_set'] === false &&
                        settings['large_image.default_viewer'] === 'geojs' &&
                        settings['large_image.max_thumbnail_files'] === 5 &&
                        settings['large_image.max_small_image_size'] === 1024 &&
                        settings['large_image.show_extra_public'] === '{}' &&
                        settings['large_image.show_extra'] === '{}' &&
                        settings['large_image.show_extra_admin'] === '{"images": ["label", "macro"]}');
            }, 'large_image settings to change');
            girderTest.waitForLoad();
        });
    });
});
