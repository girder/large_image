import * as viewers from '@girder/large_image/views/imageViewerWidget';

import ConfigView from './configView';
import ImageViewerSelectWidget from './imageViewerSelectWidget';
import ImageViewerWidgetAnnotationExtension from './imageViewerWidget/base';
import * as extensions from './imageViewerWidget';

for (var key in viewers) {
    viewers[key] = viewers[key].extend(ImageViewerWidgetAnnotationExtension);
    if (extensions[key]) {
        viewers[key] = extensions[key](viewers[key]);
    }
}

export {
    ConfigView,
    ImageViewerSelectWidget
};
