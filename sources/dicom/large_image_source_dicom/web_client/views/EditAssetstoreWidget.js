import EditAssetstoreWidget from '@girder/core/views/widgets/EditAssetstoreWidget';
import { AssetstoreType } from '@girder/core/constants';
import { wrap } from '@girder/core/utilities/PluginUtils';

import DWASEditFieldsTemplate from '../templates/dicomwebAssetstoreEditFields.pug';

/**
 * Adds DICOMweb-specific fields to the edit dialog.
 */
wrap(EditAssetstoreWidget, 'render', function (render) {
    render.call(this);

    if (this.model.get('type') === AssetstoreType.DICOMWEB) {
        this.$('.g-assetstore-form-fields').append(
            DWASEditFieldsTemplate({
                assetstore: this.model
            })
        );
    }
    return this;
});

EditAssetstoreWidget.prototype.fieldsMap[AssetstoreType.DICOMWEB] = {
    get: function () {
        return {
            url: this.$('#g-edit-dwas-url').val(),
            qido_prefix: this.$('#g-edit-dwas-qido-prefix').val(),
            wado_prefix: this.$('#g-edit-dwas-wado-prefix').val(),
            auth_type: this.$('#g-edit-dwas-auth-type').val()
        };
    },
    set: function () {
        const dwInfo = this.model.get('dicomweb_meta');
        this.$('#g-edit-dwas-url').val(dwInfo.url);
        this.$('#g-edit-dwas-qido-prefix').val(dwInfo.qido_prefix);
        this.$('#g-edit-dwas-wado-prefix').val(dwInfo.wado_prefix);
        this.$('#g-edit-dwas-auth-type').val(dwInfo.auth_type);
    }
};
