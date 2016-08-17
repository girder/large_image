girder.wrap(girder.views.MetadataWidget, 'render', function (render) {
    if (!this.item || !this.item.get('largeImage')) {
        return render.call(this);
    }

    girder.restRequest({
        path: 'item/' + this.item.id + '/tiles'
    }).then(_.bind(function (tiles) {

        this.$el.html(girder.templates.largeImage_metadataWidget({
            item: this.item,
            title: this.title,
            girder: girder,
            largeImage: tiles
        }));
    }, this));
    return this;
});
