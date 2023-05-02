<script>
import { Chrome } from 'vue-color';
import { CHANNEL_COLORS, OTHER_COLORS } from '../colors'

export default {
    props: ['layers', 'layerMap'],
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
    watch: {
        layers() {
            this.enabledLayers = this.layers
            this.initializeLayerInfo()
            this.updateStyle()
        }
    },
    methods: {
        initializeLayerInfo() {
            const usedColors = []
            this.compositeLayerInfo = {}
            this.layers.forEach((layerName, i) => {
                this.compositeLayerInfo[layerName] = {
                    framedelta: this.layerMap ?this.layerMap[layerName] :undefined,
                    band: this.layerMap ? undefined : i + 1,  // expected 1-based index
                    enabled: true,
                    min: undefined,
                    max: undefined,
                }
            })
            Object.entries(CHANNEL_COLORS).forEach(([channelName, color]) => {
                if(this.layers.includes(channelName)){
                    this.compositeLayerInfo[channelName].palette = color
                    usedColors.push(color)
                }
            })
            this.layers.forEach((layerName) => {
                if (!this.compositeLayerInfo[layerName].palette) {
                    let chosenColor;
                    const unusedColors = OTHER_COLORS.filter(
                        (color) => !usedColors.includes(color)
                    )
                    if (unusedColors.length > 0) {
                        chosenColor = unusedColors[0]
                    } else {
                        chosenColor = OTHER_COLORS[Math.floor(Math.random() * OTHER_COLORS.length)];
                    }
                    this.compositeLayerInfo[layerName].palette = chosenColor
                    usedColors.push(chosenColor)
                }
            })
        },
        toggleEnableAll() {
            if (this.enabledLayers !== this.layers) {
                this.enabledLayers = this.layers
            } else {
                this.enabledLayers = []
            }
            this.updateActiveLayers()
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
            this.compositeLayerInfo[layer].palette = swatch.hex;
        },
        updateLayerMin(event, layer) {
            const newVal = event.target.valueAsNumber;
            const newMinVal = Number.isFinite(newVal) ? parseFloat(newVal) : undefined;
            this.compositeLayerInfo[layer].min = newMinVal;
            this.updateStyle();
        },
        updateLayerMax(event, layer) {
            const newVal = event.target.valueAsNumber;
            const newMaxVal = Number.isFinite(newVal) ? parseFloat(newVal) : undefined;
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
                const styleEntry = Object.assign({}, layer);
                delete styleEntry.enabled
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
            <thead class="table-header">
                <tr>
                    <th class="layer-col">Layer</th>
                    <th class="enabled-col">
                        <input
                            type="checkbox"
                            :checked="enabledLayers === layers"
                            @input="toggleEnableAll"
                        >
                        Enable
                    </th>
                    <th class="color-col">Color</th>
                    <th class="precision-col">Min</th>
                    <th class="precision-col">Max</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="[layer, layerInfo] in Object.entries(compositeLayerInfo).filter(([, layerInfo]) => layerInfo)"
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
                            :style="{ 'background-color': layerInfo.palette }"
                            @click="() => toggleColorPicker(layer)"
                        />
                        <color-picker
                            class="picker-offset"
                            :disableAlpha="true"
                            v-if="colorPickerShown === layer"
                            :value="layerInfo.palette"
                            @input="(swatch) => {updateLayerColor(layer, swatch)}"
                        />
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="65535"
                            :value="layerInfo.min"
                            @change.prevent="(event) => updateLayerMin(event, layer)"
                        >
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="65535"
                            :value="layerInfo.max"
                            @change.prevent="(event) => updateLayerMax(event, layer)"
                        >
                    </td>
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
.table-header {
    position: sticky;
    top: 0px;
    background-color: white;
    z-index: 2;
}
.table-container {
    overflow-x: auto;
    overflow-y: hidden;
}
.table-container td {
    padding: 0 5px;
}
.table-container input {
    max-width: 70px;
}
</style>
