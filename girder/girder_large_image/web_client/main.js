import { registerPluginNamespace } from '@girder/core/pluginUtils';

// import modules for side effects
import './routes';
import './views/fileList';
import './views/itemList';
import './views/itemView';
import './views/imageViewerSelectWidget';

// expose symbols under girder.plugins
import * as largeImage from './index';
registerPluginNamespace('large_image', largeImage);
