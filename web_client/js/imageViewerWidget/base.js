girder.views.ImageViewerWidget = girder.View.extend({
    initialize: function (settings) {
        this.itemId = settings.itemId;
        this.annotations = new girder.collections.AnnotationCollection();
        this.listenTo(this.annotations, 'add', this.addAnnotation);
        this.listenTo(this.annotations, 'remove', this.removeAnnotation);
        this.viewport = new girder.annotation.Viewport();

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
        var url = '/api/v1/item/' + this.itemId + '/tiles/zxy/' +
            level + '/' + x + '/' + y;
        if (query) {
          url += '?' + $.param(query);
        }
        return url;
    },

    /**
     * Draw an annotation and return a reference to it.  (Async)
     */
    addAnnotation: function (annotation) {
        //this.listenTo(annotation, 'change', this._renderAnnotation);
        annotation.fetch();
    },

    _renderAnnotation: function (annotation) {
        this.layer.load(annotation);
    },

    /**
     * Delete an annotation from the canvas.
     */
    removeAnnotation: function (annotation) {
        annotation.collection.reset();
        // this.stopListening(annotation);
    },

    /**
     * Create a new layer on top of the image.
     */
    createLayer: function () {
        var $el = $('<div class="g-li-full-screen"/>').appendTo(this.el);
        return new girder.annotation.Layer({
            viewport: this.viewport,
            el: $el.get(0)
        });
    },

    /**
     * Clean up an existing layer.
     */
    removeLayer: function (layer) {
        layer.$el.remove();
    }
});
