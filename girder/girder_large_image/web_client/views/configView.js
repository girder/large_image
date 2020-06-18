import View from '@girder/core/views/View';

import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import { restRequest } from '@girder/core/rest';
import { AccessType } from '@girder/core/constants';
import events from '@girder/core/events';

import ConfigViewTemplate from '../templates/largeImageConfig.pug';
import '../stylesheets/largeImageConfig.styl';

/**
 * Show the default quota settings for users and collections.
 */
var ConfigView = View.extend({
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
                value: +this.$('.g-large-image-max-thumbnail-files').val()
            }, {
                key: 'large_image.max_small_image_size',
                value: +this.$('.g-large-image-max-small-image-size').val()
            }, {
                key: 'large_image.show_extra_public',
                value: this.$('.g-large-image-show-extra-public').val()
            }, {
                key: 'large_image.show_extra',
                value: this.$('.g-large-image-show-extra').val()
            }, {
                key: 'large_image.show_extra_admin',
                value: this.$('.g-large-image-show-extra-admin').val()
            }, {
                key: 'large_image.show_item_extra_public',
                value: this.$('.g-large-image-show-item-extra-public').val()
            }, {
                key: 'large_image.show_item_extra',
                value: this.$('.g-large-image-show-item-extra').val()
            }, {
                key: 'large_image.show_item_extra_admin',
                value: this.$('.g-large-image-show-item-extra-admin').val()
            }]);
        }
    },
    initialize: function () {
        ConfigView.getSettings((settings) => {
            this.settings = settings;
            this.render();
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate({
            settings: this.settings,
            viewers: ConfigView.viewers
        }));
        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Large image',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            }).render();
        }

        return this;
    },

    _saveSettings: function (settings) {
        /* Now save the settings */
        return restRequest({
            type: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(() => {
            /* Clear the settings that may have been loaded. */
            ConfigView.clearSettings();
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-large-image-error-message').text(
                resp.responseJSON.message
            );
        });
    }
}, {
    /* Class methods and objects */

    /* The list of viewers is added as a property to the select widget view so
     * that it is also available to the settings page. */
    viewers: [
        {
            name: 'geojs',
            label: 'GeoJS',
            type: 'geojs'
        }, {
            name: 'openseadragon',
            label: 'OpenSeaDragon',
            type: 'openseadragon'
        }, {
            name: 'openlayers',
            label: 'OpenLayers',
            type: 'openlayers'
        }, {
            name: 'leaflet',
            label: 'Leaflet',
            type: 'leaflet'
        }, {
            name: 'slideatlas',
            label: 'SlideAtlas',
            type: 'slideatlas'
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
        if (!ConfigView.settings) {
            restRequest({
                type: 'GET',
                url: 'large_image/settings'
            }).done((resp) => {
                resp.extraInfo = {};
                resp.extraItemInfo = {};
                let extraList = [{
                    access: null,
                    extraInfo: 'large_image.show_extra_public',
                    extraItemInfo: 'large_image.show_item_extra_public'
                }, {
                    access: AccessType.READ,
                    extraInfo: 'large_image.show_extra',
                    extraItemInfo: 'large_image.show_item_extra'
                }, {
                    access: AccessType.ADMIN,
                    extraInfo: 'large_image.show_extra_admin',
                    extraItemInfo: 'large_image.show_item_extra_admin'
                }];
                extraList.forEach((entry) => {
                    ['extraInfo', 'extraItemInfo'].forEach((key) => {
                        try {
                            resp[key][entry.access] = JSON.parse(resp[entry[key]]);
                        } catch (err) {
                        }
                    });
                });
                ConfigView.settings = resp;
                if (callback) {
                    callback(ConfigView.settings);
                }
            });
        } else {
            if (callback) {
                callback(ConfigView.settings);
            }
        }
    },

    /**
     * Clear the settings so that getSettings will refetch them.
     */
    clearSettings: function () {
        delete ConfigView.settings;
    }
});

export default ConfigView;
