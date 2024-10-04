import $ from 'jquery';
import _ from 'underscore';
import Backbone from 'backbone';

import {wrap} from '@girder/core/utilities/PluginUtils';
import {getApiRoot} from '@girder/core/rest';
import {AccessType} from '@girder/core/constants';
import {formatSize, parseQueryString, splitRoute} from '@girder/core/misc';
import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import ItemCollection from '@girder/core/collections/ItemCollection';
import FolderListWidget from '@girder/core/views/widgets/FolderListWidget';
import ItemListWidget from '@girder/core/views/widgets/ItemListWidget';

import largeImageConfig from './configView';
import {addToRoute} from '../routes';

import '../stylesheets/itemList.styl';
import ItemListTemplate from '../templates/itemList.pug';
import {MetadatumWidget, validateMetadataValue} from './metadataWidget';

ItemCollection.prototype.pageLimit = Math.max(250, ItemCollection.prototype.pageLimit);

wrap(HierarchyWidget, 'initialize', function (initialize, settings) {
    settings = settings || {};
    if (settings.paginated === undefined) {
        settings.paginated = true;
    }
    return initialize.call(this, settings);
});

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    if (!this.$('#flattenitemlist').length && this.$('.g-item-list-container').length && this.itemListView && this.itemListView.setFlatten) {
        $('button.g-checked-actions-button').parent().after(
            '<div class="li-flatten-item-list" title="Check to show items in all subfolders in this list"><input type="checkbox" id="flattenitemlist"></input><label for="flattenitemlist">Flatten</label></div>'
        );
        if ((this.itemListView || {})._recurse) {
            this.$('#flattenitemlist').prop('checked', true);
        }
        this.events['click #flattenitemlist'] = (evt) => {
            this.itemListView.setFlatten(this.$('#flattenitemlist').is(':checked'));
        };
        this.delegateEvents();
    }
    if (this.$('#flattenitemlist').length && this.parentModel.get('_modelType') !== 'folder') {
        this.$('.li-flatten-item-list').addClass('hidden');
    } else {
        this.$('.li-flatten-item-list').removeClass('hidden');
    }
});

wrap(FolderListWidget, 'checkAll', function (checkAll, checked) {
    if (checked && (this.parentView.itemListView || {})._recurse) {
        return;
    }
    return checkAll.call(this, checked);
});

wrap(ItemListWidget, 'initialize', function (initialize, settings) {
    this._inInit = true;
    const result = initialize.call(this, settings);
    delete this._hasAnyLargeImage;

    this._confList = () => {
        let list;
        if (!this._liconfig) {
            return undefined;
        }
        const namedList = this._namedList || this._liconfig.defaultItemList;
        if (this.$el.closest('.modal-dialog').length) {
            list = this._liconfig.itemListDialog;
        } else if (namedList && this._liconfig.namedItemLists && this._liconfig.namedItemLists[namedList]) {
            list = this._liconfig.namedItemLists[namedList];
        } else {
            list = this._liconfig.itemList;
        }
        if (list.group) {
            let group = list.group;
            group = !group.keys ? {keys: group} : group;
            group.keys = Array.isArray(group.keys) ? group.keys : [group.keys];
            group.keys = group.keys.filter((g) => !g.includes(',') && !g.includes(':'));
            if (!group.keys.length) {
                group = undefined;
            }
            list.group = group;
        }
        return list;
    };

    largeImageConfig.getConfigFile(settings.folderId, true, (val) => {
        if (!settings.folderId) {
            this._liconfig = val;
        }
        if (_.isEqual(val, this._liconfig) && !this._recurse) {
            this._inInit = false;
            this.render();
            return;
        }
        delete this._lastSort;
        this._liconfig = val;
        const curRoute = Backbone.history.fragment;
        const routeParts = splitRoute(curRoute);
        const query = parseQueryString(routeParts.name);
        this._namedList = query.namedList || undefined;
        let update = false;
        if (query.sort) {
            this._lastSort = query.sort.split(',').map((chunk) => {
                const parts = chunk.split(':');
                return {
                    type: parts[0],
                    value: parts[1],
                    dir: parts[2]
                };
            });
            update = true;
        } else if (this._confList && this._confList() && this._confList().defaultSort && this._confList().defaultSort.length) {
            this._lastSort = this._confList().defaultSort;
            update = true;
        }
        if (query.filter || this._recurse) {
            this._generalFilter = query.filter;
            this._setFilter(false);
            update = true;
        }
        this._inInit = false;
        if (update) {
            this._setSort();
        } else {
            this.render();
        }
    });
    this.events['click .li-item-list-header.sortable'] = (evt) => sortColumn.call(this, evt);
    this.events['click .li-item-list-cell-filter'] = (evt) => itemListCellFilter.call(this, evt);
    this.events['click .large_image_metadata.lientry_edit'] = (evt) => itemListMetadataEdit.call(this, evt);
    this.events['change .large_image_metadata.lientry_edit'] = (evt) => itemListMetadataEdit.call(this, evt);
    this.events['input .large_image_metadata.lientry_edit'] = (evt) => itemListMetadataEdit.call(this, evt);
    this.delegateEvents();
    this.setFlatten = (flatten) => {
        if (!!flatten !== !!this._recurse) {
            this._recurse = !!flatten;
            this._setFilter();
            this.render();
        }
    };
    return result;
});

