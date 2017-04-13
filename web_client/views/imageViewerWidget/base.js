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

    /**
     * Render an annotation model on the image.
     *
     * @param {AnnotationModel} annotation
     */
    drawAnnotation: function (/* annotation */) {
        throw new Error('Viewer does not support drawing annotations');
    },

    /**
     * Remove an annotation from the image.  This simply
     * finds a layer with the given id and removes it because
     * each annotation is contained in its own layer.  If
     * the annotation is not drawn, this is a noop.
     *
     * @param {AnnotationModel} annotation
     */
    removeAnnotation: function (/* annotation */) {
        throw new Error('Viewer does not support drawing annotations');
    },

    /**
     * Set the image interaction mode to region drawing mode.  This
     * method takes an optional `model` argument where the region will
     * be stored when created by the user.  In any case, this method
     * returns a promise that resolves to an array defining the region:
     *   [ left, top, width, height ]
     *
     * @param {Backbone.Model} [model] A model to set the region to
     * @returns {Promise}
     */
    drawRegion: function (/* model */) {
        throw new Error('Viewer does not support drawing annotations');
    },

    /**
     * Set the image interaction mode to draw the given type of annotation.
     *
     * @param {string} type An annotation type
     * @param {object} [options]
     * @param {boolean} [options.trigger=true]
     *      Trigger a global event after creating each annotation element.
     * @returns {Promise}
     *      Resolves to an array of generated annotation elements.
     */
    startDrawMode: function (/* type, options */) {
        throw new Error('Viewer does not support drawing annotations');
    }
});

export default ImageViewerWidget;
