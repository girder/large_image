import { registerPluginNamespace } from 'girder/pluginUtils';

// import modules for side effects
import './views/imageViewerSelectWidget';

// expose symbols under girder.plugins
import * as largeImageAnnotation from './index';
registerPluginNamespace('large_image_annotation', largeImageAnnotation);
