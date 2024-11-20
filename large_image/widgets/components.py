import ipyvuetify
import traitlets
from pathlib import Path


class DualInput(ipyvuetify.VuetifyTemplate):
    template_file = __file__, 'DualInput.vue'

    label = traitlets.Unicode(default_value='Value').tag(sync=True)
    currentValue = traitlets.Int(default_value=0).tag(sync=True)
    valueMax = traitlets.Int(default_value=10).tag(sync=True)
    sliderLabels = traitlets.List(default_value=[]).tag(sync=True)
    maxMerge = traitlets.Bool(default_value=False).tag(sync=True)

    def vue_updateValue(self, data=None):
        print(data, self.currentValue)

    def vue_updateMaxMerge(self, data=None):
        print(data, self.maxMerge)


class FrameSelector(ipyvuetify.VuetifyTemplate):
    template_file = __file__, 'FrameSelector.vue'

    itemId = traitlets.Unicode(default_value=None).tag(sync=True)
    imageMetadata = traitlets.Any(default_value=None).tag(sync=True)
    frameUpdate = traitlets.Any(default_value=None).tag(sync=True)
    liConfig = traitlets.Any(default_value=None).tag(sync=True)

    # https://stackoverflow.com/questions/70298569/ipyvuetify-cant-set-prop-to-static-text
    # components = traitlets.Dict(default_value={'aa': AA}).tag(sync=True, **v.VuetifyTemplate.class_component_serialization)
