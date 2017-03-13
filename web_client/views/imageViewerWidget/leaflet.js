import ImageViewerWidget from './base';

var LeafletImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        if (!$('head #large_image-leaflet-css').length) {
            $('head').prepend(
                $('<link>', {
                    id: 'large_image-leaflet-css',
                    rel: 'stylesheet',
                    href: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/leaflet.css'
                })
            );
        }

        $.getScript(
            'https://cdnjs.cloudflare.com/ajax/libs/leaflet/0.7.7/leaflet.js',
            () => this.render()
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.L || !this.tileWidth || !this.tileHeight) {
            return;
        }

        if (this.tileWidth !== this.tileHeight) {
            console.error('The Leaflet viewer only supports square tiles.');
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        var L = window.L; // this makes the style checker happy

        this.viewer = L.map(this.el, {
            center: [0.0, 0.0],  // initial position, must be set
            zoom: 0,  // initial zoom, must be set
            minZoom: 0,
            maxZoom: this.levels - 1,
            maxBounds: [
                [-90.0, -180.0],
                [90.0, 180.0]
            ],
            layers: [
                L.tileLayer(
                    this._getTileUrl('{z}', '{x}', '{y}', {edge: '#DDD'}), {
                        // in theory, tileSize: new L.Point(this.tileWidth,
                        // this.tileHeight) is supposed to support non-square
                        // tiles, but it doesn't work
                        tileSize: this.tileWidth,
                        continuousWorld: true
                    })
            ],
            attributionControl: false
        });
        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.viewer.remove();
            this.viewer = null;
        }
        if (window.L) {
            delete window.L;
        }
        // TODO: delete CSS
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default LeafletImageViewerWidget;
