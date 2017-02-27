import _ from 'underscore';

import ImageViewerWidget from './base';

var OpenseadragonImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        $.getScript(
            'https://openseadragon.github.io/openseadragon/openseadragon.min.js',
            () => this.render()
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.OpenSeadragon || !this.tileWidth || !this.tileHeight) {
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        var OpenSeadragon = window.OpenSeadragon; // this makes the style checker happy

        this.viewer = OpenSeadragon({ // jshint ignore:line
            element: this.el,
            prefixUrl: 'https://openseadragon.github.io/openseadragon/images/',
            minZoomImageRatio: 0.2,
            defaultZoomLevel: 0.3,
            showRotationControl: true,
            tileSources: {
                height: this.sizeY,
                width: this.sizeX,
                tileWidth: this.tileWidth,
                tileHeight: this.tileHeight,
                minLevel: 0,
                maxLevel: this.levels - 1,
                getTileUrl: _.bind(function (z, x, y) {
                    return this._getTileUrl(z, x, y, {edge: 'crop'});
                }, this),
                ajaxWithCredentials: true
            }
        });
        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.viewer.destroy();
            this.viewer = null;
        }
        if (window.OpenSeadragon) {
            delete window.OpenSeadragon;
        }
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default OpenseadragonImageViewerWidget;
