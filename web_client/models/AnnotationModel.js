import Model from 'girder/models/Model';

import convert from '../annotations/convert';

export default Model.extend({
    resourceName: 'annotation',

    /**
     * Return the annotation as a geojson FeatureCollection.
     *
     * WARNING: Not all annotations are representable in geojson.
     * Annotation types that cannot be converted will be ignored.
     */
    geojson() {
        const json = this.get('annotation') || {};
        const elements = json.elements || [];
        return convert(elements);
    }
});
