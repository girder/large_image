girder.annotation.Demo = Backbone.View.extend({
    events: {
        'change .h-annotation-file': 'open',
        'mousedown .h-visualization-body': '_startPan',
        'click .h-zoom-in ': '_zoomIn',
        'click .h-zoom-out': '_zoomOut'
    },
    initialize: function () {
        this._x0 = 0;
        this._y0 = 0;
        this._x = 0;
        this._y = 0;

        this.step = 0;
        this.animating = false;
        $.ajax(girder.staticRoot + '/built/plugins/large_image/extra/annotation_demo.json')
            .then(_.bind(function (spec) {
                this.spec = spec;
                this.render();
            }, this));
    },
    render: function () {
        this.animating = false;
        this.$el.html(girder.templates.annotationDemo());
        this.$('.h-visualization-body').css('height', '100%');
        var el = this.$('.h-visualization-body').empty().get(0);
        var canvas = d3.select(el).append('svg');
        this.layer = new girder.annotation.Layer({
            el: canvas.node()
        });
        if (this.spec) {
            this.layer.load(this.spec);
        }
        return this;
    },
    open: function () {
        var file = this.$('.h-annotation-file').get(0).files[0];

        if (!file || !file.type === 'application/json') {
            return;
        }

        var reader = new FileReader();

        reader.onload = _.bind(function (e) {
            var content = e.target.result;
            this.spec = JSON.parse(content);
            this.render();
        }, this);

        reader.readAsText(file);
    },

    _step: function () {
        if (!this.animating) {
            return;
        }
    },

    _startPan: function (evt) {
        if (!this.layer) {
            return;
        }
        this._x0 = this.layer.viewport.get('left');
        this._y0 = this.layer.viewport.get('top');
        this._x = evt.screenX;
        this._y = evt.screenY;
        $(document).on('mousemove.annotation', _.bind(this._pan, this));
        $(document).on('mouseup.annotation', _.bind(this._endPan, this));
    },

    _pan: function (evt) {
        var x = this._x - evt.screenX;
        var y = this._y - evt.screenY;
        var scale = this.layer.viewport.get('scale');
        this.layer.viewport.set({
            left: this._x0 + x * scale,
            top: this._y0 + y * scale
        });
    },

    _endPan: function () {
        $(document).off('.annotation');
    },

    _zoomIn: function () {
        if (!this.layer) {
            return;
        }
        var scale = this.layer.viewport.get('scale') / 2;
        this.layer.viewport.set('scale', scale);
    },

    _zoomOut: function () {
        if (!this.layer) {
            return;
        }
        var scale = this.layer.viewport.get('scale') * 2;
        this.layer.viewport.set('scale', scale);
    }
});
