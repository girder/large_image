import events from 'girder/events';
import router from 'girder/router';
import { exposePluginConfig } from 'girder/utilities/PluginUtils';

exposePluginConfig('large_image', 'plugins/large_image/config');

import ConfigView from './views/configView';
router.route('plugins/large_image/config', 'largeImageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
