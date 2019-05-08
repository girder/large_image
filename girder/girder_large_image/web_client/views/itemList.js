import _ from 'underscore';

import { wrap } from '@girder/core/utilities/PluginUtils';
import { getApiRoot } from '@girder/core/rest';
import { getCurrentUser } from '@girder/core/auth';
import { AccessType } from '@girder/core/constants';
import ItemListWidget from '@girder/core/views/widgets/ItemListWidget';

import largeImageConfig from './configView';
import '../stylesheets/itemList.styl';

wrap(ItemListWidget, 'render', function (render) {
    /* Chrome limits the number of connections to a single domain, which means
     * that time-consuming requests for thumbnails can bind-up the web browser.
     * To avoid this, limit the maximum number of thumbnails that are requested
     * at a time.  At this time (2016-09-27), Chrome's limit is 6 connections;
     * to preserve some overhead, use a number a few lower than that. */
    var maxSimultaneous = 3;

    /**
     * When we might need to load another image, check how many are waiting or
     * currently being loaded, and ask an appropriate additional number to
     * load.
     *
     * @param {jquery element} parent parent under which the large_image
     *      thumbnails are located.
     */
    function _loadMoreImages(parent) {
        var loading = $('.large_image_thumbnail img.loading,.large_image_associated img.loading', parent).length;
        if (maxSimultaneous > loading) {
            $('.large_image_thumbnail img.waiting,.large_image_associated img.waiting', parent).slice(0, maxSimultaneous - loading).each(function () {
                var img = $(this);
                img.removeClass('waiting').addClass('loading');
                img.attr('src', img.attr('deferred-src'));
            });
        }
    }

    function addLargeImageDetails(item, container, parent, extraInfo) {
        var elem;
        elem = $('<div class="large_image_thumbnail"/>');
        container.append(elem);
        /* We store the desired src attribute in deferred-src until we actually
         * load the image. */
        elem.append($('<img class="waiting"/>').attr(
            'deferred-src', getApiRoot() + '/item/' +
                item.id + '/tiles/thumbnail?width=160&height=100'));
        var access = item.getAccessLevel();
        var extra = extraInfo[access] || extraInfo[AccessType.READ] || {};
        if (!getCurrentUser()) {
            extra = extraInfo[null] || {};
        }

        /* Set the maximum number of columns we have so that we can let css
         * perform alignment. */
        var numColumns = Math.max((extra.images || []).length + 1, parent.attr('large_image_columns') || 0);
        parent.attr('large_image_columns', numColumns);

        _.each(extra.images || [], function (imageName) {
            elem = $('<div class="large_image_thumbnail"/>');
            container.append(elem);
            elem.append($('<img class="waiting"/>').attr(
                'deferred-src', getApiRoot() + '/item/' + item.id +
                '/tiles/images/' + imageName + '?width=160&height=100'
            ));
            elem.attr('extra-image', imageName);
        });

        $('.large_image_thumbnail', container).each(function () {
            var elem = $(this);
            /* Handle images loading or failing. */
            $('img', elem).one('error', function () {
                $('img', elem).addClass('failed-to-load');
                $('img', elem).removeClass('loading waiting');
                elem.addClass('failed-to-load');
                _loadMoreImages(parent);
            });
            $('img', elem).one('load', function () {
                $('img', elem).addClass('loaded');
                $('img', elem).removeClass('loading waiting');
                _loadMoreImages(parent);
            });
        });
        _loadMoreImages(parent);
    }

    render.call(this);
    largeImageConfig.getSettings((settings) => {
        // we will want to also show metadata, so these entries might look like
        // {images: ['label', 'macro'],  meta: [{key: 'abc', label: 'ABC'}]}
        var extraInfo = {};
        if (settings['large_image.show_extra_public']) {
            try {
                extraInfo[null] = JSON.parse(settings['large_image.show_extra_public']);
            } catch (err) {
            }
        }
        if (settings['large_image.show_extra']) {
            try {
                extraInfo[AccessType.READ] = JSON.parse(settings['large_image.show_extra']);
            } catch (err) {
            }
        }
        if (settings['large_image.show_extra_admin']) {
            try {
                extraInfo[AccessType.ADMIN] = JSON.parse(settings['large_image.show_extra_admin']);
            } catch (err) {
            }
        }

        if (settings['large_image.show_thumbnails'] === false ||
                this.$('.large_image_container').length > 0) {
            return this;
        }
        var items = this.collection.toArray();
        var parent = this.$el;
        var hasAnyLargeImage = _.some(items, function (item) {
            return item.has('largeImage');
        });
        if (hasAnyLargeImage) {
            _.each(items, function (item) {
                var elem = $('<div class="large_image_container"/>');
                if (item.get('largeImage')) {
                    item.getAccessLevel(function () {
                        addLargeImageDetails(item, elem, parent, extraInfo);
                    });
                }
                $('a[g-item-cid="' + item.cid + '"]>i', parent).before(elem);
                _loadMoreImages(parent);
            });
        }
        return this;
    });
});
