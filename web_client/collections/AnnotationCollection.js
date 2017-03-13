import Collection from 'girder/collections/Collection';
import AnnotationModel from '../models/AnnotationModel';

export default Collection.extend({
    resourceName: 'annotation',
    model: AnnotationModel,
    pageLimit: 100
});
