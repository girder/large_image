import Backbone from 'backbone';

import ElementModel from '../models/ElementModel';

export default Backbone.Collection.extend({
    model: ElementModel,
    comparator: undefined
});
