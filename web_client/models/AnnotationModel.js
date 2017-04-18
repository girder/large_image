import _ from 'underscore';
import Model from 'girder/models/Model';

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
     * Return a backbone collection containing the annotation elements.
     */
    elements() {
        return this._elements;
    }
});
