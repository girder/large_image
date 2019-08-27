import $ from 'jquery';
import _ from 'underscore';

import { restRequest } from '@girder/core/rest';
import events from '@girder/core/events';
import FileListWidget from '@girder/core/views/widgets/FileListWidget';
import { wrap } from '@girder/core/utilities/PluginUtils';
import { AccessType } from '@girder/core/constants';

import largeImageFileAction from '../templates/largeImage_fileAction.pug';
import '../stylesheets/fileList.styl';

wrap(FileListWidget, 'render', function (render) {
    render.call(this);
    if (!this.parentItem || !this.parentItem.get('_id')) {
        return this;
    }
    if (this.parentItem.getAccessLevel() < AccessType.WRITE) {
        return this;
    }
    var largeImage = this.parentItem.get('largeImage');
    var files = this.collection.toArray();
    _.each(files, (file) => {
        var actions = this.$('.g-file-list-link[cid="' + file.cid + '"]')
            .closest('.g-file-list-entry').children('.g-file-actions-container');
        if (!actions.length) {
            return;
        }
        var fileAction = largeImageFileAction({
            file: file, largeImage: largeImage});
        if (fileAction) {
            actions.prepend(fileAction);
            if (actions.has('.g-large-image-remove').length) {
                file.on('g:deleted', () => {
                    this.parentItem.unset('largeImage');
                    this.parentItem.fetch();
                });
            }
        }
    });
    this.$('.g-large-image-remove').on('click', () => {
        restRequest({
            type: 'DELETE',
            url: 'item/' + this.parentItem.id + '/tiles',
            error: null
        }).done(() => {
            this.parentItem.unset('largeImage');
            this.parentItem.fetch();
        });
    });
    this.$('.g-large-image-create').on('click', (e) => {
        var cid = $(e.currentTarget).parent().attr('file-cid');
        var fileId = this.collection.get(cid).id;
        restRequest({
            type: 'POST',
            url: 'item/' + this.parentItem.id + '/tiles',
            data: {fileId: fileId, notify: true},
            error: function (error) {
                if (error.status !== 0) {
                    events.trigger('g:alert', {
                        text: error.responseJSON.message,
                        type: 'info',
                        timeout: 5000,
                        icon: 'info'
                    });
                }
            }
        }).done(() => {
            this.parentItem.unset('largeImage');
            this.parentItem.fetch();
        });
    });
    return this;
});
