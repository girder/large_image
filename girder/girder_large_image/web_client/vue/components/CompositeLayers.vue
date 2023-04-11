<script>
import { Chrome } from 'vue-color';
import { CHANNEL_COLORS, OTHER_COLORS } from '../colors'

export default {
    props: ['layers', 'layerMap', 'frameIndices'],
    emits: ['updateStyle'],
    components: {
        'color-picker': Chrome
    },
    data() {
        return {
            enabledLayers: this.layers,
            colorPickerShown: undefined,
            currentColorPickerRef: undefined,
            compositeLayerInfo: {},
        }
    },
    methods: {
        initializeLayerInfo() {
            const usedColors = []
            this.compositeLayerInfo = {}
            this.layers.forEach((layerName) => {
                this.compositeLayerInfo[layerName] = {
                    number: this.layerMap ?this.layerMap[layerName] :undefined,
                    enabled: true,
                    min: undefined,
                    max: undefined,
                }
            })
            Object.entries(CHANNEL_COLORS).forEach(([channelName, color]) => {
                if(this.layers.includes(channelName)){
                    this.compositeLayerInfo[channelName].falseColor = color
                    usedColors.push(color)
                }
            })
            this.layers.forEach((layerName) => {
                if (!this.compositeLayerInfo[layerName].falseColor) {
                    let chosenColor;
                    const unusedColors = OTHER_COLORS.filter(
                        (color) => !usedColors.includes(color)
                    )
                    if (unusedColors.length > 0) {
                        chosenColor = unusedColors[0]
                    } else {
                        chosenColor = OTHER_COLORS[Math.floor(Math.random() * OTHER_COLORS.length)];
                    }
                    this.compositeLayerInfo[layerName].falseColor = chosenColor
                    usedColors.push(chosenColor)
                }
            })
        },
        toggleColorPicker(layer) {
            this.colorPickerShown = layer
            if (this.colorPickerShown === undefined) {
                document.removeEventListener('click', this.documentClick);
                // Only update style when picker is closed
                this.updateStyle()
            }
            else {
                this.currentColorPickerRef = document.getElementById(layer+'_picker')
                document.addEventListener('click', this.documentClick);
            }
        },
        documentClick(e) {
            const picker = this.currentColorPickerRef;
            if (picker && picker !== e.target && !picker.contains(e.target)) {
                this.toggleColorPicker(undefined);
            }
        },
        updateLayerColor(layer, swatch) {
            this.compositeLayerInfo[layer].falseColor = swatch.hex;
        },
        updateLayerMin(event, layer) {
            const newVal = event.target.value;
            const newMinVal = parseFloat(newVal);
            this.compositeLayerInfo[layer].min = newMinVal;
            this.updateStyle();
        },
        updateLayerMax(event, layer) {
            const newVal = event.target.valueAsNumber;
            const newMaxVal = parseFloat(newVal);
            this.compositeLayerInfo[layer].max = newMaxVal;
            this.updateStyle();
        },
        updateActiveLayers() {
            this.layers.forEach((layer) => {
                this.compositeLayerInfo[layer].enabled = this.enabledLayers.includes(layer);
            })
            this.updateStyle();
        },
        updateStyle() {
            const activeLayers = Object.values(
                this.compositeLayerInfo
            ).filter((layer) => layer.enabled);
            const styleArray = []
            activeLayers.forEach((layer) => {
                // TODO: what should each style entry look like for band compositing?
                const styleEntry = {};
                if (layer.number) {
                    styleEntry['frameDelta'] = layer.number
                }
                if (layer.falseColor) {
                    styleEntry['palette'] = layer.falseColor;
                }
                if (layer.min) {
                    styleEntry['min'] = layer.min;
                }
                if (layer.max) {
                    styleEntry['max'] = layer.max;
                }
                styleArray.push(styleEntry);
            });
            this.$emit('updateStyle', {bands: styleArray});
        },
    },
    mounted() {
        this.initializeLayerInfo()
        this.updateStyle()
    }
}
</script>

<template>
    <div class="table-container">
        <table id="composite-layer-table" class="table table-condensed">
            <thead>
                <tr>
                    <th class="layer-col">Layer</th>
                    <th class="enabled-col">Enabled?</th>
                    <th class="color-col">Color</th>
                    <th class="precision-col">Min</th>
                    <th class="precision-col">Max</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="layer in layers.filter(c => compositeLayerInfo[c] !== undefined)"
                    :key="layer"
                >
                    <td>{{ layer }}</td>
                    <td>
                        <input
                            type="checkbox"
                            :value="layer"
                            v-model="enabledLayers"
                            @change="updateActiveLayers"
                        >
                    </td>
                    <td :id="layer+'_picker'">
                        <span
                            class="current-color"
                            :style="{ 'background-color': compositeLayerInfo[layer].falseColor }"
                            @click="() => toggleColorPicker(layer)"
                        />
                        <color-picker
                            class="picker-offset"
                            v-if="colorPickerShown === layer"
                            :value="compositeLayerInfo[layer].falseColor"
                            @input="(swatch) => {updateLayerColor(layer, swatch)}"
                        />
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            :value="compositeLayerInfo[layer].min"
                            @change.prevent="(event) => updateLayerMin(event, layer)"
                        >
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            :value="compositeLayerInfo[layer].max"
                            @change.prevent="(event) => updateLayerMax(event, layer)"
                        >
                    </td>
                    <td></td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<style scoped>
.current-color {
    display: inline-block;
    width: 50px;
    height: 20px;
    background-color: #000;
    cursor: pointer;
}
.picker-offset {
    position: absolute;
    z-index: 100;
    margin-left: 50px;
}
.table-container {
    max-height: 700px;
    overflow: scroll;
}
.table-container input {
    max-width: 70px;
}
</style>
