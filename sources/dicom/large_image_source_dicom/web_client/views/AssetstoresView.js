import _ from 'underscore';

import AssetstoresView from '@girder/core/views/body/AssetstoresView';
import { AssetstoreType } from '@girder/core/constants';
import { wrap } from '@girder/core/utilities/PluginUtils';

import DWASImportButtonTemplate from '../templates/dicomwebAssetstoreImportButton.pug';

/**
 * Adds DICOMweb-specific info and an import button to the assetstore list
 * view.
 */
wrap(AssetstoresView, 'render', function (render) {
    render.call(this);

    const selector = '.g-assetstore-info-section[assetstore-type="' + AssetstoreType.DICOMWEB + '"]';

    _.each(this.$(selector), function (el) {
        const $el = this.$(el);
        const assetstore = this.collection.get($el.attr('cid'));

        $el.parent().find('.g-assetstore-buttons').append(
            DWASImportButtonTemplate({
                assetstore
            })
        );
    }, this);

    this.$('.g-dwas-import-button').tooltip({
        delay: 100
    });
    return this;
});
