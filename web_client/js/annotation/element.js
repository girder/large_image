/**
 * Base class for all annotation element types.
 */
girder.annotation.Element = Backbone.View.extend({
    initialize: function (settings) {
        this.viewport = settings.viewport;

        // For conversion from annotation coordinates (raw image pixels) to
        // canvas coordinates.
        this.x = this.viewport.x;
        this.y = this.viewport.y;

        // For conversion from image coordinates to canvas coordinates.
        // This should be common multiplier of both the x and y scales
        // above.  This is used for converting axis independent lengths
        // such as circle radii.  This scale should be strictly linear
        // (0 |-> 0).
        this.imageScale = this.viewport.imageScale;

        // For conversion from display coordinates to canvas coordinates.
        // Specifically, this is used as a multiplier for stroke widths,
        // font sizes, and other properties that should not appear to change
        // when zooming.
        this.pixelScale = this.viewport.pixelScale;

        this.listenTo(this.viewport, 'change', this.render);
        this.listenTo(this.model, 'destroy', this.remove);
    },
    render: function () {
        throw new Error('Unimplemented base class method');
    },
    canvas: function () {
        return d3.select(this.el);
    },
    defs: function () {
        var svg = d3.select(this.$el.closest('svg').get(0));
        var defs = svg.select('defs');
        if (!defs.size()) {
            defs = svg.append('defs');
        }
        return defs;
    },

    select: function (arg) {
        arg = arg || '*';
        return this.canvas().selectAll(arg).data([this.model.attributes]);
    },
    line: function () {
        return d3.svg.line()
            .x(_.bind(function (d) { return this.x(d[0]); }, this))
            .y(_.bind(function (d) { return this.y(d[1]); }, this));
    },
    rotate: function (rad, center) {
        var deg = -rad * 180 / Math.PI;
        var x = this.x(center[0]);
        var y = this.y(center[1]);
        return {
            transform: 'rotate(' + deg + ' ' + x + ' ' + y + ')'
        };
    },

    /**
     * Color normalization method using tinycolor.  Returns an object
     * with separate color/alpha properties.
     */
    color: function (c) {
        c = tinycolor(c);
        return {
            color: c.toHexString(),
            alpha: c.getAlpha()
        };
    },

    /**
     * Return a CSS style object for stroked elements.
     * If passed the special string 'none', then the
     * stroke will be disabled.
     * @param {object|'none'} props Override standard property lookup
     */
    stroked: function (props) {
        if (props === 'none') {
            return {
                stroke: 'none'
            };
        }
        props = props || this.model.attributes;
        var c = this.color(props.lineColor);
        return {
            stroke: c.color,
            'stroke-opacity': c.alpha,
            'stroke-width': this.pixelScale(props.lineWidth !== undefined ? props.lineWidth : 1)
        };
    },

    /**
     * Return a CSS style object for filled elements.
     * If passed the special string 'none', then the
     * fill will be disabled.
     * @param {object|'none'} props Override standard property lookup
     */
    filled: function (props) {
        if (props === 'none') {
            return {
                fill: 'none'
            };
        }
        props = props || this.model.attributes;
        var c = this.color(props.fillColor);
        return {
            fill: c.color,
            'fill-opacity': c.alpha
        };
    }
});

