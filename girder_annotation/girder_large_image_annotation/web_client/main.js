import { registerPluginNamespace } from '@girder/core/pluginUtils';

// import modules for side effects
import './routes';
import './views/imageViewerSelectWidget';

// expose symbols under girder.plugins
import * as largeImageAnnotation from './index';
registerPluginNamespace('large_image_annotation', largeImageAnnotation);
