import json
from pathlib import Path
from typing import Callable, Union

import ipyvue
import traitlets

parent = Path(__file__).parent
colors_file = parent / 'colors.json'
with open(colors_file) as f:
    colors_data = json.load(f)

ipyvue.register_component_from_file(None, 'dual-input', parent / 'DualInput.vue')
ipyvue.register_component_from_file(None, 'composite-layers', parent / 'CompositeLayers.vue')
ipyvue.register_component_from_file(None, 'histogram-editor', parent / 'HistogramEditor.vue')


class FrameSelector(ipyvue.VueTemplate):  # type: ignore
    template_file = __file__, 'FrameSelector.vue'

    itemId = traitlets.Int(allow_none=True).tag(sync=True)
    imageMetadata = traitlets.Dict().tag(sync=True)
    currentFrame = traitlets.Int(default_value=0).tag(sync=True)
    colors = traitlets.Dict(colors_data).tag(sync=True)
    frameHistograms = traitlets.Dict({}).tag(sync=True)

    updateFrameCallback: Union[Callable, None] = None
    getFrameHistogram: Union[Callable, None] = None

    def vue_frameUpdate(self, data=None):
        frame = int(data.get('frame', 0))
        style = data.get('style', {})
        if self.updateFrameCallback is not None:
            self.updateFrameCallback(frame, style)

    def vue_getFrameHistogram(self, params=None):
        if self.getFrameHistogram is not None:
            self.getFrameHistogram(params)
