import _ from 'underscore';
import AccessControlledModel from '@girder/core/models/AccessControlledModel';
import {getCurrentUser} from '@girder/core/auth';
import {restRequest} from '@girder/core/rest';
import MetadataMixin from '@girder/core/models/MetadataMixin';

import ElementCollection from '../collections/ElementCollection';
import convert from '../annotations/convert';
import {convertFeatures} from '../annotations/convertFeatures';

import style from '../annotations/style.js';

const PropsDefaults = {
    default: {
        fillColor: {r: 1, g: 120 / 255, b: 0},
        fillOpacity: 0.8,
        strokeColor: {r: 0, g: 0, b: 0},
        strokeOpacity: 1,
        strokeWidth: 1
    },
    rectangle: {
        fillColor: {r: 176 / 255, g: 222 / 255, b: 92 / 255},
        strokeColor: {r: 153 / 255, g: 153 / 255, b: 153 / 255},
        strokeWidth: 2
    },
    ellipse: {
        fillColor: {r: 176 / 255, g: 222 / 255, b: 92 / 255},
        strokeColor: {r: 153 / 255, g: 153 / 255, b: 153 / 255},
        strokeWidth: 2
    },
    circle: {
        fillColor: {r: 176 / 255, g: 222 / 255, b: 92 / 255},
        strokeColor: {r: 153 / 255, g: 153 / 255, b: 153 / 255},
        strokeWidth: 2
    },
    polyline: {
        strokeColor: {r: 1, g: 120 / 255, b: 0},
        strokeOpacity: 0.5,
        strokeWidth: 4
    },
    polyline_closed: {
        fillColor: {r: 176 / 255, g: 222 / 255, b: 92 / 255},
        strokeColor: {r: 153 / 255, g: 153 / 255, b: 153 / 255},
        strokeWidth: 2
    }
};

function propsDefault(propsdict) {
    Object.assign(propsdict, style(propsdict));
    const type = propsdict.type + (propsdict.closed ? '_closed' : '');
    ['fillColor', 'strokeColor', 'strokeWidth', 'fillOpacity', 'strokeOpacity'].forEach((key) => {
        if (propsdict[key] === undefined) {
            propsdict[key] = (PropsDefaults[type] || PropsDefaults.default)[key];
        }
        if (propsdict[key] === undefined) {
            propsdict[key] = PropsDefaults.default[key];
        }
    });
}

/**
 * Define a backbone model representing an annotation.
 * An annotation contains zero or more "elements" or
 * geometric primitives that are represented in the
 * embedded "elements" attribute.  This attribute is
 * an "ElementCollection" that triggers events when
 * any of the "ElementModel"'s contained within change.
 *
 * This model listens to changes in the element collection
 * and updates its own attribute in response.  Users
 * should not modify the "elements" attribute directly.
 */
