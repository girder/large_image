import { registerPluginNamespace } from 'girder/pluginUtils';

// import modules for side effects
import './routes';
import './views/fileList';
import './views/itemList';
import './views/imageViewerSelectWidget';

// expose symbols under girder.plugins
import * as largeImage from 'girder_plugins/large_image';
registerPluginNamespace('large_image', largeImage);
