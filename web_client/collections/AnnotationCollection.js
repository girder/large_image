import Collection from 'girder/collections/Collection';
import { SORT_DESC } from 'girder/constants';

import AnnotationModel from '../models/AnnotationModel';

export default Collection.extend({
    resourceName: 'annotation',
    model: AnnotationModel,
    pageLimit: 100,
    sortField: 'created',
    sortDir: SORT_DESC
});