girder.annotation.elements = {
    arrow: girder.annotation.Element.extend({
        render: function () {
            var select = this.select();
            var defs = this.defs();
            var points = this.model.get('points');

            if (!defs.select('#h-arrow-head').size()) {
                defs.append('marker')
                    .attr('id', 'h-arrow-head')
                    .attr('viewBox', '0 0 10 10')
                    .attr('refX', 1)
                    .attr('refY', 5)
                    .attr('markerHeight', 8)
                    .attr('markerWidth', 8)
                    .attr('orient', 'auto')
                    .append('path')
                    .attr('d', 'M 0 0 L 10 5 L 0 10 z')
            }

            select.enter().append('line');
            select.exit().remove();
            select.attr('x1', this.x(points[0][0]))
                .attr('x2', this.x(points[1][0]))
                .attr('y1', this.y(points[0][1]))
                .attr('y2', this.y(points[1][1]))
                .style(this.stroked())
                .attr('marker-end', 'url(#h-arrow-head)');
            return this; 
        }
    }),

    circle: girder.annotation.Element.extend({
        render: function () {
            var select = this.select();
            var center = this.model.get('center');
            var radius = this.model.get('radius');
            var stroke = this.model.has('lineWidth') ? undefined : 'none';

            select.enter().append('circle');
            select.exit().remove();
            select.attr('cx', this.x(center[0]))
                .attr('cy', this.y(center[1]))
                .attr('r', this.imageScale.invert(radius))
                .style(this.filled())
                .style(this.stroked(stroke));
            return this;
        }
    }),

    ellipse: girder.annotation.Element.extend({
        render: function () {
            // @TODO handle `normal`
            var select = this.select();
            var center = this.model.get('center');
            var width = this.model.get('width');
            var height = this.model.get('height');
            var rotation = this.model.get('rotation');
            var stroke = this.model.has('lineWidth') ? undefined : 'none';

            select.enter().append('ellipse');
            select.exit().remove();
            select.attr('cx', this.x(center[0]))
                .attr('cy', this.y(center[1]))
                .attr('rx', this.imageScale.invert(width / 2))
                .attr('ry', this.imageScale.invert(height / 2))
                .attr(this.rotate(rotation, center))
                .style(this.filled())
                .style(this.stroked(stroke));
            return this;
        }
    }),

    rectangle: girder.annotation.Element.extend({
        render: function () {
            // @TODO handle `normal`
            var select = this.select();
            var center = this.model.get('center');
            var width = this.model.get('width');
            var height = this.model.get('height');
            var rotation = this.model.get('rotation');
            var stroke = this.model.has('lineWidth') ? undefined : 'none';
            var x0 = center[0] - width / 2;
            var y0 = center[1] - height / 2;

            select.enter().append('rect');
            select.exit().remove();
            select.attr('x', this.x(x0))
                .attr('y', this.y(y0))
                .attr('width', this.imageScale.invert(width))
                .attr('height', this.imageScale.invert(height))
                .attr(this.rotate(rotation, center))
                .style(this.filled())
                .style(this.stroked(stroke));
            return this;
        }
    }),

    point: girder.annotation.Element.extend({
        render: function () {
            var select = this.select();
            var center = this.model.get('center');
            var stroke = this.model.has('lineWidth') ? undefined : 'none';

            // for the moment render a point as a fixed radius circle
            select.enter().append('circle');
            select.exit().remove();
            select.attr('cx', this.x(center[0]))
                .attr('cy', this.y(center[1]))
                .attr('r', this.pixelScale(8))
                .style(this.filled({fillColor: 'rgb(0,0,0)'}))
                .style(this.stroked(stroke));
            return this;
        }
    }),

    polyline: girder.annotation.Element.extend({
        render: function () {
            var select = this.select();
            var points = this.model.get('points');
            var closed = this.model.has('closed') ? this.model.get('closed') : false;
            var z = closed ? 'Z' : '';
            var fill = closed && this.model.has('fillColor') ? undefined : 'none';
            var line = this.line();

            select.enter().append('path');
            select.exit().remove();
            select.attr('d', line(points) + z)
                .style(this.filled(fill))
                .style(this.stroked());
            return this;
        }
    }),

    rectanglegrid: girder.annotation.Element.extend({
        render: function () {
            // @TODO handle `normal`
            var select;
            var center = this.model.get('center');
            var width = this.model.get('width');
            var height = this.model.get('height');
            var rotation = this.model.get('rotation');

            // number of grid lines
            var nx = this.model.get('widthSubdivisions') + 1;
            var ny = this.model.get('heightSubdivisions') + 1;

            // spacing between grid lines
            var dx = width / (nx - 1);
            var dy = height / (ny - 1);

            // get the corners
            var left = center[0] - width / 2;
            var right = center[0] + width / 2;
            var top = center[1] - height / 2;
            var bottom = center[1] + height / 2;

            // the canvas for the grid will be a group
            // element containing all elements
            var canvas = this.canvas().selectAll('g').data([0]);
            canvas.enter().append('g');

            var p, props;
            var fill = this.model.has('fillColor') ? this.model.attributes : 'none';

            function positionFunc(scale, offset, delta) {
                return function (i) {
                    return scale(i * delta + offset);
                };
            }

            // create a rect for fill
            select = canvas
                .selectAll('rect.h-grid-fill')
                .data([0]);

            select.enter()
                .append('rect')
                .attr('class', 'h-grid-fill')
                .style('stroke', 'none');

            select
                .attr('x', this.x(left))
                .attr('y', this.y(top))
                .attr('width', this.imageScale.invert(width))
                .attr('height', this.imageScale.invert(height))
                .style(this.filled(fill));

            // draw vertical lines
            select = canvas
                .selectAll('line.h-vertical')
                .data(d3.range(nx));

            select.enter()
                .append('line')
                .attr('class', 'h-vertical');

            select.exit()
                .remove();

            p = positionFunc(this.x, left, dx);
            select.attr('x1', p)
                .attr('x2', p)
                .attr('y1', this.y(top))
                .attr('y2', this.y(bottom));

            // draw horizontal lines
            select = canvas
                .selectAll('line.h-horizontal')
                .data(d3.range(ny));

            select.enter()
                .append('line')
                .attr('class', 'h-horizontal');

            select.exit()
                .remove();

            p = positionFunc(this.y, top, dy);
            select.attr('x1', this.x(left))
                .attr('x2', this.x(right))
                .attr('y1', p)
                .attr('y2', p);

            // set default line style
            props = _.defaults({}, this.model.attributes, {
                lineWidth: 1,
                lineColor: '#000000'
            });

            // set line style
            canvas.selectAll('line')
                .style(this.stroked(props));

            // apply the rotation
            canvas.attr(this.rotate(rotation, center));
        }
    })
};
