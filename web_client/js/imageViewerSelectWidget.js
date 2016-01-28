girder.wrap(girder.views.ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        if (this.model.get('largeImage')) {
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
        this.itemId = settings.imageModel.get('largeImage') === 'test'
            ? 'test'
            : settings.imageModel.id;
        this.currentViewer = null;
        this.viewers = [
            {
                name: 'openseadragon',
                label: 'OpenSeaDragon',
                type: girder.views.OpenseadragonImageViewerWidget
            },
            {
                name: 'openlayers',
                label: 'OpenLayers',
                type: girder.views.OpenlayersImageViewerWidget
            },
            {
                name: 'leaflet',
                label: 'Leaflet',
                type: girder.views.LeafletImageViewerWidget
            },
            {
                name: 'geojs',
                label: 'GeoJS',
                type: girder.views.GeojsImageViewerWidget
            },
            {
                name: 'slideatlas',
                label: 'SlideAtlas',
                type: girder.views.SlideAtlasImageViewerWidget
            }
        ];

        this.render();
    },

    render: function () {
        this.$el.html(girder.templates.imageViewerSelectWidget({
            viewers: this.viewers
        }));
        // TODO: choose an actual default, and update the option element to match
        this._selectViewer(this.viewers[0].name);
        return this;
    },

    _selectViewer: function (viewerName) {
        if (this.currentViewer) {
            this.currentViewer.destroy();
            this.currentViewer = null;
        }
        this.$('.image-viewer').toggleClass('hidden', true);

        var ViewerType = _.findWhere(this.viewers, {name: viewerName}).type;
        // GeoJs isn't always fully removing itself from its element when
        // destroyed, so use dedicated elements for each viewer for now
        var viewerEl = this.$('#' + ViewerType);
        viewerEl.toggleClass('hidden', false);
        this.currentViewer = new ViewerType({
            el: viewerEl,
            parentView: this,
            itemId: this.itemId
        });
    }

});
