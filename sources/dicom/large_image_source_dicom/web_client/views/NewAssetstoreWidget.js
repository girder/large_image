import NewAssetstoreWidget from '@girder/core/views/widgets/NewAssetstoreWidget';
import { AssetstoreType } from '@girder/core/constants';
import { wrap } from '@girder/core/utilities/PluginUtils';

import DWASCreateTemplate from '../templates/dicomwebAssetstoreCreate.pug';

import authOptions from './AuthOptions';

/**
 * Add UI for creating new DICOMweb assetstore.
 */
wrap(NewAssetstoreWidget, 'render', function (render) {
    render.call(this);

    this.$('#g-assetstore-accordion').append(DWASCreateTemplate({
        authOptions
    }));
    return this;
});

NewAssetstoreWidget.prototype.events['submit #g-new-dwas-form'] = function (e) {
    this.createAssetstore(e, this.$('#g-new-dwas-error'), {
        type: AssetstoreType.DICOMWEB,
        name: this.$('#g-new-dwas-name').val(),
        url: this.$('#g-new-dwas-url').val(),
        qido_prefix: this.$('#g-new-dwas-qido-prefix').val(),
        wado_prefix: this.$('#g-new-dwas-wado-prefix').val(),
        auth_type: this.$('#g-new-dwas-auth-type').val(),
        auth_token: this.$('#g-new-dwas-auth-token').val()
    });
};
