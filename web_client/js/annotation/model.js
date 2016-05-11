girder.annotation.ElementModel = Backbone.Model.extend({
    sync: function () {}
});
girder.annotation.ElementCollection = Backbone.Collection.extend({
    model: girder.annotation.ElementModel
});

girder.models.AnnotationModel = girder.Model.extend({
    initialize: function () {
        this.elements = new girder.annotation.ElementCollection();

        // attach to internal events to keep the element collection
        // and elements in the attribute in sync
        this.listenTo(this, 'g:fetched', this._updateElements);
        this.listenTo(this, 'change:annotation', this._updateAttributes)

        // call the super-class method
        return girder.Model.prototype.initialize.apply(this, arguments);
    },

    resourceName: 'annotation',

    /**
     * Update the attached element collection according to the
     * attributes.
     */
    _updateElements: function () {
        var annotation = this.get('annotation') || {};
        var elements = annotation.elements || [];
        this.elements.reset(elements)
    },

    /**
     * Update the annotation attributes when the annotation collection
     * changes.
     */
    _updateAttributes: function () {
        var annotation = this.annotation();
        annotation.elements = this.elements.map(function (e) {
            return e.attributes;
        });
        this.annotation(annotation);
    },

    /**
     * Get or set the annotation attribute.  (Triggers
     * a change:annotation event on set.)
     */
    annotation: function (attr) {
        if (attr) {
            this.attributes.annotation = attr;
            this.trigger('change:annotation', this);
            return this;
        }
        return this.get('annotation') || {};
    }
});

girder.collections.AnnotationCollection = girder.Collection.extend({
    resourceName: 'annotation',
    model: girder.models.AnnotationModel
});

// extend the item model to include annotation support
girder.models.ItemModel = girder.models.ItemModel.extend({
    /**
     * Get annotations associated with the item.  Optionally,
     * additional query parameters can be provided.  Returns
     * a promise that resolves with an AnnotationCollection.
     */
    annotations: function (query) {
        query = query || {};
        query.itemId = this.id;
        return girder.restRequest({
            path: 'annotation',
            data: query
        }).then(function (data) {
            return new girder.collections.AnnotationCollection(data);
        });
    }
});
