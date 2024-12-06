import ipyvue
import traitlets
from pathlib import Path
from typing import Callable, List, Union


class DualInput(ipyvue.VueTemplate):  # type: ignore
    template_file = __file__, 'DualInput.vue'

    label = traitlets.Unicode(default_value='Value').tag(sync=True)
    currentValue = traitlets.Int(default_value=0).tag(sync=True)
    valueMax = traitlets.Int(default_value=10).tag(sync=True)
    sliderLabels = traitlets.List([""], allow_none=True).tag(sync=True)
    maxMerge = traitlets.Bool(default_value=False).tag(sync=True)

class FrameSelector(ipyvue.VueTemplate ):  # type: ignore
    template_file = __file__, 'FrameSelector.vue'
    components = traitlets.Dict({
        'DualInput': DualInput().template.template,
    }).tag(sync=True)

    imageMetadata = traitlets.Dict().tag(sync=True)
    currentFrame = traitlets.Int(default_value=0).tag(sync=True)
    updateFrameCallback: Union[Callable, None] = None

    def vue_frameUpdate(self, data=None):
        if self.updateFrameCallback is not None:
            self.updateFrameCallback(data)
