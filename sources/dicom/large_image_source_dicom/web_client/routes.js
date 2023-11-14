import router from '@girder/core/router';
import events from '@girder/core/events';

import AssetstoreModel from './models/AssetstoreModel';
import DICOMwebImportView from './views/DICOMwebImportView';

router.route('dicomweb_assetstore/:id/import', 'dwasImport', function (id) {
    // Fetch the assetstore by id, then render the view.
    const assetstore = new AssetstoreModel({ _id: id });
    assetstore.once('g:fetched', function () {
        events.trigger('g:navigateTo', DICOMwebImportView, {
            model: assetstore
        });
    }).once('g:error', function () {
        router.navigate('assetstores', { trigger: true });
    }).fetch();
});
