import _ from 'underscore';

import { wrap } from 'girder/utilities/PluginUtils';
import { apiRoot } from 'girder/rest';
import ItemListWidget from 'girder/views/widgets/ItemListWidget';

import largeImageConfig from './configView';

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
        var loading = $('.large_image_thumbnail img.loading', parent).length;
        if (maxSimultaneous > loading) {
            $('.large_image_thumbnail img.waiting', parent).slice(0, maxSimultaneous - loading).each(function () {
                var img = $(this);
                img.removeClass('waiting').addClass('loading');
                img.attr('src', img.attr('deferred-src'));
            });
        }
    }

    render.call(this);
    largeImageConfig.getSettings((settings) => {
        if (settings['large_image.show_thumbnails'] === false ||
                $('.large_image_thumbnail', this.$el).length > 0) {
            return this;
        }
        var items = this.collection.toArray();
        var parent = this.$el;
        var hasAnyLargeImage = _.some(items, function (item) {
            return item.has('largeImage');
        });
        if (hasAnyLargeImage) {
            $.each(items, function (idx, item) {
                var elem = $('<div class="large_image_thumbnail"/>');
                if (item.get('largeImage')) {
                    /* We store the desired src attribute in deferred-src until
                     * we actually load the image. */
                    elem.append($('<img class="waiting"/>').attr(
                            'deferred-src', apiRoot + '/item/' +
                            item.id + '/tiles/thumbnail?width=160&height=100'));
                    $('img', elem).one('error', function () {
                        $('img', elem).addClass('failed-to-load');
                        $('img', elem).removeClass('loading waiting');
                        _loadMoreImages(parent);
                    });
                    $('img', elem).one('load', function () {
                        $('img', elem).addClass('loaded');
                        $('img', elem).removeClass('loading waiting');
                        _loadMoreImages(parent);
                    });
                }
                $('a[g-item-cid="' + item.cid + '"]>i', parent).before(elem);
            });
            _loadMoreImages(parent);
        }
        return this;
    });
});
