import _ from 'underscore';
import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import { restRequest } from '@girder/core/rest';

import ElementCollection from '../collections/ElementCollection';
import convert from '../annotations/convert';

/**
 * Define a backbone model representing an annotation.
 * An annotation contains zero or more "elements" or
 * geometric primatives that are represented in the
 * embedded "elements" attribute.  This attribute is
 * an "ElementCollection" that triggers events when
 * any of the "ElementModel"'s contained within change.
 *
 * This model listens to changes in the element collection
 * and updates its own attribute in response.  Users
 * should not modify the "elements" attribute directly.
 */
export default AccessControlledModel.extend({
    resourceName: 'annotation',

    defaults: {
        'annotation': {}
    },

    initialize() {
        this._region = {
            maxDetails: 250000,
            sort: 'size',
            sortdir: -1
        };
        /* amount of annotations to request compared to visible area.  1 will
         * request exactly the visible area of the map, 2 will get a region
         * twice as big in each direction. */
        this._viewArea = 3;
        this._elements = new ElementCollection(
            this.get('annotation').elements || []
        );
        this._elements.annotation = this;

        this.listenTo(this._elements, 'change add remove reset', () => {
            // copy the object to ensure a change event is triggered
            var annotation = _.extend({}, this.get('annotation'));

            annotation.elements = this._elements.toJSON();
            this.set('annotation', annotation);
        });
    },

    /**
     * Fetch a single resource from the server. Triggers g:fetched on success,
     * or g:error on error.
     * To ignore the default error handler, pass
     *     ignoreError: true
     * in your opts object.
     */
    fetch: function (opts) {
        if (this.altUrl === null && this.resourceName === null) {
            alert('Error: You must set an altUrl or a resourceName on your model.'); // eslint-disable-line no-alert
            return;
        }

        opts = opts || {};
        var restOpts = {
            url: (this.altUrl || this.resourceName) + '/' + this.get('_id'),
            /* Add out region request into the query */
            data: this._region
        };
        if (opts.extraPath) {
            restOpts.url += '/' + opts.extraPath;
        }
        if (opts.ignoreError) {
            restOpts.error = null;
        }
        this._inFetch = true;
        return restRequest(restOpts).done((resp) => {
            const annotation = resp.annotation || {};
            const elements = annotation.elements || [];

            this.set(resp);
            if (this._pageElements === undefined && resp._elementQuery) {
                this._pageElements = resp._elementQuery.count > resp._elementQuery.returned;
            }
            if (opts.extraPath) {
                this.trigger('g:fetched.' + opts.extraPath);
            } else {
                this.trigger('g:fetched');
            }

            this._elements.reset(elements, _.extend({sync: true}, opts));
        }).fail((err) => {
            this.trigger('g:error', err);
        }).always(() => {
            this._inFetch = false;
            if (this._nextFetch) {
                var nextFetch = this._nextFetch;
                this._nextFetch = null;
                nextFetch();
            }
        });
    },

    /**
     * Get/set for a refresh flag.
     *
     * @param {boolean} [val] If specified, set the refresh flag.  If not
     *    specified, return the refresh flag.
     * @returns {boolean|this}
     */
    refresh(val) {
        if (val === undefined) {
            return self._refresh;
        }
        self._refresh = val;
        return this;
    },

    /**
     * Perform a PUT or POST request on the annotation data depending
     * on whether the annotation is new or not.  This mirrors somewhat
     * the api of `Backbone.Model.save`.  For new models, the `itemId`
     * attribute is required.
     */
    save(options) {
        const data = _.extend({}, this.get('annotation'));
        let url;
        let method;

        if (this.isNew()) {
            if (!this.get('itemId')) {
                throw new Error('itemId is required to save new annotations');
            }
            url = `annotation?itemId=${this.get('itemId')}`;
            method = 'POST';
        } else {
            url = `annotation/${this.id}`;
            method = 'PUT';
        }

        if (this._pageElements === false || this.isNew()) {
            this._pageElements = false;
            data.elements = _.map(data.elements, (element) => {
                element = _.extend({}, element);
                if (element.label && !element.label.value) {
                    delete element.label;
                }
                return element;
            });
        } else {
            delete data.elements;
            // we don't want to override an annotation with a partial response
            if (this._pageElements === true) {
                console.warn('Cannot save elements of a paged annotation');
            }
        }

        return restRequest({
            url,
            method,
            contentType: 'application/json',
            processData: false,
            data: JSON.stringify(data)
        }).done((annotation) => {
            // the elements array does not come back with this request
            annotation.elements = (this.get('annotation') || {}).elements || [];
            this.set(annotation);
            this.trigger('sync', this, annotation, options);
        });
    },

    /**
     * Perform a DELETE request on the annotation model and remove all
     * event listeners.  This mirrors the api of `Backbone.Model.destroy`
     * without the backbone specific options, which are not supported by
     * girder's base model either.
     */
    destroy(options) {
        this.stopListening();
        this.trigger('destroy', this, this.collection, options);
        return this.delete(options);
    },

    name() {
        return (this.get('annotation') || {}).name;
    },

    /**
     * Perform a DELETE request on the annotation model and reset the id
     * attribute, but don't remove event listeners.
     */
    delete(options) {
        this.trigger('g:delete', this, this.collection, options);
        let xhr = false;
        if (!this.isNew()) {
            xhr = restRequest({
                url: `annotation/${this.id}`,
                method: 'DELETE'
            });
        }
        this.unset('_id');
        return xhr;
    },

    /**
     * Return the annotation as a geojson FeatureCollection.
     *
     * WARNING: Not all annotations are representable in geojson.
     * Annotation types that cannot be converted will be ignored.
     */
    geojson() {
        const json = this.get('annotation') || {};
        const elements = json.elements || [];
        return convert(elements, {annotation: this.id});
    },

    /**
     * Set the view.  If we are paging elements, possibly refetch the elements.
     * Callers should listen for the g:fetched event to know when new elements
     * have been fetched.
     *
     * @param {object} bounds the corners of the visible region.  This is an
     *      object with left, top, right, bottom in pixels.
     * @param {number} zoom the zoom factor.
     * @param {number} maxZoom the maximum zoom factor.
     * @param {boolean} noFetch Truthy to not perform a fetch if the view
     *  changes.
     */
    setView(bounds, zoom, maxZoom, noFetch) {
        if (this._pageElements === false || this.isNew()) {
            return;
        }
        var width = bounds.right - bounds.left,
            height = bounds.bottom - bounds.top,
            xoverlap = (width * (this._viewArea - 1)) / 2,
            yoverlap = (height * (this._viewArea - 1)) / 2,
            minxoverlap = xoverlap / 2,
            minyoverlap = yoverlap / 2;
        var canskip = (this._region.left !== undefined &&
            bounds.left >= this._region.left + minxoverlap &&
            bounds.top >= this._region.top + minyoverlap &&
            bounds.right <= this._region.right - minxoverlap &&
            bounds.bottom <= this._region.bottom - minyoverlap &&
            Math.abs(this._lastZoom - zoom) < 1);
        if (canskip && !this._inFetch) {
            return;
        }
        this._region.left = bounds.left - xoverlap;
        this._region.top = bounds.top - yoverlap;
        this._region.right = bounds.right + xoverlap;
        this._region.bottom = bounds.bottom + yoverlap;
        /* ask for items that will be at least 0.5 pixels, minus a bit */
        this._lastZoom = zoom;
        this._region.minimumSize = Math.pow(2, maxZoom - zoom - 1) - 1;
        if (noFetch) {
            return;
        }
        if (!this._nextFetch) {
            var nextFetch = () => {
                this.fetch();
            };
            if (this._inFetch) {
                this._nextFetch = nextFetch;
            } else {
                nextFetch();
            }
        }
    },

    /**
     * Return a backbone collection containing the annotation elements.
     */
    elements() {
        return this._elements;
    }
});
