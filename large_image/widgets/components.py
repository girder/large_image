import json
from pathlib import Path
from typing import Callable, Union

import ipyvue
import traitlets

parent = Path(__file__).parent
colors_file = parent / 'colors.json'
with open(colors_file) as f:
    colors_data = json.load(f)
dual_input_template_file = parent / 'DualInput.vue'
with open(dual_input_template_file) as f:
    dual_input_template = f.read()
composite_layers_template_file = parent / 'CompositeLayers.vue'
with open(composite_layers_template_file) as f:
    composite_layers_template = f.read()
histogram_editor_template_file = parent / 'HistogramEditor.vue'
with open(histogram_editor_template_file) as f:
    histogram_editor_template = f.read()

ipyvue.register_component_from_file(None, 'dual-input', dual_input_template_file)
ipyvue.register_component_from_file(None, 'composite-layers', composite_layers_template_file)
ipyvue.register_component_from_file(None, 'histogram-editor', histogram_editor_template_file)


class FrameSelector(ipyvue.VueTemplate):  # type: ignore
    template_file = __file__, 'FrameSelector.vue'

    itemId = traitlets.Int(allow_none=True).tag(sync=True)
    imageMetadata = traitlets.Dict().tag(sync=True)
    currentFrame = traitlets.Int(default_value=0).tag(sync=True)
    colors = traitlets.Dict(colors_data).tag(sync=True)
    frameHistograms = traitlets.Dict({}).tag(sync=True)

    updateFrameCallback: Union[Callable, None] = None
    getFrameHistogram: Union[Callable, None] = None

    debug = traitlets.Unicode().tag(sync=True)

    def vue_frameUpdate(self, data=None):
        frame = int(data.get('frame', 0))
        style = data.get('style', {})
        if self.updateFrameCallback is not None:
            self.updateFrameCallback(frame, style)

    def vue_getFrameHistogram(self, params=None):
        if self.getFrameHistogram is not None:
            self.getFrameHistogram(params)
