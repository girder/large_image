import OpenlayersImageViewerWidget from './openlayers';

var MapnikOpenlayersImageViewerWidget = OpenlayersImageViewerWidget.extend({
    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.ol || !this.tileWidth || !this.tileHeight || this.deleted) {
            return this;
        }

        if (this.viewer) {
            // don't rerender the viewer
            return this;
        }

        var ol = window.ol; // this makes the style checker happy

        this.viewer = new ol.Map({
            target: this.el,
            layers: [
                new ol.layer.Tile({
                    source: new ol.source.OSM()
                }),
                new ol.layer.Tile({
                    source: new ol.source.XYZ({
                        tileSize: [this.tileWidth, this.tileHeight],
                        url: this._getTileUrl('{z}', '{x}', '{y}', {'encoding': 'PNG'}),
                        crossOrigin: 'use-credentials',
                        maxZoom: this.levels,
                        wrapX: true
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
    }
});

export default MapnikOpenlayersImageViewerWidget;
