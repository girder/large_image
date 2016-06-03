girder.wrap(girder.views.ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        if (this.model.get('largeImage') &&
            this.model.get('largeImage').fileId) {
            this.imageViewerSelect = new girder.views.ImageViewerSelectWidget({
                el: $('<div>', {class: 'g-item-image-viewer-select'})
                    .insertAfter(this.$('.g-item-info')),
                parentView: this,
                imageModel: this.model
            });
        }
    }, this);
    render.call(this);
});

girder.views.ImageViewerSelectWidget = girder.View.extend({
    events: {
        'change select': function (event) {
            this._selectViewer(event.target.value);
        },
        'keyup select': function (event) {
            this._selectViewer(event.target.value);
        }
    },

    initialize: function (settings) {
        this.itemId = settings.imageModel.id;
        this.model = settings.imageModel;
        this.currentViewer = null;
        girder.views.largeImageConfig.getSettings(
            _.bind(this.render, this));
    },

    render: function () {
        if (girder.views.largeImageConfig.settings['large_image.show_viewer'] === false) {
            return this;
        }
        this.$el.html(girder.templates.imageViewerSelectWidget({
            viewers: girder.views.largeImageConfig.viewers
        }));
        var name = girder.views.largeImageConfig.settings['large_image.default_viewer'];
        if (_.findWhere(girder.views.largeImageConfig.viewers, {name: name}) === undefined) {
            name = girder.views.largeImageConfig.viewers[0].name;
        }
        $('select.form-control', this.$el).val(name);
        this._selectViewer(name);
        return this;
    },

    _selectViewer: function (viewerName) {
        if (this.currentViewer) {
            this.currentViewer.destroy();
            this.currentViewer = null;
        }
        this.$('.image-viewer').toggleClass('hidden', true);

        var viewer = _.findWhere(girder.views.largeImageConfig.viewers,
                                 {name: viewerName});
        var ViewerType = girder.views[viewer.type];
        // use dedicated elements for each viewer for now in case they aren't
        // fully cleaned up
        var viewerEl = this.$('#' + viewerName);
        viewerEl.toggleClass('hidden', false);
        this.currentViewer = new ViewerType({
            el: viewerEl,
            parentView: this,
            itemId: this.itemId,
            model: this.model
        });
    }
});
