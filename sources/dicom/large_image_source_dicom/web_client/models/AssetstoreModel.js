import AssetstoreModel from '@girder/core/models/AssetstoreModel';
import { restRequest } from '@girder/core/rest';

/**
 * Extends the core assetstore model to add DICOMweb-specific functionality.
 */
AssetstoreModel.prototype.dicomwebImport = function (params) {
    return restRequest({
        url: 'dicomweb_assetstore/' + this.get('_id') + '/import',
        type: 'POST',
        data: params,
        error: null
    }).done(() => {
        this.trigger('g:imported');
    }).fail((err) => {
        this.trigger('g:error', err);
    });
};

export default AssetstoreModel;
