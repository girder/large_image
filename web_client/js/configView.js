/**
 * Show the default quota settings for users and collections.
 */
girder.views.largeImageConfig = girder.View.extend({
    events: {
        'submit #g-large-image-form': function (event) {
            event.preventDefault();
            this.$('#g-large-image-error-message').empty();
            this._saveSettings([{
                key: 'large_image.show_thumbnails',
                value: this.$('.g-large-image-thumbnails-show').prop('checked')
            }, {
                key: 'large_image.show_viewer',
                value: this.$('.g-large-image-viewer-show').prop('checked')
            }, {
                key: 'large_image.default_viewer',
                value: this.$('.g-large-image-default-viewer').val()
            }, {
                key: 'large_image.auto_set',
                value: this.$('.g-large-image-auto-set-on').prop('checked')
            }, {
                key: 'large_image.max_thumbnail_files',
                value: this.$('.g-large-image-max-thumbnail-files').val() - 0
            }]);
        }
    },
    initialize: function () {
        girder.views.largeImageConfig.getSettings(_.bind(
            function (settings) {
                this.settings = settings;
                this.render();
            }, this));
    },

    render: function () {
        this.$el.html(girder.templates.largeImageConfig({
            settings: this.settings,
            viewers: girder.views.largeImageConfig.viewers
        }));
        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Large image',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings) {
        /* Now save the settings */
        girder.restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function () {
            /* Clear the settings that may have been loaded. */
            girder.views.largeImageConfig.clearSettings();
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-large-image-error-message').text(
                resp.responseJSON.message
            );
        }, this));
    }
}, {
    /* Class methods and objects */

    /* The list of viewers is added as a property to the select widget view so
     * that it is also available to the settings page. */
    viewers: [
        {
            name: 'openseadragon',
            label: 'OpenSeaDragon',
            type: 'OpenseadragonImageViewerWidget'
        },
        {
            name: 'openlayers',
            label: 'OpenLayers',
            type: 'OpenlayersImageViewerWidget'
        },
        {
            name: 'leaflet',
            label: 'Leaflet',
            type: 'LeafletImageViewerWidget'
        },
        {
            name: 'geojs',
            label: 'GeoJS',
            type: 'GeojsImageViewerWidget'
        },
        {
            name: 'slideatlas',
            label: 'SlideAtlas',
            type: 'SlideAtlasImageViewerWidget'
        }
    ],

    /**
     * Get settings if we haven't yet done so.  Either way, call a callback
     * when we have settings.
     *
     * @param {function} callback a function to call after the settings are
     *      fetched.  If the settings are already present, this is called
     *      without any delay.
     */
    getSettings: function (callback) {
        if (!girder.views.largeImageConfig.settings) {
            girder.restRequest({
                type: 'GET',
                path: 'system/setting/large_image'
            }).done(function (resp) {
                girder.views.largeImageConfig.settings = resp;
                if (callback) {
                    callback(girder.views.largeImageConfig.settings);
                }
            });
        } else {
            if (callback) {
                callback(girder.views.largeImageConfig.settings);
            }
        }
    },

    /**
     * Clear the settings so that getSettings will refetch them.
     */
    clearSettings: function () {
        delete girder.views.largeImageConfig.settings;
    }
});

girder.router.route(
    'plugins/large_image/config', 'largeImageConfig', function () {
        girder.events.trigger('g:navigateTo',
                              girder.views.largeImageConfig);
    });

girder.exposePluginConfig('large_image', 'plugins/large_image/config');