const AnnotationModel = AccessControlledModel.extend({
    resourceName: 'annotation',

    defaults: {
        annotation: {},
        minElements: 5000,
        maxDetails: 500000,
        maxCentroids: 5000000
    },

    initialize() {
        if (!this.get('updated') && getCurrentUser()) {
            this.attributes.updated = (new Date()).toISOString(); // eslint-disable-line backbone/no-model-attributes
            this.attributes.updatedId = getCurrentUser().id; // eslint-disable-line backbone/no-model-attributes
        }
        this._region = {
            maxDetails: this.get('maxDetails'),
            minElements: this.get('minElements'),
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
        this.bindListeners();
    },
    bindListeners: function () {
        this.listenTo(this._elements, 'change add remove reset', this.handleChangeEvent);
        this.listenTo(this._elements, 'change add', this.handleElementChanged);
        this.listenTo(this._elements, 'remove', this.handleElementRemoved);
    },
    handleChangeEvent: function () {
        // copy the object to ensure a change event is triggered
        var annotation = _.extend({}, this.get('annotation'));

        annotation.elements = this._elements.toJSON();
        this.set('annotation', annotation);
    },
    handleElementChanged: function (element, collection, options) {
        if (!this._centroids) {
            return;
        }
        const props = {
            type: element.get('type'),
            fillColor: element.get('fillColor'),
            lineColor: element.get('lineColor'),
            lineWidth: element.get('lineWidth'),
            closed: element.get('closed')
        };
        let propidx;
        for (propidx = 0; propidx < this._centroids.props.length; propidx += 1) {
            const p = this._centroids.props[propidx];
            if (p.type === props.type && p.fillColor === props.fillColor && p.lineColor === props.lineColor && p.lineWidth === props.lineWidth && p.closed === props.closed) {
                break;
            }
        }
        if (propidx === this._centroids.props.length) {
            propsDefault(props);
            this._centroids.props.push(props);
        }
        const elid = element.id;
        let idx;
        for (idx = 0; idx < this._centroids.centroids.id.length; idx += 1) {
            if (this._centroids.centroids.id[idx] === elid) {
                break;
            }
        }
        let x, y, r = 1;
        if (element.get('center')) {
            x = element.get('center')[0];
            y = element.get('center')[0];
            if (element.get('radius')) {
                r = element.get('radius');
            } else if (element.get('width')) {
                r = Math.max(1, (element.get('width') ** 2 + element.get('height') ** 2) ** 0.5 / 2);
            }
        } else if (element.get('points')) {
            const pts = element.get('points');
            let minx = pts[0][0], maxx = pts[0][0];
            let miny = pts[0][1], maxy = pts[0][1];
            for (const [px, py] of pts) {
                minx = Math.min(minx, px);
                miny = Math.min(miny, py);
                maxx = Math.max(maxx, px);
                maxy = Math.max(maxy, py);
            }
            x = (maxx + minx) / 2;
            y = (maxy + miny) / 2;
            r = Math.max(1, ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5);
        }
        if (idx === this._centroids.centroids.id.length) {
            this._centroids.centroids.id.push(elid);

            const newX = new Float32Array(idx + 1);
            newX.set(this._centroids.centroids.x);
            newX[idx] = x;
            this._centroids.centroids.x = newX;

            const newY = new Float32Array(idx + 1);
            newY.set(this._centroids.centroids.y);
            newY[idx] = y;
            this._centroids.centroids.y = newY;

            const newR = new Float32Array(idx + 1);
            newR.set(this._centroids.centroids.r);
            newR[idx] = r;
            this._centroids.centroids.r = newR;

            const newS = new Uint32Array(idx + 1);
            newS.set(this._centroids.centroids.s);
            newS[idx] = propidx;
            this._centroids.centroids.s = newS;
        } else {
            this._centroids.centroids.x[idx] = x;
            this._centroids.centroids.y[idx] = y;
            this._centroids.centroids.r[idx] = r;
            this._centroids.centroids.s[idx] = propidx;
        }
        this._centroids._redraw = true;
        this._centroids.data = {length: this._centroids.centroids.id.length};
    },

    handleElementRemoved: function (element, collection, options) {
        if (!this._centroids) {
            return;
        }
        const elid = element.id;
        for (let idx = 0; idx < this._centroids.centroids.id.length; idx += 1) {
            if (this._centroids.centroids.id[idx] === elid) {
                if (this._shownIds) {
                    this._shownIds.add(elid);
                }
                const last = this._centroids.centroids.id.length - 1;
                this._centroids.centroids.id[idx] = this._centroids.centroids.id[last];
                this._centroids.centroids.x[idx] = this._centroids.centroids.x[last];
                this._centroids.centroids.y[idx] = this._centroids.centroids.y[last];
                this._centroids.centroids.r[idx] = this._centroids.centroids.r[last];
                this._centroids.centroids.s[idx] = this._centroids.centroids.s[last];
                this._centroids.centroids.id.splice(last, 1);
                this._centroids.data = {length: this._centroids.centroids.id.length};
                this._centroids._redraw = true;
                break;
            }
        }
    },

    /**
     * Fetch the centroids and unpack the binary data.
     */
    fetchCentroids: function () {
        var url = (this.altUrl || this.resourceName) + '/' + this.get('_id');
        var restOpts = {
            url: url,
            data: {
                centroids: true,
                _: (this.get('updated') || this.get('created')) + '_' + this.get('_version')
            },
            xhrFields: {
                responseType: 'arraybuffer'
            },
            error: null
        };
        if ((this.get('_elementQuery') || {}).count && (this.get('_elementQuery') || {}).count > this.get('maxCentroids')) {
            restOpts.data.sort = 'size';
            restOpts.data.sortdir = -1;
            restOpts.data.limit = this.get('maxCentroids');
        }
        return restRequest(restOpts).done((resp) => {
            let dv = new DataView(resp);
            let z0 = 0, z1 = dv.byteLength - 1;
            for (; dv.getUint8(z0) && z0 < dv.byteLength; z0 += 1);
            for (; dv.getUint8(z1) && z1 >= 0; z1 -= 1);
            if (z0 >= z1) {
                throw new Error('invalid centroid data');
            }
            const json = new Uint8Array(z0 + dv.byteLength - z1 - 1);
            json.set(new Uint8Array(resp.slice(0, z0)), 0);
            json.set(new Uint8Array(resp.slice(z1 + 1)), z0);
            const result = JSON.parse(decodeURIComponent(escape(String.fromCharCode.apply(null, json))));
            result.props = result._elementQuery.props.map((props) => {
                const propsdict = {};
                result._elementQuery.propskeys.forEach((key, i) => {
                    propsdict[key] = props[i];
                });
                propsDefault(propsdict);
                return propsdict;
            });
            dv = new DataView(resp, z0 + 1, z1 - z0 - 1);
            if (dv.byteLength !== result._elementQuery.returned * 28) {
                throw new Error('invalid centroid data size');
            }
            const centroids = {
                id: new Array(result._elementQuery.returned),
                x: new Float32Array(result._elementQuery.returned),
                y: new Float32Array(result._elementQuery.returned),
                r: new Float32Array(result._elementQuery.returned),
                s: new Uint32Array(result._elementQuery.returned)
            };
            let i, s;
            for (i = s = 0; s < dv.byteLength; i += 1, s += 28) {
                centroids.id[i] =
                    ('0000000' + dv.getUint32(s, false).toString(16)).substr(-8) +
                    ('0000000' + dv.getUint32(s + 4, false).toString(16)).substr(-8) +
                    ('0000000' + dv.getUint32(s + 8, false).toString(16)).substr(-8);
                centroids.x[i] = dv.getFloat32(s + 12, true);
                centroids.y[i] = dv.getFloat32(s + 16, true);
                centroids.r[i] = dv.getFloat32(s + 20, true);
                centroids.s[i] = dv.getUint32(s + 24, true);
            }
            result.centroids = centroids;
            result.data = {length: result._elementQuery.returned};
            if (result._elementQuery.count > result._elementQuery.returned) {
                result.partial = true;
            }
            this._centroids = result;
            return result;
        });
    },

    fetchCentroidsWrapper: function (opts) {
        this._inFetch = 'centroids';
        return this.fetchCentroids().then(() => {
            this._inFetch = true;
            if (opts.extraPath) {
                this.trigger('g:fetched.' + opts.extraPath);
            } else {
                this.trigger('g:fetched');
            }
            return null;
        }).always(() => {
            this._inFetch = false;
            if (this._nextFetch) {
                var nextFetch = this._nextFetch;
                this._nextFetch = null;
                nextFetch();
            }
            return null;
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
            console.error('Error: You must set an altUrl or a resourceName on your model.');
            return;
        }

        opts = opts || {};
        var user = getCurrentUser();
        var restOpts = {
            url: (this.altUrl || this.resourceName) + '/' + this.get('_id'),
            /* Add our region request into the query */
            data: Object.assign({}, this._region, {_: (this.get('updated') || this.get('created')) + (user && user.id ? '_' + user.id : '') + '_' + this.get('_version')})
        };
        if (opts.extraPath) {
            restOpts.url += '/' + opts.extraPath;
        }
        if (opts.ignoreError) {
            restOpts.error = null;
        }
        if (this._pageElements === undefined && (this.get('_elementCount') || 0) > this.get('minElements') && (this.get('_detailsCount') || 0) > this.get('maxDetails')) {
            this._pageElements = true;
            return this.fetchCentroidsWrapper(opts);
        }
        this._inFetch = true;
        if (this._refresh) {
            delete this._pageElements;
            delete this._centroids;
            this._refresh = false;
        }
        return restRequest(restOpts).always(() => {
            if (this._inFetch !== 'centroids') {
                this._inFetch = false;
                if (this._nextFetch) {
                    var nextFetch = this._nextFetch;
                    this._nextFetch = null;
                    if (this._pageElements !== false) {
                        nextFetch();
                    }
                }
            }
        }).done((resp) => {
            const annotation = resp.annotation || {};
            const elements = annotation.elements || [];

            this._fromFetch = true;
            this.set(resp);
            this._fromFetch = null;
            if (this._pageElements === undefined && resp._elementQuery) {
                this._pageElements = resp._elementQuery.count > resp._elementQuery.returned;
                if (this._pageElements) {
                    this.fetchCentroidsWrapper(opts);
                } else {
                    this._nextFetch = null;
                }
            }
            if (this._inFetch !== 'centroids') {
                if (opts.extraPath) {
                    this.trigger('g:fetched.' + opts.extraPath);
                } else {
                    this.trigger('g:fetched');
                }
            }
            this._fromFetch = true;
            this._elements.reset(elements, _.extend({sync: true}, opts));
            this._fromFetch = null;
        }).fail((err) => {
            this.trigger('g:error', err);
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
        let url;
        let method;
        const isNew = this.isNew();
        if (isNew && this._changeLog) {
            delete this._changeLog;
        }
        if (isNew) {
            if (!this.get('itemId')) {
                throw new Error('itemId is required to save new annotations');
            }
            url = `annotation?itemId=${this.get('itemId')}`;
            method = 'POST';
        } else {
            url = `annotation/${this.id}`;
            method = 'PUT';
            if (getCurrentUser()) {
                this.attributes.updated = (new Date()).toISOString(); // eslint-disable-line backbone/no-model-attributes
                this.attributes.updatedId = getCurrentUser().id; // eslint-disable-line backbone/no-model-attributes
            }
        }
        let data;

        if (this._changeLog) {
            method = 'PATCH';
            const annot = this.get('annotation');
            data = Object.values(this._changeLog);
            data.forEach((change) => {
                if (change.value && change.value.label && !change.value.label.value) {
                    delete change.value.label;
                }
            });
            Object.keys(annot).forEach((k) => {
                if (k !== 'elements') {
                    data.push({op: 'replace', path: k, value: annot[k]});
                }
            });
            delete this._changeLog;
        } else {
            data = _.extend({}, this.get('annotation'));
            if (this._pageElements === false || isNew) {
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
                    /* we should only get to here if we really only wanted to
                     * save the main annotation and not the elements, so quiet
                     * our warning
                    console.warn('Cannot save elements of a paged annotation');
                     */
                }
            }
        }

        this._inSave = true;
        return restRequest({
            url,
            method,
            contentType: 'application/json',
            processData: false,
            data: JSON.stringify(data)
        }).done((annotation) => {
            this._inSave = false;
            if (isNew) {
                // the elements array does not come back with this request
                annotation.elements = (this.get('annotation') || {}).elements || [];
                this.set(annotation);
            }
            this.trigger('sync', this, annotation, options);
            if (this._nextFetch && !this._inFetch && (this._saveAgain === undefined || this._saveAgain === false)) {
                var nextFetch = this._nextFetch;
                this._nextFetch = null;
                nextFetch();
            }
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
            if (getCurrentUser()) {
                this.attributes.updated = (new Date()).toISOString(); // eslint-disable-line backbone/no-model-attributes
                this.attributes.updatedId = getCurrentUser().id; // eslint-disable-line backbone/no-model-attributes
            }
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
     * Return annotations that cannot be represented as geojson as geojs
     * features specifications.
     *
     * @param webglLayer: the parent feature layer.
     */
    non_geojson(layer) {
        const json = this.get('annotation') || {};
        const elements = json.elements || [];
        return convertFeatures(elements, {annotation: this.id}, layer);
    },

    /**
     * Return annotation elements that cannot be represented as geojs
     * features, such as image overlays.
     */
    overlays() {
        const overlayElementTypes = ['image', 'pixelmap'];
        const json = this.get('annotation') || {};
        const elements = json.elements || [];
        return elements.filter((element) => overlayElementTypes.includes(element.type));
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
     * @param {number} sizeX the maximum width to query.
     * @param {number} sizeY the maximum height to query.
     */
    setView(bounds, zoom, maxZoom, noFetch, sizeX, sizeY) {
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
        if (this._pageElements || this._region.left !== undefined) {
            var lastRegion = Object.assign({}, this._region);
            this._region.left = Math.max(0, bounds.left - xoverlap);
            this._region.top = Math.max(0, bounds.top - yoverlap);
            this._region.right = Math.min(sizeX || 1e6, bounds.right + xoverlap);
            this._region.bottom = Math.min(sizeY || 1e6, bounds.bottom + yoverlap);
            this._region.maxDetails = zoom + 1 < maxZoom ? this.get('maxDetails') : undefined;
            this._lastZoom = zoom;
            if (['left', 'top', 'right', 'bottom', 'maxDetails'].every((key) => this._region[key] === lastRegion[key])) {
                return;
            }
        }
        if (noFetch) {
            return;
        }
        if (!this._nextFetch) {
            var nextFetch = () => {
                this.fetch();
            };
            if (this._inFetch || this._inSave) {
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

_.extend(AnnotationModel.prototype, MetadataMixin);

export default AnnotationModel;
