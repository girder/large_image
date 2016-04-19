/* globals girderTest, describe, it, expect, waitsFor, runs */

girderTest.addCoveredScripts([
    '/static/built/plugins/large_image/templates.js',
    '/plugins/large_image/web_client/js/configView.js',
    '/plugins/large_image/web_client/js/fileList.js',
    '/plugins/large_image/web_client/js/imageViewerSelectWidget.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/base.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/geojs.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/leaflet.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/openlayers.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/openseadragon.js',
    '/plugins/large_image/web_client/js/imageViewerWidget/slideatlas.js',
    '/plugins/large_image/web_client/js/itemList.js'
]);

girderTest.importStylesheet(
    '/static/built/plugins/large_image/plugin.min.css'
);

girderTest.startApp();

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
            return $('input.g-plugin-switch[key="large_image"]').length > 0;
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
            $('#g-large-image-form input.btn-primary').click();
        });
        waitsFor(function () {
            var resp = girder.restRequest({
                path: 'system/setting/large_image',
                type: 'GET',
                async: false
            });
            var settings = resp.responseJSON;
            return (settings['large_image.show_thumbnails'] === false &&
                    settings['large_image.show_viewer'] === false &&
                    settings['large_image.default_viewer'] === 'geojs');
        }, 'large_image settings to change');
        girderTest.waitForLoad();
    });
});
