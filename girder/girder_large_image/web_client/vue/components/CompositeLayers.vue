<script>
import { restRequest } from '@girder/core/rest';
import { Chrome } from 'vue-color';
import { CHANNEL_COLORS, OTHER_COLORS } from '../utils/colors'
import HistogramEditor from './HistogramEditor.vue';

export default {
    props: ['itemId', 'currentFrame', 'currentStyle', 'layers', 'layerMap', 'active'],
    emits: ['updateStyle'],
    components: {
        'color-picker': Chrome,
        HistogramEditor,
    },
    data() {
        return {
            enabledLayers: [],
            colorPickerShown: undefined,
            currentFrameHistogram: undefined,
            compositeLayerInfo: {},
            expandedRows: [],
            autoRangeForAll: undefined,
            histogramParams: {
                frame: this.currentFrame,
                width: 1024,
                height: 1024,
                bins: 512,
                resample: false,
                style: '{}',
                roundRange: true,
            },
            showKeyboardShortcuts: false,
        }
    },
    methods: {
        keyHandler(e) {
            let numericKey = parseFloat(e.key)
            if (e.ctrlKey && !isNaN(numericKey)) {
                e.preventDefault()
                if (numericKey === 0) {
                    numericKey += 10
                }
                if (e.altKey) {
                    numericKey += 10
                }
                const layerIndex = numericKey - 1
                if (layerIndex < this.layers.length) {
                    const targetLayer = this.layers[layerIndex]
                    if (this.compositeLayerInfo[targetLayer].enabled) {
                        this.enabledLayers = this.enabledLayers.filter((v) => v !== targetLayer)
                    } else {
                        this.enabledLayers.push(targetLayer)
                    }
                    this.updateActiveLayers()
                }
            }
        },
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
                    autoRange: undefined
                }
            })
            // Assign colors
            this.layers.forEach((layerName) => {
                if (!this.compositeLayerInfo[layerName].palette) {
                    // Search for case-insensitive regex match among known channel-colors
                    Object.entries(CHANNEL_COLORS).forEach(([channelPattern, color]) => {
                        if (layerName.match(new RegExp(channelPattern, 'i')) && !usedColors.includes(color)) {
                            this.compositeLayerInfo[layerName].palette = color
                            usedColors.push(color)
                        }
                    })

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
            this.fetchCurrentFrameHistogram()
        },
        initializeStateFromStyle() {
            this.enabledLayers = []
            const styleArray = this.currentStyle.bands
            this.layers.forEach((layerName) => {
                const layerInfo = this.compositeLayerInfo[layerName]
                const currentLayerStyle = styleArray.find((s) => s.framedelta === layerInfo.framedelta && s.band === layerInfo.band)
                if (currentLayerStyle) {
                    this.enabledLayers.push(layerName)
                    if (
                        currentLayerStyle.min && currentLayerStyle.max
                        && currentLayerStyle.min.includes("min:")
                        && currentLayerStyle.max.includes("max:")
                    ) {
                        currentLayerStyle.autoRange = parseFloat(
                            currentLayerStyle.min.replace("min:", '')
                        ) * 100
                        currentLayerStyle.min = undefined
                        currentLayerStyle.max = undefined
                    }
                }
                this.compositeLayerInfo[layerName] = Object.assign(
                    {}, layerInfo, currentLayerStyle
                )
            })
            this.layers.forEach((layer) => {
                this.compositeLayerInfo[layer].enabled = this.enabledLayers.includes(layer);
            })
            const autoRanges = Object.entries(this.compositeLayerInfo)
                .map(([index, info]) => info.autoRange)
                .filter((a) => a !== undefined)
            if (autoRanges.every((v) => v === autoRanges[0])) {
                this.autoRangeForAll = autoRanges[0]
            }
        },
        fetchCurrentFrameHistogram() {
            restRequest({
                type: 'GET',
                url: 'item/' + this.itemId + '/tiles/histogram',
                data: this.histogramParams,
            }).then((response) => {
                this.currentFrameHistogram = response
            });
        },
        toggleEnableAll() {
            if (!this.layers.every((l) => this.enabledLayers.includes(l))) {
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
            }
            else {
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
        updateLayerAutoRange(layer, value) {
            this.compositeLayerInfo = Object.assign(
                {}, this.compositeLayerInfo,
                {[layer] : Object.assign(
                    {}, this.compositeLayerInfo[layer], { autoRange: value }
                )}
            )
            this.updateStyle();
        },
        updateAllAutoRanges(value) {
            this.autoRangeForAll = value
            this.compositeLayerInfo = Object.fromEntries(
                Object.entries(this.compositeLayerInfo).map(([layerName, layerInfo]) => {
                    return [
                        layerName,
                        Object.assign({}, layerInfo, { autoRange: value })
                    ]
                })
            )
            this.updateStyle();
        },
        allAutoRange() {
            return Object.values(this.compositeLayerInfo).every(({ autoRange }) => autoRange !== undefined)
        },
        documentClick(e) {
            const picker = document.getElementById('color_picker');
            if (
                picker
                && picker !== e.target
                && !picker.contains(e.target)
                && !e.target.classList.contains('current-color')
            ) {
                this.toggleColorPicker(undefined);
            }
        },
        updateLayerColor(layer, swatch) {
            this.compositeLayerInfo[layer].palette = swatch.hex;
            this.updateStyle();
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
                    min: layer.autoRange !== undefined ? `min:${layer.autoRange / 100}` : layer.min,
                    max: layer.autoRange !== undefined ? `max:${layer.autoRange / 100}` : layer.max,
                    palette: layer.palette,
                    framedelta: layer.framedelta,
                    band: layer.band,
                }
                styleArray.push(styleEntry);
            });
            this.$emit('updateStyle', {bands: styleArray});
        },
    },
    mounted() {
        this.initializeLayerInfo()
        if (this.currentStyle) {
            this.initializeStateFromStyle()
        } else {
            if (this.layerMap) {
                // channels all enabled by default
                this.enabledLayers = this.layers
            } else {
                // only some bands enabled by default
                ['red', 'green', 'blue', 'gray', 'grey'].forEach((bandColor) => {
                    if (this.layers.includes(bandColor)) {
                        this.enabledLayers.push(bandColor)
                    }
                })
                // if no known band colors exist, enable the first three
                if (this.enabledLayers.length === 0) {
                    this.enabledLayers = this.layers.slice(0, 3)
                }
            }
            this.updateActiveLayers()
            this.updateStyle()
        }
        if (this.active) {
            document.addEventListener('keydown', this.keyHandler)
        }
    },
    watch: {
        active() {
            if (this.active) {
                document.addEventListener('keydown', this.keyHandler)
            } else {
                document.removeEventListener('keydown', this.keyHandler)
            }
        },
        currentStyle() {
            this.initializeStateFromStyle()
        }
    }
}
</script>

