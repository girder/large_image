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
     * Get a url to download the annotation objects
     */
    downloadUrl: function () {
        var url = girder.Model.prototype.downloadUrl.apply(this, arguments);
        return url.replace(/\/download$/, '');
    },

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

// wrap the initialize method to append an annotations collection
girder.wrap(girder.models.ItemModel, 'initialize', function (initialize) {
    initialize.call(this, _.rest(arguments, 1));
    this.annotations = new girder.collections.AnnotationCollection();
    
    girder.restRequest({
        path: 'annotation',
        data: {itemId: this.id}
    }).then(_.bind(function (data) {
        this.annotations.set(data);
    }, this));
});
