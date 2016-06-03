/**
 * An object for managing an annotation layer rendered over a
 * "slippy map" visualization.  If no map is provided to the
 * constructor, then the annotations will be rendered to a
 * static canvas.
 *
 * @param {object} [settings={}]
 * @param {geo.map} [settings.map]
 * @param {object} [settings.size="auto"]
 */
girder.annotation.Layer = Backbone.View.extend({
    initialize: function (settings) {
        settings = settings || {};
        this.setMap(settings.map);
        this.size(settings.size || 'auto');
        this.annotations = {};
        var size = this.size();
        this.viewport = settings.viewport || new girder.annotation.Viewport(size);
    },

    /**
     * Load an annotation object into the layer.
     */
    load: function (annotation) {
        var settings = $.extend({
            el: d3.select(this.el).append('g').node(),
            viewport: this.viewport
        }, annotation);
        var view = new girder.annotation.Annotation(settings).render();
        this.annotations[view.id] = view;
        return view;
    },

    setMap: function (map) {
        this.unbindMap();

        if (map) {
            this._map = map;
            // @TODO
        } else {
            this._canvas = d3.select(this.el);
        }
        return this;
    },

    /**
     * Unbind events from the attached map object.
     */
    unbindMap: function () {
        if (this._map) {
            // @TODO
            this._map = null;
        }
        return this;
    },

    /**
     * Return a d3 selection containing the layer's canvas (an SVG element).
     */
    canvas: function () {
        return this._canvas;
    },

    /**
     * Get/set the canvas size.  Pass "auto" to set the size to
     * the size reported by jQuery width/height.
     */
    size: function (arg) {
        var parent, canvas = this.canvas();

        if (arg === 'auto') {
            parent = $(canvas.node()).parent();
            arg = {
                width: parent.width(),
                height: parent.height()
            };
        } else if (arg === undefined) {
            return {
                width: parseFloat(canvas.attr('width')),
                height: parseFloat(canvas.attr('height'))
            };
        }

        canvas.attr('width', arg.width)
            .attr('height', arg.height);
        return this;
    }

    // @TODO Handle navigation (pan, zoom, etc.)
});
