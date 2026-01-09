import json
from collections.abc import Callable
from pathlib import Path

import ipyvue
import traitlets

parent = Path(__file__).parent
with open(parent / 'colors.json') as f:
    colors_data = json.load(f)
with open(parent / 'DualInput.vue') as f:
    dual_input = f.read()
with open(parent / 'CompositeLayers.vue') as f:
    composite_layers = f.read()
with open(parent / 'HistogramEditor.vue') as f:
    histogram_editor = f.read()

ipyvue.register_component_from_string('histogram-editor', histogram_editor)


class FrameSelector(ipyvue.VueTemplate):  # type: ignore
    template_file = __file__, 'FrameSelector.vue'

    itemId = traitlets.Int(allow_none=True).tag(sync=True)
    imageMetadata = traitlets.Dict().tag(sync=True)
    currentFrame = traitlets.Int(default_value=0).tag(sync=True)
    colors = traitlets.Dict(colors_data).tag(sync=True)
    frameHistograms = traitlets.Dict({}).tag(sync=True)

    updateFrameCallback: Callable | None = None
    getFrameHistogram: Callable | None = None

    # register_component_from_file function does not work in Google Colab;
    # register child components from strings instead
    components = traitlets.Dict({
        'dual-input': dual_input,
        'composite-layers': composite_layers,
    }).tag(sync=True)

    def vue_frameUpdate(self, data=None):
        frame = int(data.get('frame', 0))
        style = data.get('style', {})
        if self.updateFrameCallback is not None:
            self.updateFrameCallback(frame, style)

    def vue_getFrameHistogram(self, params=None):
        if self.getFrameHistogram is not None:
            self.getFrameHistogram(params)
