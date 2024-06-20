
import ConfigView from './configView';
import HierarchyWidget from './hierarchyWidget';
import './imageViewerSelectWidget';
import ItemListWidget from './itemList';
import ImageViewerWidgetAnnotationExtension from './imageViewerWidget/base';
import * as extensions from './imageViewerWidget';

const events = girder.events;
const viewers = {};

events.on('g:appload.before', function () {
    const _ = girder._;

    for (var key in girder.plugins.large_image.views.imageViewerWidget) {
        viewers[key] = girder.plugins.large_image.views.imageViewerWidget[key];

        _.extend(viewers[key], ImageViewerWidgetAnnotationExtension);
        if (extensions[key]) {
            const extension = extensions[key](viewers[key]);
            _.extend(viewers[key], extension);
        }
    }
});

export {
    ConfigView,
    HierarchyWidget,
    ItemListWidget,
    viewers as ViewerWidget
};
