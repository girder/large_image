import $ from 'jquery';

import { getApiRoot, restRequest } from '@girder/core/rest';
import View from '@girder/core/views/View';

var ImageViewerWidget = View.extend({
    initialize: function (settings) {
        this.itemId = settings.itemId;

        return restRequest({
            type: 'GET',
            url: 'item/' + this.itemId + '/tiles'
        }).done((resp) => {
            this.levels = resp.levels;
            this.tileWidth = resp.tileWidth;
            this.tileHeight = resp.tileHeight;
            this.sizeX = resp.sizeX;
            this.sizeY = resp.sizeY;
            this.metadata = resp;
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
        var url = getApiRoot() + '/item/' + this.itemId + '/tiles/zxy/' +
            level + '/' + x + '/' + y;
        if (query) {
            url += '?' + $.param(query);
        }
        return url;
    }
});

export default ImageViewerWidget;
