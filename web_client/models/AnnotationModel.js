import _ from 'underscore';
import Model from 'girder/models/Model';
import { restRequest } from 'girder/rest';

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
export default Model.extend({
    resourceName: 'annotation',

    defaults: {
        'annotation': {}
    },

    initialize() {
        this._region = {
            maxDetails: 100000,
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
            alert('Error: You must set an altUrl or a resourceName on your model.');
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
            this.set(resp);
            if (this._pageElements === undefined && resp._elementQuery) {
                this._pageElements = resp._elementQuery.count > resp._elementQuery.returned;
            }
            if (opts.extraPath) {
                this.trigger('g:fetched.' + opts.extraPath);
            } else {
                this.trigger('g:fetched');
            }
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
     * @param {object} bounds: the corners of the visible region.  This is an
     *      object with left, top, right, bottom in pixels.
     * @param {number} zoom: the zoom factor.
     * @param {number} maxZoom: the maximum zoom factor.
     */
    setView(bounds, zoom, maxZoom) {
        if (this._pageElements === false || !this.get('_id')) {
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
        this._region.minSize = Math.pow(2, maxZoom - zoom - 1) - 1;
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
