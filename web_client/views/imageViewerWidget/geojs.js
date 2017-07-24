import _ from 'underscore';
import Backbone from 'backbone';
// Import hammerjs for geojs touch events
import Hammer from 'hammerjs';

import { staticRoot } from 'girder/rest';
import events from 'girder/events';

import ImageViewerWidget from './base';
import convertAnnotation from '../../annotations/geojs/convert';

window.hammerjs = Hammer;

/**
 * Generate a new "random" element id (24 random 16 digits).
 */
function guid() {
    function s4() {
        return Math.floor((1 + Math.random()) * 0x10000)
            .toString(16)
            .substring(1);
    }
    return s4() + s4() + s4() + s4() + s4() + s4();
}

var GeojsImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        this._layers = {};
        this.listenTo(events, 's:widgetDrawRegion', this.drawRegion);
        this.listenTo(events, 'g:startDrawMode', this.startDrawMode);
        this._hoverEvents = settings.hoverEvents;

        $.when(
            ImageViewerWidget.prototype.initialize.call(this, settings),
            $.ajax({  // like $.getScript, but allow caching
                url: staticRoot + '/built/plugins/large_image/extra/geojs.js',
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

        var w = this.sizeX, h = this.sizeY;
        var params = geo.util.pixelCoordinateParams(
            this.el, w, h, this.tileWidth, this.tileHeight);
        params.layer.useCredentials = true;
        params.layer.url = this._getTileUrl('{z}', '{x}', '{y}');
        this.viewer = geo.map(params.map);
        this.viewer.createLayer('osm', params.layer);
        this.annotationLayer = this.viewer.createLayer('annotation', {
            annotations: ['point', 'line', 'rectangle', 'polygon']
        });

        this.trigger('g:imageRendered', this);
        return this;
    },

    destroy: function () {
        if (this.viewer) {
            this.viewer.exit();
            this.viewer = null;
        }
        this.deleted = true;
        ImageViewerWidget.prototype.destroy.call(this);
    },

    /**
     * Render an annotation model on the image.  Currently,
     * this is limited to annotation types that can be directly
     * converted into geojson primatives.
     *
     * Internally, this generates a new feature layer for the
     * annotation that is referenced by the annotation id.
     * All "elements" contained inside this annotations are
     * drawn in the referenced layer.
     *
     * @param {AnnotationModel} annotation
     * @param {object} [options]
     * @param {boolean} [options.fetch=true]
     *   Enable fetching the annotation from the server, including paging
     *   the results.  If false, it is assumed the elements already
     *   exist on the annotation object.  This is useful for temporarily
     *   showing annotations that are not propagated to the server.
     */
    drawAnnotation: function (annotation, options) {
        var geo = window.geo;
        options = _.defaults(options || {}, {fetch: true});
        var geojson = annotation.geojson();
        var layer;
        if (_.has(this._layers, annotation.id)) {
            layer = this._layers[annotation.id];
            layer.clear();
        } else {
            layer = this.viewer.createLayer('feature', {
                features: ['point', 'line', 'polygon']
            });
            this._layers[annotation.id] = layer;

            var setBounds = () => {
                var zoom = this.viewer.zoom(),
                    bounds = this.viewer.bounds(),
                    zoomRange = this.viewer.zoomRange();
                if (annotation.setView) {
                    annotation.setView(bounds, zoom, zoomRange.max);
                }
            };

            if (options.fetch) {
                if (layer.geoOn) {
                    layer.geoOn(window.geo.event.pan, setBounds);
                }

                annotation.off('g:fetched', null, this).on('g:fetched', () => {
                    // Trigger an event indicating to the listener that
                    // mouseover states should reset.
                    this.trigger(
                        'g:mouseResetAnnotation',
                        annotation
                    );
                    this.drawAnnotation(annotation);
                }, this);
                setBounds();
            }
        }
        window.geo.createFileReader('jsonReader', {layer})
            .read(geojson, (features) => {
                _.each(features || [], (feature) => {
                    var events = geo.event.feature;

                    feature.selectionAPI(this._hoverEvents);

                    feature.geoOn(
                        [
                            events.mouseclick,
                            events.mouseoff,
                            events.mouseon,
                            events.mouseover,
                            events.mouseout
                        ],
                        (evt) => this._onMouseFeature(evt)
                    );
                });
                this.viewer.draw();
            });
    },

    /**
     * Remove an annotation from the image.  This simply
     * finds a layer with the given id and removes it because
     * each annotation is contained in its own layer.  If
     * the annotation is not drawn, this is a noop.
     *
     * @param {AnnotationModel} annotation
     */
    removeAnnotation: function (annotation) {
        annotation.off('g:fetched', null, this);
        // Trigger an event indicating to the listener that
        // mouseover states should reset.
        this.trigger(
            'g:mouseResetAnnotation',
            annotation
        );
        var layer = this._layers[annotation.id];
        if (layer) {
            delete this._layers[annotation.id];
            this.viewer.deleteLayer(layer);
        }
    },

    /**
     * Set the image interaction mode to region drawing mode.  This
     * method takes an optional `model` argument where the region will
     * be stored when created by the user.  In any case, this method
     * returns a promise that resolves to an array defining the region:
     *   [ left, top, width, height ]
     *
     * @param {Backbone.Model} [model] A model to set the region to
     * @returns {Promise}
     */
    drawRegion: function (model) {
        model = model || new Backbone.Model();
        return this.startDrawMode('rectangle', {trigger: false}).then((elements) => {
            /*
             * Strictly speaking, the rectangle drawn here could be rotated, but
             * for simplicity we will set the region model assuming it is not.
             * To be more precise, we could expand the region to contain the
             * whole rotated rectangle.  A better solution would be to add
             * a draw parameter to geojs that draws a rectangle aligned with
             * the image coordinates.
             */
            var element = elements[0];
            var width = Math.round(element.width);
            var height = Math.round(element.height);
            var left = Math.round(element.center[0] - element.width / 2);
            var top = Math.round(element.center[1] - element.height / 2);

            model.set('value', [
                left, top, width, height
            ], {trigger: true});

            return model.get('value');
        });
    },

    /**
     * Set the image interaction mode to draw the given type of annotation.
     *
     * @param {string} type An annotation type
     * @param {object} [options]
     * @param {boolean} [options.trigger=true]
     *      Trigger a global event after creating each annotation element.
     * @returns {Promise}
     *      Resolves to an array of generated annotation elements.
     */
    startDrawMode: function (type, options) {
        var layer = this.annotationLayer;
        var elements = [];
        var annotations = [];

        layer.mode(null);
        layer.geoOff(window.geo.event.annotation.state);
        layer.removeAllAnnotations();
        return new Promise((resolve) => {
            var element;

            options = _.defaults(options || {}, {trigger: true});
            layer.geoOn(
                window.geo.event.annotation.state,
                (evt) => {
                    element = convertAnnotation(evt.annotation);
                    if (!element.id) {
                        element.id = guid();
                    }
                    elements.push(element);
                    annotations.push(evt.annotation);

                    if (options.trigger) {
                        events.trigger('g:annotationCreated', element, evt.annotation);
                    }

                    layer.removeAllAnnotations();
                    layer.geoOff(window.geo.event.annotation.state);
                    resolve(elements, annotations);
                }
            );
            layer.mode(type);
        });
    },

    _setEventTypes: function () {
        var events = window.geo.event.feature;
        this._eventTypes = {
            [events.mouseclick]: 'g:mouseClickAnnotation',
            [events.mouseoff]: 'g:mouseOffAnnotation',
            [events.mouseon]: 'g:mouseOnAnnotation',
            [events.mouseover]: 'g:mouseOverAnnotation',
            [events.mouseout]: 'g:mouseOutAnnotation'
        };
    },

    _onMouseFeature: function (evt) {
        var properties = evt.data.properties || {};
        var eventType;

        if (!this._eventTypes) {
            this._setEventTypes();
        }

        if (properties.element && properties.annotation) {
            eventType = this._eventTypes[evt.event];

            if (eventType) {
                this.trigger(
                    eventType,
                    properties.element,
                    properties.annotation
                );
            }
        }
    }
});

export default GeojsImageViewerWidget;
