import { staticRoot } from 'girder/rest';
import events from 'girder/events';

import ImageViewerWidget from './base';

var GeojsImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        this._layers = {};
        this.listenTo(events, 's:widgetDrawRegion', this.drawRegion);

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

        this._destroyViewer();
        var geo = window.geo; // this makes the style checker happy

        var w = this.sizeX, h = this.sizeY;
        var params = geo.util.pixelCoordinateParams(
            this.el, w, h, this.tileWidth, this.tileHeight);
        params.layer.useCredentials = true;
        params.layer.url = this._getTileUrl('{z}', '{x}', '{y}');
        this.viewer = geo.map(params.map);
        this.viewer.createLayer('osm', params.layer);

        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        this._destroyViewer();
        if (window.geo) {
            delete window.geo;
        }
        ImageViewerWidget.prototype.destroy.call(this);
    },

    _destroyViewer: function () {
        if (this.viewer) {
            this.viewer.exit();
            this.viewer = null;
        }
    },

    drawAnnotation: function (annotation) {
        var geojson = annotation.geojson();
        var layer = this.viewer.createLayer('feature', {
            features: ['point', 'line', 'polygon']
        });
        this._layers[annotation.id] = layer;
        window.geo.createFileReader('jsonReader', {layer})
            .read(geojson, () => this.viewer.draw());
    },

    removeAnnotation: function (annotation) {
        var layer = this._layers[annotation.id];
        if (layer) {
            this.viewer.deleteLayer(layer);
        }
    },

    drawRegion: function (model) {
        if (!this.viewer) {
            return;
        }
        var layer = this.viewer.createLayer('annotation');
        layer.geoOn(
            window.geo.event.annotation.state,
            (evt) => {
                var annotation = evt.annotation;
                var left, top, width, height, c;
                if (annotation.type() === 'rectangle') {
                    c = annotation.coordinates();
                    left = Math.round(c[0].x);
                    top = Math.round(c[1].y);
                    width = Math.round(c[2].x - left);
                    height = Math.round(c[3].y - top);
                    model.set('value', [left, top, width, height], {trigger: true});
                    window.setTimeout(() => this.viewer.deleteLayer(layer), 10);
                }
            }
        );
        layer.mode('rectangle');
    }

});

export default GeojsImageViewerWidget;
