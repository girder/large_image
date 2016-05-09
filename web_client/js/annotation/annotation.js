/**
 * A view that renders "annotation" objects as described at:
 *
 * https://github.com/DigitalSlideArchive/large_image/blob/master/docs/annotations.md
 */
girder.annotation.Annotation = Backbone.View.extend({
    initialize: function (settings) {
        this.viewport = settings.viewport;
        this.name = settings.name || '';
        this.id = settings.id || _.uniqueId('annotation-');
        this.description = settings.description || '';
        this.attributes = settings.attributes || {};
        this.collection = new girder.annotation.Collection(settings.elements || []);

        this.listenTo(this.collection, 'add', this.addOne);
        this.listenTo(this.collection, 'reset', this.render);
        this.listenTo(this.collection, 'remove', this.removeOne);
    },

    /**
     * Return a d3 selection of the element's parent.
     * Possibly cache this in the future.
     */
    canvas: function () {
        return d3.select(this.el);
    },

    render: function () {
        this.$el.attr('id', this.id);
        this.addAll();
        return this;
    },

    addOne: function (model) {
        var type = model.get('type'),
            elements = girder.annotation.elements,
            el;

        if (!_.has(elements, type)) {
            console.warn('Unknown annotation type "' + type + '"'); // eslint-disable-line no-console
            return;
        }

        el = this.canvas().append('g')
            .attr('id', model.id);

        new elements[type]({
            el: el.node(),
            model: model,
            viewport: this.viewport
        }).render();
        return this;
    },

    addAll: function () {
        this.canvas().selectAll('g').remove();
        this.collection.each(this.addOne, this);
        return this;
    },

    removeOne: function (model) {
        model.destroy();
        return this;
    }
});
