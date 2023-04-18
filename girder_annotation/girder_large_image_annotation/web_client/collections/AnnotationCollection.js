import Collection from '@girder/core/collections/Collection';
import {SORT_DESC} from '@girder/core/constants';

import AnnotationModel from '../models/AnnotationModel';

export default Collection.extend({
    resourceName: 'annotation',
    model: AnnotationModel,
    // this is a large number so that we probably never need to page
    // annotations.
    pageLimit: 10000,
    sortField: 'created',
    sortDir: SORT_DESC
});
