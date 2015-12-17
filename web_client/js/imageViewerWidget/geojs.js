girder.views.GeojsImageViewerWidget = girder.views.ImageViewerWidget.extend({
    initialize: function (settings) {
        girder.views.ImageViewerWidget.prototype.initialize.call(this, settings);

        $.getScript(
            girder.staticRoot + '/built/plugins/large_image/geo.min.js',
            _.bind(function () {
                this.render();
            }, this)
        );

    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.geo || !this.tileSize) {
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        this.viewer = geo.map({
            node: this.el
        });
        this.viewer.createLayer('osm', {
            useCredentials: true,
            // TODO: syntax has changed in the latest GeoJS version
            //tileUrl: this._getTileUrl('{z}', '{x}', '{y}')
            tileUrl: this._getTileUrl('<zoom>', '<x>', '<y>')
        });

        return this;
    },

    destroy: function () {
        if (this.viewer) {
            //this.viewer.destroy();
            this.viewer = null;
        }
        //if (window.geo) {
        //    delete window.geo;
        //}
        girder.views.ImageViewerWidget.prototype.destroy.call(this);
    }
});
