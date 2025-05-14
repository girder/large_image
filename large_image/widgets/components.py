import json
from pathlib import Path
from typing import Callable, Union

import ipyvue
import traitlets

from ipywidgets import DOMWidget, register

parent = Path(__file__).parent
with open(parent / 'colors.json') as f:
    colors_data = json.load(f)
with open(parent / 'DualInput.vue') as f:
    dual_input = f.read()
with open(parent / 'CompositeLayers.vue') as f:
    composite_layers = f.read()
with open(parent / 'HistogramEditor.vue') as f:
    histogram_editor = f.read()

@register
class HistogramEditor(DOMWidget):
    _view_name = traitlets.Unicode('histogram-editor').tag(sync=True)
    _view_module = traitlets.Unicode('histogram_editor').tag(sync=True)
    _view_module_version = traitlets.Unicode('0.1.0').tag(sync=True)

    name = traitlets.Unicode('histogram-editor').tag(sync=True)
    component = traitlets.Unicode(histogram_editor).tag(sync=True)


class FrameSelector(ipyvue.VueTemplate):  # type: ignore
    template_file = __file__, 'FrameSelector.vue'

    itemId = traitlets.Int(allow_none=True).tag(sync=True)
    imageMetadata = traitlets.Dict().tag(sync=True)
    currentFrame = traitlets.Int(default_value=0).tag(sync=True)
    colors = traitlets.Dict(colors_data).tag(sync=True)
    frameHistograms = traitlets.Dict({}).tag(sync=True)

    updateFrameCallback: Union[Callable, None] = None
    getFrameHistogram: Union[Callable, None] = None

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

print('test updated 5')
