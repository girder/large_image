import { wrap } from 'girder/utilities/PluginUtils';

import CheckedMenuWidget from 'girder/views/widgets/CheckedMenuWidget';
import HierarchyWidget from 'girder/views/widgets/HierarchyWidget';

import CheckedMenuExtensionTemplate from '../templates/checkedMenuWidget.pug';

var _copyWithAnnotations = false;

wrap(CheckedMenuWidget, 'render', function (render) {
    render.call(this);

    if (this.pickedCopyAllowed) {
        this.$el.find('.g-copy-picked').closest('li').after(
            CheckedMenuExtensionTemplate({pickedCopyAllowed: this.pickedCopyAllowed})
        );
    }
    return this;
});

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);
    if (!this.copyPickedResourcesAnnotations) {
        this.copyPickedResourcesAnnotations = () => {
            _copyWithAnnotations = true;
            this.copyPickedResources();
            _copyWithAnnotations = false;
        };
        this.events['click a.g-copy-picked-annotations'] = this.copyPickedResourcesAnnotations;
        this.delegateEvents();
    }
    return this;
});

/* The checked menu widget doesn't expose enough to do this easily, so we set
 * a global flag and modify the request on the way through.  This should be
 * safe, as it is done within a single javascript time slice. */
$.ajaxPrefilter((options, originalOptions, jqXHR) => {
    if (_copyWithAnnotations === true && options.url === 'api/v1/resource/copy') {
        options.data += '&copyAnnotations=true';
    }
});