<template>
    <div>
        <i
            class="icon-keyboard"
            @click="showKeyboardShortcuts = !showKeyboardShortcuts"
        />
        <div class="shortcuts" v-if="showKeyboardShortcuts">
            <div class="h5">Keyboard Shortcuts</div>
            <div>
                <span class="monospace">ctrl + number</span>
                Toggle visibility of the layer at the number position
            </div>
            <div>
                <span style="font-weight: bold;">Example: </span>
                <span class="monospace">ctrl + 1</span>
                Toggle visibility of the first layer in the table
            </div>
            <div>
                <span class="monospace">ctrl + alt + number</span>
                Toggle visibility of the layer at the position of the number plus 10
            </div>
            <div>
                <span style="font-weight: bold;">Example: </span>
                <span class="monospace">ctrl + alt + 1</span>
                Toggle visibility of the eleventh layer in the table
            </div>
        </div>
        <div  :class="colorPickerShown ? 'table-container tall' : 'table-container'">
            <table id="composite-layer-table" class="table table-condensed">
                <thead class="table-header">
                    <tr>
                        <th>
                            <input
                                type="checkbox"
                                class="input-80"
                                :checked="layers.every((l) => enabledLayers.includes(l))"
                                @input="toggleEnableAll"
                            >
                        </th>
                        <th></th>
                        <th></th>
                        <th>
                            <div class="auto-range-col">
                                <div class="auto-range-label">
                                    <span class="small-text">Auto Range</span>
                                    <label class="switch">
                                        <span
                                            :class="allAutoRange() ? 'onoff-slider checked' : 'onoff-slider'"
                                            @click="() => updateAllAutoRanges(allAutoRange() ? undefined : 0.2)"
                                        />
                                    </label>
                                </div>
                                <span
                                    v-if="allAutoRange()"
                                    class="percentage-input"
                                >
                                    <input
                                        type="number"
                                        class="input-80"
                                        :max="50"
                                        :min="0"
                                        :value="autoRangeForAll"
                                        @input="(e) => updateAllAutoRanges(e.target.value)"
                                    >
                                </span>
                            </div>
                            <i
                                :class="expandedRows.length === layers.length ? 'expand-btn icon-up-open' : 'expand-btn icon-down-open'"
                                @click="toggleAllExpanded"
                            />
                        </th>
                    </tr>
                    <!-- color picker should display relative to sticky table head -->
                    <color-picker
                        v-if="colorPickerShown"
                        id="color_picker"
                        class="picker-offset"
                        :disableAlpha="true"
                        :value="Object.values(compositeLayerInfo).find((({layerName}) => layerName === colorPickerShown)).palette"
                        @input="(swatch) => {updateLayerColor(colorPickerShown, swatch)}"
                    />
                </thead>
                <tbody>
                    <tr
                        v-for="{
                            layerName, index, palette,
                            autoRange, min, max,
                            framedelta
                        } in Object.values(compositeLayerInfo)"
                        :key="layerName"
                        :class="expandedRows.includes(index) ? 'tall-row' : ''"
                    >
                        <td class="enable-col">
                            <input
                                type="checkbox"
                                class="input-80"
                                :value="layerName"
                                v-model="enabledLayers"
                                @change="updateActiveLayers"
                            >
                        </td>
                        <td class="name-col">{{ layerName }}</td>
                        <td class="color-col">
                            <span
                                class="current-color"
                                :style="{ 'background-color': palette }"
                                @click="() => toggleColorPicker(layerName)"
                            />
                        </td>
                        <td class="auto-range-col">
                            <div class="auto-range-toggle">
                                <label class="switch">
                                    <span
                                        :class="autoRange ? 'onoff-slider checked' : 'onoff-slider'"
                                        @click="() => updateLayerAutoRange(layerName, autoRange ? undefined : 0.2)"
                                    />
                                </label>
                            </div>
                            <i
                                :class="expandedRows.includes(index) ? 'expand-btn icon-up-open' : 'expand-btn icon-down-open'"
                                @click="() => toggleExpanded(index)"
                            />
                        </td>
                        <div v-if="expandedRows.includes(index)" class="advanced-section">
                            <histogram-editor
                                :itemId="itemId"
                                :layerIndex="index"
                                :currentFrame="currentFrame"
                                :currentFrameHistogram="currentFrameHistogram"
                                :histogramParams="histogramParams"
                                :framedelta="framedelta"
                                :autoRange="autoRange"
                                :currentMin="min"
                                :currentMax="max"
                                @updateMin="(v, d) => updateLayerMin(layerName, v, d)"
                                @updateMax="(v, d) => updateLayerMax(layerName, v, d)"
                                @updateAutoRange="(v) => updateLayerAutoRange(layerName, v)"
                            />
                        </div>
                    </tr>
                </tbody>
            </table>
        </div>
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
    right: 15%
}
.table-header {
    position: sticky;
    top: 0px;
    background-color: white;
    z-index: 2;
    border-bottom: 3px solid;
}
.small-text {
    font-size: 10px;
}
.tall-row {
    height: 75px;
}
.enable-col {
    width: 10%;
}
.name-col {
    max-width: 40%;
    word-break: break-all;
}
.color-col {
    width: 25%;
}
.auto-range-col {
    position: relative;
}
.auto-range-toggle {
    min-width: 100px;
    display: flex;
    column-gap: 10px;
    align-content: space-around;
    padding: 0;
}
.auto-range-label {
    display: flex;
    flex-direction: column;
}
.switch {
  position: relative;
  display: inline-block;
  width: 45px;
  height: 20px;
  margin-top: 5px;
}
.onoff-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  -webkit-transition: .4s;
  transition: .4s;
  border-radius: 34px;
}
.onoff-slider.checked {
  background-color: #2196F3;
}
.onoff-slider:focus{
  box-shadow: 0 0 1px #2196F3;
}
.onoff-slider:before {
  position: absolute;
  content: "";
  height: 15px;
  width: 15px;
  left: 4px;
  bottom: 2px;
  background-color: white;
  -webkit-transition: .4s;
  transition: .4s;
  border-radius: 50%;
}
.onoff-slider.checked:before {
  -webkit-transform: translateX(22px);
  -ms-transform: translateX(22px);
  transform: translateX(22px);
}
.table-container {
    overflow-y: scroll;
    overflow-x: auto;
    position: relative;
    max-height: 300px;
}
.table-container.tall {
    height: 300px;
}
.table-container td {
    padding: 0 5px;
}
.table-container input {
    max-width: 80px;
}
.table {
    border-collapse: separate;
}
.expand-btn {
    position: absolute;
    right: 10px;
    top: 5px;
}
.advanced-section {
    position: absolute;
    left: 0px;
    width: calc(100% - 10px);
    margin: 30px 0px 0px;
    height: 40px;
}
.icon-keyboard {
    font-size: 2rem;
}
.shortcuts {
    padding-bottom: 10px;
}
.monospace {
    font-family: monospace;
    background-color: rgba(0, 0, 0, 0.2);
    padding: 1px;
}
</style>

<style>
.input-80 {
    width: 80px
}
.percentage-input {
    position: relative;
    margin-top: 5px;
    width: 80px;
}
.percentage-input::after {
    position: absolute;
    content: '%';
    left: 45px;
    top: 3px;
}
</style>
