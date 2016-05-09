girder.wrap(girder.views.FileListWidget, 'render', function (render) {
    render.call(this);
    if (!this.parentItem || !this.parentItem.get('_id')) {
        return this;
    }
    if (this.parentItem.getAccessLevel() < girder.AccessType.WRITE) {
        return this;
    }
    var largeImage = this.parentItem.get('largeImage');
    var files = this.collection.toArray();
    _.each(files, function (file) {
        var actions = $('.g-file-list-link[cid="' + file.cid + '"]',
                        this.$el).closest('.g-file-list-entry').children(
                        '.g-file-actions-container');
        if (!actions.length) {
            return;
        }
        var fileAction = girder.templates.largeImage_fileAction({
            file: file, largeImage: largeImage});
        if (fileAction) {
            actions.prepend(fileAction);
        }
    });
    $('.g-large-image-remove', this.$el).on('click', _.bind(function () {
        girder.restRequest({
            type: 'DELETE',
            path: 'item/' + this.parentItem.id + '/tiles',
            error: null
        }).done(_.bind(function () {
            this.parentItem.unset('largeImage');
            this.parentItem.fetch();
        }, this));
    }, this));
    $('.g-large-image-create', this.$el).on('click', _.bind(function (e) {
        var cid = $(e.currentTarget).parent().attr('file-cid');
        var fileId = this.collection.get(cid).id;
        girder.restRequest({
            type: 'POST',
            path: 'item/' + this.parentItem.id + '/tiles',
            data: {fileId: fileId},
            error: function (error) {
                if (error.status !== 0) {
                    girder.events.trigger('g:alert', {
                        text: error.responseJSON.message,
                        type: 'info',
                        timeout: 5000,
                        icon: 'info'
                    });
                }
            }
        }).done(_.bind(function () {
            this.parentItem.unset('largeImage');
            this.parentItem.fetch();
        }, this));
    }, this));
    return this;
});
