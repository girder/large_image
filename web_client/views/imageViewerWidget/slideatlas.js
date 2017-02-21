import { staticRoot } from 'girder/rest';

import ImageViewerWidget from './base';

var SlideAtlasImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        ImageViewerWidget.prototype.initialize.call(this, settings);

        if (!$('head #large_image-slideatlas-css').length) {
            $('head').prepend(
                $('<link>', {
                    id: 'large_image-slideatlas-css',
                    rel: 'stylesheet',
                    href: staticRoot + '/built/plugins/large_image/extra/slideatlas/sa.css'
                })
            );
        }

        $.getScript(
            staticRoot + '/built/plugins/large_image/extra/slideatlas/sa-all.min.js',
            () => this.render()
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.SA || !this.tileWidth || !this.tileHeight) {
            return;
        }

        if (this.tileWidth !== this.tileHeight) {
            console.error('The SlideAtlas viewer only supports square tiles.');
            return;
        }

        // TODO: if a viewer already exists, do we render again?
        // SlideAtlas bundles its own version of jQuery, which should attach itself to "window.$" when it's sourced
        // The "this.$el" still uses the Girder version of jQuery, which will not have "saViewer" registered on it.
        window.$(this.el).saViewer({
            zoomWidget: true,
            drawWidget: true,
            prefixUrl: staticRoot + '/built/plugins/large_image/extra/slideatlas/img/',
            tileSource: {
                height: this.sizeY,
                width: this.sizeX,
                tileSize: this.tileWidth,
                minLevel: 0,
                maxLevel: this.levels - 1,
                getTileUrl: (level, x, y, z) => {
                    // Drop the "z" argument
                    return this._getTileUrl(level, x, y);
                }
            }
        });
        this.viewer = this.el.saViewer;

        return this;
    },

    destroy: function () {
        if (this.viewer) {
            window.$(this.el).saViewer('destroy');
            this.viewer = null;
        }
        if (window.SA) {
            delete window.SA;
        }
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default SlideAtlasImageViewerWidget;
