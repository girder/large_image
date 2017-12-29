import GeojsImageViewerWidget from './geojs';

var MapnikGeojsImageViewerWidget = GeojsImageViewerWidget.extend({
    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.geo || !this.tileWidth || !this.tileHeight || this.deleted) {
            return this;
        }

        if (this.viewer) {
            // don't rerender the viewer
            return this;
        }

        var geo = window.geo; // this makes the style checker happy

        var params = {
            keepLower: false,
            attribution: null,
            url: this._getTileUrl('{z}', '{x}', '{y}', {'encoding': 'PNG'}),
            useCredentials: true
        };

        this.viewer = geo.map({
            node: this.el,
            zoom: 4,
            center: {x: -98.0, y: 39.5}
        });

        this.viewer.createLayer('osm');
        this.viewer.createLayer('osm', params);

        this.trigger('g:imageRendered', this);
        return this;
    }
});

export default MapnikGeojsImageViewerWidget;
