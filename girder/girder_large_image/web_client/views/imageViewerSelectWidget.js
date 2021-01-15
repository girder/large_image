import $ from 'jquery';
import _ from 'underscore';

import { wrap } from '@girder/core/utilities/PluginUtils';
import eventStream from '@girder/core/utilities/EventStream';
import ItemView from '@girder/core/views/body/ItemView';
import View from '@girder/core/views/View';

import largeImageConfig from './configView';
import * as viewers from './imageViewerWidget';

import imageViewerSelectWidget from '../templates/imageViewerSelectWidget.pug';
import '../stylesheets/imageViewerSelectWidget.styl';

wrap(ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {
        if (this.model.get('largeImage') &&
            this.model.get('largeImage').fileId) {
            this.imageViewerSelect = new ImageViewerSelectWidget({
                el: $('<div>', {class: 'g-item-image-viewer-select'})
                    .insertAfter(this.$('.g-item-info')),
                parentView: this,
                imageModel: this.model
            });
        }
    }, this);
    render.call(this);
});

var ImageViewerSelectWidget = View.extend({
    events: {
        'change select': function (event) {
            this._selectViewer(event.target.value);
        },
        'keyup select': function (event) {
            this._selectViewer(event.target.value);
        },
        'input #image-frame,#image-frame-number': function (event) {
            this.frameUpdate(event.target);
        }
    },

    initialize: function (settings) {
        this.itemId = settings.imageModel.id;
        this.model = settings.imageModel;
        this.currentViewer = null;
        largeImageConfig.getSettings(() => this.render());
    },

    render: function () {
        if (largeImageConfig.settings['large_image.show_viewer'] === false) {
            return this;
        }
        this.$el.html(imageViewerSelectWidget({
            viewers: largeImageConfig.viewers
        }));
        var name = largeImageConfig.settings['large_image.default_viewer'];
        if (_.findWhere(largeImageConfig.viewers, {name: name}) === undefined) {
            name = largeImageConfig.viewers[0].name;
        }
        this.$('select.form-control').val(name);
        this._selectViewer(name);
        return this;
    },

    _selectViewer: function (viewerName) {
        if (this.currentViewer && this.currentViewer.name === viewerName) {
            return;
        }
        if (this.currentViewer) {
            this.currentViewer.destroy();
            this.currentViewer = null;
        }
        // hide general image controls; individual viewers must enable them
        this.$('.image-controls>span').toggleClass('hidden', true);
        this._frameUpdate = null;
        this.$('.image-viewer').toggleClass('hidden', true);

        var viewer = _.findWhere(largeImageConfig.viewers,
            {name: viewerName});
        var ViewerType = viewers[viewer.type];
        // use dedicated elements for each viewer for now in case they aren't
        // fully cleaned up
        var viewerEl = this.$('#' + viewerName);
        viewerEl.toggleClass('hidden', false);
        this.currentViewer = new ViewerType({
            el: viewerEl,
            parentView: this,
            itemId: this.itemId,
            model: this.model,
            setFrames: _.bind(this.setFrames, this)
        });
        this.currentViewer.name = viewerName;
    },

    /**
     * If a viewer supports handling multi-frame images, call this as part of
     * this initial render to expose frame controls.
     *
     * @param {object} metadata A dictionary of metadata that might contain a
     *      list of frames.
     * @param {function} frameUpdate a function to call with the current frame
     *      number when it changes.  This is called with an initial frame
     *      number if the frame controls are available.  It is never called if
     *      there is only one frame.
     */
    setFrames: function (metadata, frameUpdate) {
        if (metadata.frames && metadata.frames.length > 1) {
            this._frameUpdate = frameUpdate;
            this.$('.image-controls-frame').removeClass('hidden');
            var ctrl = this.$('#image-frame'),
                ctrlnum = this.$('#image-frame-number');
            ctrl.attr('max', metadata.frames.length - 1);
            ctrlnum.attr('max', metadata.frames.length - 1);
            var frame = +ctrl.val();
            if (frame >= metadata.frames.length) {
                ctrl.val(0);
                frame = 0;
            }
            ctrlnum.val(frame);
            frameUpdate(frame);
        }
    },

    /**
     * Handle a change in a frame control.
     */
    frameUpdate: function (ctrl) {
        ctrl = $(ctrl);
        var frame = ctrl.val();
        this.$('#image-frame,#image-frame-number').val(frame);
        if (this._frameUpdate) {
            this._frameUpdate(frame);
        }
    }
});

wrap(ItemView, 'initialize', function (initialize) {
    this.listenTo(eventStream, 'g:event.large_image.finished_image_item', () => {
        this.model.unset('largeImage');
        this.model.fetch();
    });
    initialize.apply(this, _.rest(arguments));
});

export default ImageViewerSelectWidget;
