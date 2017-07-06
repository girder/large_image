import events from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

import ConfigView from './views/configView';

exposePluginConfig('large_image', 'plugins/large_image/config');

router.route('plugins/large_image/config', 'largeImageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
