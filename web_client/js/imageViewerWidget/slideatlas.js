girder.views.SlideAtlasImageViewerWidget = girder.views.ImageViewerWidget.extend({
    initialize: function (settings) {
        girder.views.ImageViewerWidget.prototype.initialize.call(this, settings);

        if ( typeof(SA) == "undefined") {
            $('head').prepend(
                $('<link rel="stylesheet" href="https://beta.slide-atlas.org/webgl-viewer/static/css/sa.css">'));

            $.getScript(
                'https://beta.slide-atlas.org/webgl-viewer/static/sam.max.js',
                _.bind(function () {
                    this.render();
                }, this)
            );
            $.getScript(
                'https://beta.slide-atlas.org/webgl-viewer/static/sa.max.js',
                _.bind(function () {
                    this.render();
                }, this)
            );
        }
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
        this.$el.saViewer({
            zoomWidget: true,
            drawWidget: true,
            prefixUrl: 'https://beta.slide-atlas.org/webgl-viewer/static/',
            tileSource: {
                height: this.sizeY,
                width: this.sizeX,
                tileSize: this.tileWidth,
                minLevel: 0,
                maxLevel: this.levels - 1,
                getTileUrl: _.bind(this._getTileUrl, this),
                ajaxWithCredentials: true
            }});
        this.viewer = this.el.saViewer;
        this.girderGui = new SAM.GirderWidget(this.viewer.GetAnnotationLayer(), this.itemId);

        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.$el.saViewer('destroy');
            this.viewer = null;
        }
        girder.views.ImageViewerWidget.prototype.destroy.call(this);
    }
});
