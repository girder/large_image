import events from '@girder/core/events';
import router from '@girder/core/router';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

import ConfigView from './views/configView';

exposePluginConfig('large_image_annotation', 'plugins/large_image_annotation/config');

router.route('plugins/large_image_annotation/config', 'largeImageAnnotationConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});
