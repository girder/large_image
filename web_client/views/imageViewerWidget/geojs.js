import { staticRoot } from 'girder/rest';

import ImageViewerWidget from './base';

var GeojsImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        $.getScript(
            staticRoot + '/built/plugins/large_image/extra/geojs.js',
            () => this.render()
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.geo || !this.tileWidth || !this.tileHeight) {
            return;
        }

        var geo = window.geo; // this makes the style checker happy

        var w = this.sizeX, h = this.sizeY;
        var params = geo.util.pixelCoordinateParams(
            this.el, w, h, this.tileWidth, this.tileHeight);
        params.layer.useCredentials = true;
        params.layer.url = this._getTileUrl('{z}', '{x}', '{y}');
        this.viewer = geo.map(params.map);
        this.viewer.createLayer('osm', params.layer);

        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.viewer.exit();
            this.viewer = null;
        }
        if (window.geo) {
            delete window.geo;
        }
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default GeojsImageViewerWidget;
