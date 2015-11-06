girder.views.SlideatlasImageViewerWidget = girder.views.ImageViewerWidget.extend({
    initialize: function (settings) {
        girder.views.ImageViewerWidget.prototype.initialize.call(this, settings);

        $.getScript(
            'slideatlas.js',
            _.bind(function () {
                this.render();
            }, this)
        );

    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.slideatlas || !this.tileSize) {
            return;
        }

        // TODO: if a viewer already exists, do we render again?

        this.viewer = new slideatlas();

        return this;
    },

    destroy: function () {
        if (this.viewer) {
            //this.viewer.destroy();
            this.viewer = null;
        }
        //if (window.slideatlas) {
        //    delete window.slideatlas;
        //}
        girder.views.ImageViewerWidget.prototype.destroy.call(this);
    }
});
