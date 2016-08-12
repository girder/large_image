/**
 * This model manages the viewport of the display and
 * provides d3 scale objects for coordinate transformations.
 */
girder.annotation.Viewport = Backbone.Model.extend({
    defaults: {
        left: 0,      // left-most pixel displayed
        top: 0,       // top-most pixel displayed
        scale: 1,     // scale factor image pixels / screen pixels
        width: 1,     // viewport width in screen pixels
        height: 1     // viewport height in screen pixels
    },

    initialize: function () {
        // convert from image pixel coordinates to canvas pixel coordinates
        this.x = d3.scale.linear();
        this.y = d3.scale.linear();

        // scale distances from canvas pixels to image pixels
        this.imageScale = d3.scale.linear();

        // scale distances from display pixels to canvas pixels
        // (this is always the identity function for the moment, but
        // exists for future optimization).
        this.pixelScale = d3.scale.linear();

        // initialize the scales
        this._setScale();
        this._setTranslate();

        // update the scales when the model changes
        this.listenTo(this, 'change:scale', this._setScale);
        this.listenTo(this, 'change', this._setTranslate);
    },

    /**
     * Return the current viewport bounds in image pixel coordinates.
     */
    viewport: function () {
        var left = this.get('left'),
            top_ = this.get('top');
        return {
            left: left,
            top: top_,
            right: left + this.get('scale') * this.get('width'),
            bottom: top_ + this.get('scale') * this.get('height')
        };
    },

    _setTranslate: function () {
        var vp = this.viewport();
        this.x.domain([vp.left, vp.right])
            .range([0, this.get('width')]);
        this.y.domain([vp.top, vp.bottom])
            .range([0, this.get('height')]);
        this.trigger('translate', this);
    },

    _setScale: function () {
        var scale = this.get('scale'),
            old = this.previous('scale') || scale,
            m = (old - scale) / 2;

        this.imageScale.range([0, this.get('scale')]);
        this.set({
            left: this.get('left') + m * this.get('width'),
            top: this.get('top') + m * this.get('height')
        });
        this.trigger('scale', this);
    },

    /**
     * Get or set the center of the viewport given in
     * image pixel coordinates.
     */
    center: function (center) {
        var vp, scale;
        if (!center) {
            vp = this.viewport();
            return {
                x: (vp.left + vp.right) / 2,
                y: (vp.top + vp.bottom) / 2
            };
        }
        scale = this.get('scale') / 2;
        this.set({
            left: center.x - this.get('width') * scale,
            top: center.y - this.get('height') * scale
        });
        return this;
    },

    /**
     * Get or set the "zoom level" defined as the binary
     * logarithm of the scale factor.
     *
     * Note: this is different from the zoom level as defined
     * by mapping applications which would vary from [0, max].
     * The zoom level for this method is translated by 2 * max
     * to [-max, 0].
     */
    zoom: function (zoom) {
        if (zoom === undefined) {
            return Math.log(this.get('scale')) / Math.log(2);
        }
        this.set('scale', Math.pow(2, zoom));
        return this;
    },

    sync: function () {}
});
