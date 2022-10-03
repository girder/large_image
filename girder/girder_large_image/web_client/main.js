import { registerPluginNamespace } from '@girder/core/pluginUtils';
import SearchFieldWidget from '@girder/core/views/widgets/SearchFieldWidget';

// import modules for side effects
import './routes';
import './eventStream';
import './views/fileList';
import './views/itemList';
import './views/itemView';
import './views/itemViewCodemirror';
import './views/imageViewerSelectWidget';

// expose symbols under girder.plugins
import * as largeImage from './index';
registerPluginNamespace('large_image', largeImage);

SearchFieldWidget.addMode(
    'li_metadata',
    ['item', 'folder'],
    'Metadata search',
    'You can search specific metadata keys by adding "key:<key name>" to your search.  Otherwise, all primary metadata keys are searched.  For example "key:quality good" would find any items or folders with a metadata key named quality (case sensitive) that contains the word "good" (case insensitive) anywhere in its value.'
);
