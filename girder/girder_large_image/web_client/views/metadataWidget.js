import $ from 'jquery';
import {wrap} from '@girder/core/utilities/PluginUtils';
import MetadataWidget from '@girder/core/views/widgets/MetadataWidget';

import MetadatumWidget from './metadatumWidget';

import largeImageConfig from './configView';

wrap(MetadataWidget, 'initialize', function (initialize, settings) {
    const result = initialize.call(this, settings);
    if (this.item.get('_modelType') === 'item') {
        largeImageConfig.getConfigFile(this.item.get('folderId')).done((val) => {
            this._limetadata = (val || {}).itemMetadata;
            if (this._limetadata) {
                this.render();
            }
        });
    } else {
        this._limetadata = null;
    }
    return result;
});

wrap(MetadataWidget, 'render', function (render) {
    render.call(this);
    const menu = this.$el.find('ul.dropdown-menu.pull-right[role="menu"]');
    menu.remove('li.li-metadata-menuitem');
    if (this._limetadata) {
        let lastentry;
        this._limetadata.forEach((entry) => {
            if (!entry || !entry.value) {
                return;
            }
            const menuitem = $('<li class="li-metadata-menuitem" role="presentation"></li>');
            const link = $('<a class="li-add-metadata"></a>');
            link.attr('metadata-key', entry.value);
            link.text(entry.title || entry.value);
            menuitem.append(link);
            if (!lastentry) {
                menu.prepend(menuitem);
            } else {
                lastentry.after(menuitem);
            }
            lastentry = menuitem;
            // we should probably render based on a template
            // add an option to take away existing entries
        });
        if (lastentry) {
            this.events['click .li-add-metadata'] = (evt) => {
                const key = $(evt.target).attr('metadata-key');
                // if this key already exists, just go to editing it
                var EditWidget = this.modes.simple.editor;
                var value = ''; // default from config?

                var widget = new MetadatumWidget({
                    className: 'g-widget-metadata-row editing',
                    mode: 'simple',
                    key: key,
                    value: value,
                    item: this.item,
                    fieldName: this.fieldName,
                    apiPath: this.apiPath,
                    accessLevel: this.accessLevel,
                    parentView: this,
                    onMetadataEdited: this.onMetadataEdited,
                    onMetadataAdded: this.onMetadataAdded
                });
                widget.$el.appendTo(this.$('.g-widget-metadata-container'));

                new EditWidget({
                    item: this.item,
                    key: key,
                    value: value,
                    fieldName: this.fieldName,
                    apiPath: this.apiPath,
                    accessLevel: this.accessLevel,
                    newDatum: true,
                    parentView: widget,
                    onMetadataEdited: this.onMetadataEdited,
                    onMetadataAdded: this.onMetadataAdded
                })
                    .render()
                    .$el.appendTo(widget.$el);
            };
            this.delegateEvents();
        }
    }
    return this;
});

export default MetadataWidget;
