girder.views.ImageViewerWidget = girder.View.extend({
    initialize: function (settings) {
        this.itemId = settings.itemId;

        girder.restRequest({
            type: 'GET',
            path: 'item/' + this.itemId + '/tiles'
        }).done(_.bind(function (resp) {
            this.levels = resp.levels;
            this.tileWidth = resp.tileWidth;
            this.tileHeight = resp.tileHeight;
            this.sizeX = resp.sizeX;
            this.sizeY = resp.sizeY;
            this.render();
        }, this));
    },

    /**
     * Perform an annotation query on the item.
     * (See the GET /annotation endpoint)
     *
     * @param {object} [query]
     * @param {string} [query.userId]
     * @param {string} [query.text]
     * @param {string} [query.name]
     * @param {number} [query.limit=50]
     * @param {number} [query.offset=0]
     * @returns {promise} A promise that resolves with an array of annotations
     */
    annotations: function (query) {
        query = query || {};
        query.itemId = this.itemId;

        return girder.restRequest({
            type: 'GET',
            path: 'annotation',
            data: query
        });
    },

    _getTileUrl: function (level, x, y) {
        return '/api/v1/item/' + this.itemId + '/tiles/zxy/' +
            level + '/' + x + '/' + y;
    }

});
