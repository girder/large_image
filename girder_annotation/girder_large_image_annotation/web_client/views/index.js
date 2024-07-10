
import ConfigView from './configView';
import HierarchyWidget from './hierarchyWidget';
import './imageViewerSelectWidget';
import ItemListWidget from './itemList';
import ImageViewerWidgetAnnotationExtension from './imageViewerWidget/base';
import * as extensions from './imageViewerWidget';

const viewers = {};

for (var key in girder.plugins.large_image.views.imageViewerWidget) {
    viewers[key] = girder.plugins.large_image.views.imageViewerWidget[key].extend(ImageViewerWidgetAnnotationExtension);

    if (extensions[key]) {
        viewers[key] = extensions[key](viewers[key]);
    }
}

export {
    ConfigView,
    HierarchyWidget,
    ItemListWidget,
    viewers as ViewerWidget
};