wrap(ItemListWidget, 'render', function (render) {
    this.$el.closest('.modal-dialog').addClass('li-item-list-dialog');
    if (!this.$el.children().length) {
        this.$el.html('<span class="icon-spin1 animate-spin" title="Loading item list"/>');
    }

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

    /**
     * Set sort on the collection and perform a debounced re-fetch.
     */
    this._setSort = () => {
        if (!this._inFetch) {
            this._inFetch = true;
            this._needsFetch = false;
            if (this._lastSort) {
                this.collection.comparator = _.constant(0);
                this.collection.sortField = JSON.stringify(this._lastSort.map((e) => [
                    (e.type === 'metadata' ? 'meta.' : '') + e.value,
                    e.dir === 'down' ? 1 : -1
                ]));
            }
            this.collection._totalCount = 0;
            this.collection.fetch(_.extend({}, {folderId: this.parentView.parentModel.id}, this.collection.params), true).done(() => {
                const oldPages = this._totalPages;
                const pages = Math.ceil(this.collection.getTotalCount() / this.collection.pageLimit);
                this._totalPages = pages;
                // recheck if this has large images
                this._hasAnyLargeImage = !!_.some(this.collection.toArray(), function (item) {
                    return item.has('largeImage');
                });
                this._inFetch = false;
                if (oldPages !== pages || this.collection.offset !== this.collection.size()) {
                    this.collection.offset = this.collection.size();
                    this.trigger('g:paginated');
                    this.collection.trigger('g:changed');
                } else {
                    itemListRender.apply(this, _.rest(arguments));
                }
                if (this._needsFetch) {
                    this._setSort();
                }
            });
        } else {
            this._needsFetch = true;
        }
    };

    this._updateFilter = (evt) => {
        this._generalFilter = $(evt.target).val().trim();
        this._setFilter();
        addToRoute({filter: this._generalFilter});
    };

    this._clearFilter = (evt) => {
        this._generalFilter = '';
        this._setFilter();
        addToRoute({filter: this._generalFilter});
    };

    this._unescapePhrase = (val) => {
        if (val !== undefined) {
            val = val.replace('\\\'', '\'').replace('\\"', '"').replace('\\\\', '\\');
        }
        return val;
    };

    this._setFilter = (update) => {
        const val = this._generalFilter;
        let filter;
        const usedPhrases = {};
        const columns = (this._confList() || {}).columns || [];
        if (val !== undefined && val !== '' && columns.length) {
            // a value can be surrounded by single or double quotes, which will
            // be removed.
            const quotedValue = /((?:"((?:[^\\"]|\\\\|\\")*)(?:"|$)|'((?:[^\\']|\\\\|\\')*)(?:'|$)|([^:,\s]+)))/g;
            const phraseRE = new RegExp(
                new RegExp('((?:' + quotedValue.source + ':|))').source +
                /(-?)/.source +
                quotedValue.source +
                new RegExp('((?:,' + quotedValue.source + ')*)').source, 'g');
            filter = [];
            [...val.matchAll(phraseRE)].forEach((match) => {
                const coltag = this._unescapePhrase(match[5] || match[4] || match[3]);
                const phrase = this._unescapePhrase(match[10] || match[9] || match[8]);
                const negation = match[6] === '-';
                var phrases = [{phrase: phrase, exact: match[8] !== undefined}];
                if (match[11]) {
                    [...match[11].matchAll(quotedValue)].forEach((submatch) => {
                        const subphrase = this._unescapePhrase(submatch[4] || submatch[3] || submatch[2]);
                        // remove dupes?
                        if (subphrase && subphrase.length) {
                            phrases.push({phrase: subphrase, exact: submatch[2] !== undefined});
                        }
                    });
                }
                const key = `${coltag || ''}:` + phrases.map((p) => p.phrase + (p.exact ? '__exact__' : '')).join('|||');
                if (!phrases.length || usedPhrases[key]) {
                    return;
                }
                usedPhrases[key] = true;
                const clause = [];
                phrases.forEach(({phrase, exact}) => {
                    const numval = +phrase;
                    /* If numval is a non-zero number not in exponential
                     * notation, delta is the value of one for the least
                     * significant digit.  This will be NaN if phrase is not a
                     * number. */
                    const delta = Math.abs(+numval.toString().replace(/\d(?=.*[1-9](0*\.|)0*$)/g, '0').replace(/[1-9]/, '1'));
                    // escape for regex
                    phrase = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

                    columns.forEach((col) => {
                        let key;
                        if (coltag &&
                            coltag.localeCompare(col.title || col.value, undefined, {sensitivity: 'accent'}) &&
                            coltag.localeCompare(col.value, undefined, {sensitivity: 'accent'})
                        ) {
                            return;
                        }
                        if (col.type === 'record' && col.value !== 'controls') {
                            key = col.value;
                        } else if (col.type === 'metadata') {
                            key = 'meta.' + col.value;
                        }
                        if (!coltag && !exact) {
                            const r = new RegExp('^' + (phrase.substr(phrase.length - 1) === ':' ? phrase.substr(0, phrase.length - 1) : phrase), 'i');
                            if (r.exec(col.value) || r.exec(col.title || col.value)) {
                                clause.push({[key]: {$exists: true}});
                            }
                        }
                        if (key && exact) {
                            clause.push({[key]: {$regex: '^' + phrase + '$', $options: 'i'}});
                            if (!_.isNaN(numval)) {
                                clause.push({[key]: numval});
                            }
                        } else if (key) {
                            clause.push({[key]: {$regex: phrase, $options: 'i'}});
                            if (!_.isNaN(numval)) {
                                clause.push({[key]: numval});
                                if (numval > 0 && delta) {
                                    clause.push({[key]: {$gte: numval, $lt: numval + delta}});
                                } else if (numval < 0 && delta) {
                                    clause.push({[key]: {$lte: numval, $gt: numval + delta}});
                                }
                            }
                        }
                    });
                });
                if (clause.length > 0) {
                    filter.push(!negation ? {$or: clause} : {$nor: clause});
                } else if (!negation) {
                    filter.push({$or: [{_no_such_value_: '_no_such_value_'}]});
                }
            });
            if (filter.length === 0) {
                filter = undefined;
            } else {
                if (filter.length === 1) {
                    filter = filter[0];
                } else {
                    filter = {$and: filter};
                }
                filter = '_filter_:' + JSON.stringify(filter);
            }
        }
        if (this._recurse) {
            filter = '_recurse_:' + (filter || '');
        }
        if (filter !== this._filter || filter !== (this.collection.params || {}).text) {
            this._filter = filter;
            this.collection.params = this.collection.params || {};
            this.collection.params.text = this._filter;
            if (update !== false) {
                this._setSort();
            }
        }
    };

    function itemListRender() {
        if (this._inInit || this._inFetch) {
            return;
        }
        const root = this.$el.closest('.g-hierarchy-widget');
        if (!root.find('.li-item-list-filter').length) {
            let base = root.find('.g-hierarchy-actions-header .g-folder-header-buttons').eq(0);
            let func = 'after';
            if (!base.length) {
                base = root.find('.g-hierarchy-breadcrumb-bar>.breadcrumb>div').eq(0);
                func = 'before';
            }
            if (base.length) {
                base[func]('<span class="li-item-list-filter">Filter: <input class="li-item-list-filter-input" title="' +
                    'All specified terms must be included.  ' +
                    'Surround with single quotes to include spaces, double quotes for exact value match.  ' +
                    'Prefix with - to exclude that value.  ' +
                    'By default, all columns are searched.  ' +
                    'Use <column>:<value1>[,<value2>...] to require that a column matches a specified value or any of a list of specified values.  ' +
                    'Column and value names can be quoted to include spaces (single quotes for substring match, double quotes for exact value match).  ' +
                    'If <column>:-<value1>[,<value2>...] is specified, matches will exclude the list of values.  ' +
                    'Non-exact matches without a column specifier will also match columns that start with the specified value.  ' +
                    '"></input>' +
                    '<span class="li-item-list-filter-clear"><i class="icon-cancel"></i></span>' +
                    '</span>');
                if (this._generalFilter) {
                    root.find('.li-item-list-filter-input').val(this._generalFilter);
                }
                this.parentView.events['change .li-item-list-filter-input'] = this._updateFilter;
                this.parentView.events['input .li-item-list-filter-input'] = this._updateFilter;
                this.parentView.events['click .li-item-list-filter-clear'] = (evt) => {
                    this.parentView.$el.find('.li-item-list-filter-input').val('');
                    this._clearFilter();
                };
                this.parentView.delegateEvents();
            }
        }

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
            hasAnyLargeImage: this._hasAnyLargeImage,
            itemList: this._confList(),
            sort: this._lastSort,
            MetadatumWidget: MetadatumWidget,
            accessLevel: this.accessLevel,
            parentView: this,
            AccessType: AccessType
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

    largeImageConfig.getSettings((settings) => {
        var items = this.collection.toArray();
        this._hasAnyLargeImage = !!_.some(items, function (item) {
            return item.has('largeImage');
        });
        if (this._confList()) {
            return itemListRender.apply(this, _.rest(arguments));
        }

        if (this._recurse && !((this.collection || {}).params || {}).text) {
            this._setFilter();
            this.render();
        }
        return this;
    });
    return this;
});

