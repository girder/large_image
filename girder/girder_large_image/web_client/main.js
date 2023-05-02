import _ from 'underscore';

import * as rest from '@girder/core/rest';
import {registerPluginNamespace} from '@girder/core/pluginUtils';
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

/* eslint-disable no-import-assign */
rest.restRequest = _.wrap(rest.restRequest, (restRequest, opts) => {
    /* Automatically convert long GET and PUT queries to POST queries */
    try {
        if ((!opts.method || opts.method === 'GET' || opts.method === 'PUT') && opts.data && !opts.contentType) {
            if (JSON.stringify(opts.data).length > 1536) {
                opts.headers = opts.header || {};
                opts.headers['X-HTTP-Method-Override'] = opts.method || 'GET';
                opts.method = 'POST';
            }
        }
    } catch (err) { }
    return restRequest(opts);
});
/* eslint-enable no-import-assign */

SearchFieldWidget.addMode(
    'li_metadata',
    ['item', 'folder'],
    'Metadata search',
    'You can search specific metadata keys by adding "key:<key name>" to your search.  Otherwise, all primary metadata keys are searched.  For example "key:quality good" would find any items or folders with a metadata key named quality (case sensitive) that contains the word "good" (case insensitive) anywhere in its value.'
);
