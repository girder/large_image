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

    _getTileUrl: function (level, x, y) {
        return '/api/v1/item/' + this.itemId + '/tiles/zxy/' +
            level + '/' + x + '/' + y;
    }

});
