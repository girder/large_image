import $ from 'jquery';
import _ from 'underscore';
// Import hammerjs for geojs touch events
import Hammer from 'hammerjs';
import d3 from 'd3';

import { restRequest } from '@girder/core/rest';

import ImageViewerWidget from './base';
import setFrameQuad from './setFrameQuad.js';

window.hammerjs = Hammer;
window.d3 = d3;

var GeojsImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        this._scale = settings.scale;
        this._setFrames = settings.setFrames;

        let root = '/static/built';
        try {
            root = __webpack_public_path__ || root; // eslint-disable-line
        } catch (err) { }
        root = root.replace(/\/$/, '');
        $.when(
            ImageViewerWidget.prototype.initialize.call(this, settings).then(() => {
                if (this.metadata.geospatial) {
                    this.tileWidth = this.tileHeight = null;
                    return restRequest({
                        type: 'GET',
                        url: 'item/' + this.itemId + '/tiles',
                        data: {projection: 'EPSG:3857'}
                    }).done((resp) => {
                        this.levels = resp.levels;
                        this.tileWidth = resp.tileWidth;
                        this.tileHeight = resp.tileHeight;
                        this.sizeX = resp.sizeX;
                        this.sizeY = resp.sizeY;
                        this.metadata = resp;
                    });
                }
                return this;
            }),
            $.ajax({ // like $.getScript, but allow caching
                url: root + '/plugins/large_image/extra/geojs.js',
                dataType: 'script',
                cache: true
            }))
            .done(() => {
                this.trigger('g:beforeFirstRender', this);
                this.render();
            });
    },

    render: function () {
        // If script or metadata isn't loaded, then abort
        if (!window.geo || !this.tileWidth || !this.tileHeight || this.deleted) {
            return this;
        }

        if (this.viewer) {
            // don't rerender the viewer
            return this;
        }

        var geo = window.geo; // this makes the style checker happy

        var params;
        if (!this.metadata.geospatial || !this.metadata.bounds) {
            var w = this.sizeX, h = this.sizeY;
            params = geo.util.pixelCoordinateParams(
                this.el, w, h, this.tileWidth, this.tileHeight);
            params.layer.useCredentials = true;
            params.layer.url = this._getTileUrl('{z}', '{x}', '{y}');
            if (this.tileWidth > 8192 || this.tileHeight > 8192) {
                params.layer.renderer = 'canvas';
            }
            this.viewer = geo.map(params.map);
            params.layer.autoshareRenderer = false;
            this._layer = this.viewer.createLayer('osm', params.layer);
            if (this.metadata.frames && this.metadata.frames.length > 1) {
                setFrameQuad(this.metadata, this._layer, {
                    // allow more and larger textures is slower, balancing
                    // performance and appearance
                    // maxTextures: 16,
                    // maxTotalTexturePixels: 256 * 1024 * 1024,
                    baseUrl: this._getTileUrl('{z}', '{x}', '{y}').split('/tiles/')[0] + '/tiles'
                });
                this._layer.setFrameQuad(0);
            }
        } else {
            params = {
                keepLower: false,
                attribution: null,
                url: this._getTileUrl('{z}', '{x}', '{y}', {'encoding': 'PNG', 'projection': 'EPSG:3857'}),
                useCredentials: true,
                maxLevel: this.levels - 1
            };
            // the metadata levels is the count including level 0, so use one
            // less than the value specified
            this.viewer = geo.map({node: this.el, max: this.levels - 1});
            if (this.metadata.bounds.xmin !== this.metadata.bounds.xmax && this.metadata.bounds.ymin !== this.metadata.bounds.ymax) {
                this.viewer.bounds({
                    left: this.metadata.bounds.xmin,
                    right: this.metadata.bounds.xmax,
                    top: this.metadata.bounds.ymax,
                    bottom: this.metadata.bounds.ymin
                }, 'EPSG:3857');
            }
            this.viewer.createLayer('osm');
            if (this.tileWidth > 8192 || this.tileHeight > 8192) {
                params.renderer = 'canvas';
            }
            params.autoshareRenderer = false;
            this._layer = this.viewer.createLayer('osm', params);
        }
        if (this._setFrames) {
            this._setFrames(this.metadata, _.bind(this.frameUpdate, this));
        }
        if (this._scale && (this.metadata.mm_x || this.metadata.geospatial || this._scale.scale)) {
            if (!this._scale.scale && !this.metadata.geospatial) {
                // convert mm to m.
                this._scale.scale = this.metadata.mm_x / 1000;
            }
            this.uiLayer = this.viewer.createLayer('ui');
            this.scaleWidget = this.uiLayer.createWidget('scale', this._scale);
        }

        this._postRender();

        this.trigger('g:imageRendered', this);
        return this;
    },

    /**
     * Extensible code that will be run after rendering but before the render
     * trigger.
     */
    _postRender: function () {
    },

    frameUpdate: function (frame) {
        if (this._frame === undefined) {
            // don't set up layers until the we access the first non-zero frame
            if (frame === 0) {
                return;
            }
            this._frame = 0;
            this._baseurl = this._layer.url();
            let quadLoaded = ((this._layer.setFrameQuad || {}).status || {}).loaded;
            if (!quadLoaded) {
                // use two layers to get smooth transitions until we load
                // background quads.
                this._layer2 = this.viewer.createLayer('osm', this._layer._options);
                this._layer2.moveDown();
                setFrameQuad((this._layer.setFrameQuad.status || {}).tileinfo, this._layer2, (this._layer.setFrameQuad.status || {}).options);
                this._layer2.setFrameQuad(0);
            }
        }
        this._nextframe = frame;
        if (frame !== this._frame && !this._updating) {
            this._frame = frame;
            this.trigger('g:imageFrameChanging', this, frame);
            let quadLoaded = ((this._layer.setFrameQuad || {}).status || {}).loaded;
            if (quadLoaded) {
                if (this._layer2) {
                    this.viewer.deleteLayer(this._layer2);
                    delete this._layer2;
                }
                this._layer.url(this.getFrameAndUrl().url);
                this._layer.setFrameQuad(frame);
                this._layer.frame = frame;
                this.trigger('g:imageFrameChanged', this, frame);
                return;
            }

            this._updating = true;
            this.viewer.onIdle(() => {
                this._layer2.url(this.getFrameAndUrl().url);
                this._layer2.setFrameQuad(frame);
                this._layer2.frame = frame;
                this.viewer.onIdle(() => {
                    this._layer.moveDown();
                    var ltemp = this._layer;
                    this._layer = this._layer2;
                    this._layer2 = ltemp;
                    this._updating = false;
                    this.trigger('g:imageFrameChanged', this, frame);
                    if (frame !== this._nextframe) {
                        this.frameUpdate(this._nextframe);
                    }
                });
            });
        }
    },

    getFrameAndUrl: function () {
        const frame = this._frame || 0;
        let url = this._baseurl || this._layer.url();
        if (frame) {
            url += (url.indexOf('?') >= 0 ? '&' : '?') + 'frame=' + frame;
        }
        return {
            frame: frame,
            url: url
        };
    },

    destroy: function () {
        if (this.viewer) {
            // make sure there is nothing left in the animation queue
            var queue = [];
            this.viewer.animationQueue(queue);
            queue.splice(0, queue.length);
            this.viewer.exit();
            this.viewer = null;
        }
        this.deleted = true;
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default GeojsImageViewerWidget;
