import { apiRoot, restRequest } from 'girder/rest';
import View from 'girder/views/View';

var ImageViewerWidget = View.extend({
    initialize: function (settings) {
        this.itemId = settings.itemId;

        restRequest({
            type: 'GET',
            path: 'item/' + this.itemId + '/tiles'
        }).done((resp) => {
            this.levels = resp.levels;
            this.tileWidth = resp.tileWidth;
            this.tileHeight = resp.tileHeight;
            this.sizeX = resp.sizeX;
            this.sizeY = resp.sizeY;
            this.render();
        });
    },

    /**
     * Return a url for a specific tile.  This can also be used to generate a
     * template url if the level, x, and y parameters are template strings
     * rather than integers.
     *
     * @param {number|string} level: the tile level or a template string.
     * @param {number|string} x: the tile x position or a template string.
     * @param {number|string} y: the tile y position or a template string.
     * @param {object} [query]: optional query parameters to add to the url.
     */
    _getTileUrl: function (level, x, y, query) {
        var url = apiRoot + '/item/' + this.itemId + '/tiles/zxy/' +
            level + '/' + x + '/' + y;
        if (query) {
            url += '?' + $.param(query);
        }
        return url;
    },

    drawAnnotation: function () {
        throw new Error('Viewer does not support drawing annotations');
    },

    removeAnnotation: function () {
        throw new Error('Viewer does not support drawing annotations');
    }
});

export default ImageViewerWidget;
