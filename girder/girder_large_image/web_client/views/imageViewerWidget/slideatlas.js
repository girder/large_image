import $ from 'jquery';

import ImageViewerWidget from './base';

var SlideAtlasImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        let root = '/static/built';
        try {
            root = __webpack_public_path__ || root; // eslint-disable-line
        } catch (err) { }
        root = root.replace(/\/$/, '');
        if (!$('head #large_image-slideatlas-css').length) {
            $('head').prepend(
                $('<link>', {
                    id: 'large_image-slideatlas-css',
                    rel: 'stylesheet',
                    href: root + '/plugins/large_image/extra/slideatlas/sa.css'
                })
            );
        }

        $.when(
            ImageViewerWidget.prototype.initialize.call(this, settings),
            $.ajax({ // like $.getScript, but allow caching
                url: root + '/plugins/large_image/extra/slideatlas/sa-all.min.js',
                dataType: 'script',
                cache: true
            }))
            .done(() => this.render());
    },

    render: function () {
        var errmsg;
        // If script or metadata isn't loaded, then abort
        if (!window.SA || !this.tileWidth || !this.tileHeight || this.deleted) {
            return this;
        }

        if (this.viewer) {
            // don't rerender the viewer
            return this;
        }

        if (this.tileWidth !== this.tileHeight) {
            errmsg = 'The SlideAtlas viewer only supports square tiles.';
        }
        if (this.tileWidth > 256) {
            errmsg = 'The SlideAtlas viewer does not support tiles wider than 256 pixels.';
        }
        if (errmsg) {
            this.viewer = $('<div/>').text(errmsg);
            this.$el.append(this.viewer);
            console.error(errmsg);
            return this;
        }

        // TODO: if a viewer already exists, do we render again?
        // SlideAtlas bundles its own version of jQuery, which should attach itself to "window.$" when it's sourced
        // The "this.$el" still uses the Girder version of jQuery, which will not have "saViewer" registered on it.
        let root = '/static/built';
        try {
            root = __webpack_public_path__ || root; // eslint-disable-line
        } catch (err) { }
        root = root.replace(/\/$/, '');
        window.$(this.el).saViewer({
            zoomWidget: true,
            drawWidget: true,
            prefixUrl: root + '/plugins/large_image/extra/slideatlas/img/',
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

        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        if (this.viewer) {
            window.$(this.el).saViewer('destroy');
            this.viewer = null;
        }
        this.deleted = true;
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default SlideAtlasImageViewerWidget;
