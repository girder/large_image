<script>
import { restRequest } from '@girder/core/rest';
import { Chrome } from 'vue-color';
import { CHANNEL_COLORS, OTHER_COLORS } from '../utils/colors'
import HistogramEditor from './HistogramEditor.vue';

export default {
    props: ['itemId', 'currentFrame', 'layers', 'layerMap'],
    emits: ['updateStyle'],
    components: {
        'color-picker': Chrome,
        HistogramEditor,
    },
    data() {
        return {
            enabledLayers: this.layers,
            colorPickerShown: undefined,
            currentColorPickerRef: undefined,
            compositeLayerInfo: {},
            histograms: [],
            expandedRows: [],
        }
    },
    methods: {
        initializeLayerInfo() {
            const usedColors = []
            this.compositeLayerInfo = {}
            this.layers.forEach((layerName, i) => {
                this.compositeLayerInfo[layerName] = {
                    layerName,
                    index: i,
                    framedelta: this.layerMap ? this.layerMap[layerName] : undefined,
                    band: this.layerMap ? undefined : i + 1,  // expected 1-based index
                    enabled: true,
                    min: undefined,
                    max: undefined,
                    custom: false,
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
            this.fetchHistograms()
        },
        fetchHistograms() {
            const histogramParams = {
                frame: this.currentFrame,
                width: 1024,
                height: 1024,
                bins: 512,
                resample: false,
            }
            if (this.layerMap) {
                // layers are channels; each layer has a frame delta
                this.layers.forEach((layer) => {
                    restRequest({
                        type: 'GET',
                        url: 'item/' + this.itemId + '/tiles/histogram',
                        data: Object.assign(
                            histogramParams,
                            {frame: this.currentFrame + this.compositeLayerInfo[layer].framedelta}
                        )
                    }).then((response) => {
                        if (response.length < 3) {
                            this.histograms.push(response[0])
                        } else {
                            this.histograms.push(response[1])
                        }
                    })
                })
            } else {
                // layers are bands; they share the same frame
                restRequest({
                    type: 'GET',
                    url: 'item/' + this.itemId + '/tiles/histogram',
                    data: histogramParams,
                }).then((response) => {
                    this.histograms = response
                });
            }
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
        toggleExpanded(index) {
            if (this.expandedRows.includes(index)) {
                this.expandedRows = this.expandedRows.filter((v) => v !== index)
            } else {
                this.expandedRows = [...this.expandedRows, index]
            }
        },
        toggleAllExpanded() {
            if (this.expandedRows.length === this.layers.length) {
                this.expandedRows = []
            } else {
                this.expandedRows = Object.values(this.compositeLayerInfo).map(({index}) => index)
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
        updateLayerMin(layer, newVal) {
            const newMinVal = Number.isFinite(newVal) ? parseFloat(newVal) : undefined;
            this.compositeLayerInfo[layer].min = newMinVal;
            this.compositeLayerInfo = Object.assign({}, this.compositeLayerInfo)  // for reactivity
            this.updateStyle();
        },
        updateLayerMax(layer, newVal) {
            const newMaxVal = Number.isFinite(newVal) ? parseFloat(newVal) : undefined;
            this.compositeLayerInfo[layer].max = newMaxVal;
            this.compositeLayerInfo = Object.assign({}, this.compositeLayerInfo)  // for reactivity
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
                const styleEntry = {
                    min: layer.min,
                    max: layer.max,
                    palette: layer.palette,
                    framedelta: layer.framedelta,
                    band: layer.band,
                }
                styleArray.push(styleEntry);
            });
            this.$emit('updateStyle', {bands: styleArray});
        },
    },
    watch: {
        currentFrame() {
            this.histograms = []
            this.fetchHistograms()
        },
        histograms() {
            this.layers.forEach((layer, index) => {
                if(this.histograms.length > index) {
                    const { min, max } = this.histograms[index]
                    this.compositeLayerInfo[layer] = Object.assign(
                        this.compositeLayerInfo[layer], {
                            min,
                            max,
                            defaultMin: min,
                            defaultMax: max,
                        }
                    )
                    this.compositeLayerInfo = Object.assign({}, this.compositeLayerInfo)
                }
            })
        }
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
                    <th class="enabled-col">
                        <input
                            type="checkbox"
                            :checked="enabledLayers === layers"
                            @input="toggleEnableAll"
                        >
                    </th>
                    <th class="layer-col">Layer</th>
                    <th class="color-col">Color</th>
                    <th class="layer-col">Range</th>
                    <div
                        v-if="histograms.length"
                        class="expand-btn"
                        @click="toggleAllExpanded"
                    >
                        {{ expandedRows.length === layers.length ? '&#9651;' : '&#9661;'}}
                    </div>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="{layerName, index, min, max, palette, defaultMin, defaultMax} in Object.values(compositeLayerInfo)"
                    :key="layerName"
                    :style="expandedRows.includes(index) ? {height: '100px'} : {}"
                >
                    <td style="width: 10%;">
                        <input
                            type="checkbox"
                            :value="layerName"
                            v-model="enabledLayers"
                            @change="updateActiveLayers"
                        >
                    </td>
                    <td  style="width: 40%;">{{ layerName }}</td>
                    <td :id="layerName+'_picker'" style="width: 25%;">
                    <span
                            class="current-color"
                            :style="{ 'background-color': palette }"
                            @click="() => toggleColorPicker(layerName)"
                        />
                        <color-picker
                            v-if="colorPickerShown === layerName"
                            class="picker-offset"
                            :disableAlpha="true"
                            :value="palette"
                            @input="(swatch) => {updateLayerColor(layerName, swatch)}"
                        />
                    </td>
                    <td style="width: 25%;">{{ min !== undefined && max !== undefined ? `${min} - ${max}` : '' }}</td>
                    <div
                        v-if="histograms[index]"
                        class="expand-btn"
                        @click="() => toggleExpanded(index)"
                    >
                    {{ (min === undefined && max === undefined) ||
                       (min === defaultMin && max === defaultMax)
                        ? expandedRows.includes(index) ? '&#9651;' : '&#9661;'
                        : expandedRows.includes(index) ? '&#9650;' : '&#9660;'
                    }}
                    </div>
                    <div v-if="histograms[index] && expandedRows.includes(index)" class="advanced-section">
                        <histogram-editor
                            :histogram="histograms[index]"
                            :currentMin="min"
                            :currentMax="max"
                            @updateMin="(v, d) => updateLayerMin(layerName, v, d)"
                            @updateMax="(v, d) => updateLayerMax(layerName, v, d)"
                        />
                    </div>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<style scoped>
.current-color {
    display: inline-block;
    width: calc(100% - 10px);
    height: 25px;
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
tr {
    position: relative;
}
.expand-btn {
    position: absolute;
    right: 0;
}
.advanced-section {
    position: absolute;
    left: 0px;
    width: 100%;
    margin: 30px 5px 0px;
    height: 55px;
}
</style>