wrap(ItemListWidget, 'remove', function (remove) {
    const root = this.$el.closest('.g-hierarchy-widget');
    root.remove('.li-item-list-filter');
    delete this.parentView.events['change .li-item-list-filter-input'];
    delete this.parentView.events['input .li-item-list-filter-input'];
    this.parentView.delegateEvents();
    return remove.call(this);
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
        addToRoute({sort: this._lastSort.map((e) => `${e.type}:${e.value}:${e.dir}`).join(',')});
    }
}

function itemListCellFilter(evt) {
    evt.preventDefault();
    const cell = $(evt.target).closest('.li-item-list-cell-filter');
    let filter = this._generalFilter || '';
    let val = cell.attr('filter-value');
    let col = cell.attr('column-value');
    if (/[ '\\]/.exec(col)) {
        col = "'" + col.replace('\\', '\\\\').replace("'", "\\'") + "'";
    }
    val = val.replace('\\', '\\\\').replace('"', '\\"');
    filter += ` ${col}:"${val}"`;
    filter = filter.trim();
    this.$el.closest('.g-hierarchy-widget').find('.li-item-list-filter-input').val(filter);
    this._generalFilter = filter;
    this._setFilter();
    addToRoute({filter: this._generalFilter});
    this._setSort();
    return false;
}

function itemListMetadataEdit(evt) {
    evt.preventDefault();
    if (evt.type === 'click') {
        return false;
    }
    const ctrl = $(evt.target).closest('.lientry_edit');
    const columns = (this._confList() || {}).columns || [];
    const column = columns[+ctrl.attr('column-idx')];
    let tempValue = ctrl.find('.g-widget-metadata-value-input').val();
    tempValue = tempValue.trim();
    let valResult = validateMetadataValue(column, tempValue, self._lastValidationError || (tempValue === '' && !column.required));
    if (tempValue === '' && !column.required) {
        valResult = {value: tempValue};
    }
    if (!valResult) {
        self._lastValidationError = true;
        return false;
    }
    self._lastValidationError = false;
    const item = this.collection.get(ctrl.closest('[g-item-cid]').attr('g-item-cid'));
    let value = item.get('meta') || {};
    let meta;
    let key;
    column.value.split('.').forEach((part) => {
        meta = value;
        key = part;
        value = (value || {})[part];
    });
    if (value === valResult.value) {
        return;
    }
    meta[key] = valResult.value;
    item._sendMetadata(item.get('meta'));
    return false;
}

export default ItemListWidget;
