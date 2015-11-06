girder.views.OpenlayersImageViewerWidget = girder.views.ImageViewerWidget.extend({
    initialize: function (settings) {
        girder.views.ImageViewerWidget.prototype.initialize.call(this, settings);

        $('head').prepend(
            $('<link rel="stylesheet" href="http://openlayers.org/en/v3.10.1/css/ol.css">'));

        $.getScript(
            'http://openlayers.org/en/v3.10.1/build/ol.js',
            _.bind(function () {
                this.render();
            }, this)
        );
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.ol || !this.tileSize) {
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        this.viewer = new ol.Map({
            target: this.el,
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        tileSize: this.tileSize,
                        url: this._getTileUrl('{z}', '{x}', '{y}'),
                        maxZoom: this.maxZoom,
                        wrapX: false
                    }),
                    preload: 1
                })
            ],
            view: new ol.View({
                minZoom: 0,
                maxZoom: this.maxZoom,
                center: [0.0, 0.0],
                zoom: 0
                //projection: new ol.proj.Projection({
                //    code: 'rect',
                //    units: 'pixels',
                //    extent: [0, 0, this.sizeX, this.sizeY],
                //})
            }),
            logo: false
        });
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
        girder.views.ImageViewerWidget.prototype.destroy.call(this);
    }
});
