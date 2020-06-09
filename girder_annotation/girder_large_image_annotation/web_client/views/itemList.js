import $ from 'jquery';
import _ from 'underscore';

import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';
import ItemListWidget from '@girder/core/views/widgets/ItemListWidget';

import largeImageAnnotationConfig from './configView';

import '../stylesheets/itemList.styl';

wrap(ItemListWidget, 'render', function (render) {
    render.apply(this, _.rest(arguments));

    function addLargeImageAnnotationBadge(item, parent, numAnnotations) {
        const thumbnail = $('a[g-item-cid="' + item.cid + '"] .large_image_thumbnail', parent).first();

        let badge = thumbnail.find('.large_image_annotation_badge');
        if (badge.length === 0) {
            badge = $(`<div class="large_image_annotation_badge hidden"></div>`).appendTo(thumbnail);
        }
        // update badge
        badge
            .attr('title', `${numAnnotations} annotation${numAnnotations === 1 ? '' : 's'}`)
            .text(numAnnotations)
            .toggleClass('hidden', !numAnnotations);
    }

    largeImageAnnotationConfig.getSettings((settings) => {
        // don't render or already rendered
        if (settings['large_image.show_thumbnails'] === false || this.$('.large_image_annotation_badge').length > 0) {
            return;
        }
        const items = this.collection.toArray();
        const parent = this.$el;
        const hasAnyLargeImage = _.some(items, (item) => item.has('largeImage'));

        if (!hasAnyLargeImage) {
            return;
        }

        const needCounts = items.filter((item) => item._annotationCount === undefined && item.has('largeImage')).map((item) => {
            item._annotationCount = null; // pending
            return item.id;
        });
        let promise;
        if (!needCounts.length) {
            promise = $.Deferred().resolve({});
        } else {
            promise = restRequest({
                type: 'POST',
                url: 'annotation/counts',
                data: {
                    items: needCounts.join(',')
                },
                headers: { 'X-HTTP-Method-Override': 'GET' },
                error: null
            }).done((resp) => {
                Object.entries(resp).forEach(([id, count]) => {
                    if (this.collection.get(id)) {
                        this.collection.get(id)._annotationCount = count;
                    }
                });
            });
        }
        promise.then(() => {
            this.collection.forEach((item) => {
                if (item._annotationCount !== undefined) {
                    addLargeImageAnnotationBadge(item, parent, item._annotationCount);
                }
            });
            return null;
        });
    });
});

export default ItemListWidget;
