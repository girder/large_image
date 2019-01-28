import events from '@girder/core/events';
import router from '@girder/core/router';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

import ConfigView from './views/configView';

exposePluginConfig('large_image', 'plugins/large_image/config');

router.route('plugins/large_image/config', 'largeImageConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
