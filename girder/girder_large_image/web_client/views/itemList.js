import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import { wrap } from '@girder/core/utilities/PluginUtils';
import { getApiRoot, restRequest } from '@girder/core/rest';
import { getCurrentUser } from '@girder/core/auth';
import { AccessType } from '@girder/core/constants';
import { formatSize, parseQueryString, splitRoute } from '@girder/core/misc';
import router from '@girder/core/router';
import ItemListWidget from '@girder/core/views/widgets/ItemListWidget';

import largeImageConfig from './configView';
import '../stylesheets/itemList.styl';
import ItemListTemplate from '../templates/itemList.pug';

wrap(ItemListWidget, 'initialize', function (initialize, settings) {
    let result = initialize.call(this, settings);
    delete this._hasAnyLargeImage;

    if (!settings.folderId) {
        this._liconfig = {};
    }
    restRequest({
        url: `folder/${settings.folderId}/yaml_config/.large_image_config.yaml`
    }).done((val) => {
        if (!_.isEqual(val, this._liconfig)) {
            delete this._lastSort;
            this._liconfig = val || {};
            const curRoute = Backbone.history.fragment;
            const routeParts = splitRoute(curRoute);
            const query = parseQueryString(routeParts.name);
            if (query.sort) {
                this._lastSort = query.sort.split(',').map((chunk) => {
                    const parts = chunk.split(':');
                    return {
                        type: parts[0],
                        value: parts[1],
                        dir: parts[2]
                    };
                });
                this._setSort();
            }
            this.render();
        }
    });
    this.events['click .li-item-list-header.sortable'] = (evt) => sortColumn.call(this, evt);
    this.delegateEvents();
    return result;
});

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
        elem.attr('g-item-cid', item.cid);
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
                '/tiles/images/' + imageName + '?width=160&height=100&_=' + item.get('updated')
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

    this._confList = () => {
        return this._liconfig ? (this.$el.closest('.modal-dialog').length ? this._liconfig.itemListDialog : this._liconfig.itemList) : undefined;
    };

    this._setSort = () => {
        this.collection.offset = 0;
        this.collection.comparator = _.constant(0);
        this.collection.sortField = JSON.stringify(this._lastSort.map((e) => [
            (e.type === 'metadata' ? 'meta.' : '') + e.value,
            e.dir === 'down' ? 1 : -1
        ]));
        this.collection.fetch({folderId: this.parentView.parentModel.id});
    };

    function itemListRender() {
        if (!this._lastSort && this._confList() && this._confList().defaultSort && this._confList().defaultSort.length) {
            this._lastSort = this._confList().defaultSort;
            this._setSort();
            return;
        }
        this.$el.html(ItemListTemplate({
            items: this.collection.toArray(),
            isParentPublic: this.public,
            hasMore: this.collection.hasNextPage(),
            formatSize: formatSize,
            checkboxes: this._checkboxes,
            downloadLinks: this._downloadLinks,
            viewLinks: this._viewLinks,
            showSizes: this._showSizes,
            highlightItem: this._highlightItem,
            selectedItemId: (this._selectedItem || {}).id,
            paginated: this._paginated,
            apiRoot: getApiRoot(),
            itemList: this._confList(),
            sort: this._lastSort
        }));

        const parent = this.$el;
        this.$el.find('.large_image_thumbnail').each(function () {
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

    if (this._confList() && this._hasAnyLargeImage) {
        return itemListRender.apply(this, _.rest(arguments));
    }

    render.call(this);
    largeImageConfig.getSettings((settings) => {
        var items = this.collection.toArray();
        var parent = this.$el;
        this._hasAnyLargeImage = !!_.some(items, function (item) {
            return item.has('largeImage');
        });
        if (this._confList() && this._hasAnyLargeImage) {
            return itemListRender.apply(this, _.rest(arguments));
        }
        if (settings['large_image.show_thumbnails'] === false ||
                this.$('.large_image_container').length > 0) {
            return this;
        }
        if (this._hasAnyLargeImage) {
            if (!this._confList()) {
                _.each(items, (item) => {
                    var elem = $('<div class="large_image_container"/>');
                    if (item.get('largeImage')) {
                        item.getAccessLevel(() => {
                            if (!this._confList()) {
                                addLargeImageDetails(item, elem, parent, settings.extraInfo);
                            }
                        });
                    }
                    $('a[g-item-cid="' + item.cid + '"]>i', parent).before(elem);
                    _loadMoreImages(parent);
                });
            }
        }
        return this;
    });
    return this;
});

function sortColumn(evt) {
    const header = $(evt.target);
    const entry = {
        type: header.attr('column_type'),
        value: header.attr('column_value')
    };
    const curDir = header.hasClass('down') ? 'down' : header.hasClass('up') ? 'up' : null;
    const nextDir = curDir === 'down' ? 'up' : 'down';
    header.toggleClass('down', nextDir === 'down').toggleClass('up', nextDir === 'up');
    entry.dir = nextDir;
    const oldSort = this._lastSort;
    if (!this._lastSort) {
        this._lastSort = [];
    }
    this._lastSort = this._lastSort.filter((e) => e.type !== entry.type || e.value !== entry.value);
    this._lastSort.unshift(entry);
    this._setSort();
    if (!_.isEqual(this._lastSort, oldSort)) {
        const curRoute = Backbone.history.fragment;
        const routeParts = splitRoute(curRoute);
        const query = parseQueryString(routeParts.name);
        query.sort = this._lastSort.map((e) => `${e.type}:${e.value}:${e.dir}`).join(',');
        if (router.enabled()) {
            router.navigate(routeParts.base + '?' + $.param(query));
        }
    }
}

export default ItemListWidget;
