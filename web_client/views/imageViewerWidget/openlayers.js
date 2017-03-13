import ImageViewerWidget from './base';

var OpenlayersImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        if (!$('head #large_image-openlayers-css').length) {
            $('head').prepend(
                $('<link>', {
                    id: 'large_image-openlayers-css',
                    rel: 'stylesheet',
                    href: 'https://cdnjs.cloudflare.com/ajax/libs/ol3/3.15.0/ol.css'
                })
            );
        }

        $.getScript(
            'https://cdnjs.cloudflare.com/ajax/libs/ol3/3.15.0/ol.js',
            () => this.render()
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.ol || !this.tileWidth || !this.tileHeight) {
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        var ol = window.ol; // this makes the style checker happy

        this.viewer = new ol.Map({
            target: this.el,
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        tileSize: [this.tileWidth, this.tileHeight],
                        url: this._getTileUrl('{z}', '{x}', '{y}', {edge: 'white'}),
                        crossOrigin: 'use-credentials',
                        maxZoom: this.levels,
                        wrapX: false
                    }),
                    preload: 1
                })
            ],
            view: new ol.View({
                minZoom: 0,
                maxZoom: this.levels,
                center: [0.0, 0.0],
                zoom: 0
                // projection: new ol.proj.Projection({
                //     code: 'rect',
                //     units: 'pixels',
                //     extent: [0, 0, this.sizeX, this.sizeY],
                // })
            }),
            logo: false
        });
        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.viewer.setTarget(null);
            this.viewer = null;
        }
        if (window.ol) {
            delete window.ol;
        }
        // TODO: delete CSS
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default OpenlayersImageViewerWidget;
