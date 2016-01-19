$(function () {
    girderTest.addCoveredScripts([
        '/static/built/plugins/large_image/templates.js',
        '/plugins/large_image/web_client/js/imageViewerSelectWidget.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/base.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/geojs.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/leaflet.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/openlayers.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/openseadragon.js',
        '/plugins/large_image/web_client/js/imageViewerWidget/slideatlas.js'
    ]);

    girderTest.importStylesheet(
        '/static/built/plugins/large_image/plugin.min.css'
    );

    girder.events.trigger('g:appload.before');
    var app = new girder.App({
        el: 'body',
        parentView: null
    });
    girder.events.trigger('g:appload.after');

    describe('Example test block', function () {
        it('Example test case', function () {
            expect('a').toBe('a');
        });
    });
});
