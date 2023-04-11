<script>
import { Chrome } from 'vue-color';
import { CHANNEL_COLORS, OTHER_COLORS } from '../colors'

export default {
    props: ['channels', 'channelMap', 'frameIndices'],
    emits: ['updateStyle'],
    components: {
        'color-picker': Chrome
    },
    data() {
        return {
            enabledChannels: this.channels,
            colorPickerShown: undefined,
            currentColorPickerRef: undefined,
            compositeChannelInfo: {},
        }
    },
    methods: {
        initializeChannelInfo() {
            const usedColors = []
            this.compositeChannelInfo = {}
            this.channels.forEach((channelName) => {
                this.compositeChannelInfo[channelName] = {
                    number: this.channelMap[channelName],
                    enabled: true,
                    min: 0,
                    max: 0,
                }
            })
            Object.entries(CHANNEL_COLORS).forEach(([channelName, color]) => {
                if(this.channels.includes(channelName)){
                    this.compositeChannelInfo[channelName].falseColor = CHANNEL_COLORS[channelName]
                    usedColors.push(CHANNEL_COLORS[channelName])
                }
            })
            this.channels.forEach((channelName) => {
                if (!this.compositeChannelInfo[channelName].falseColor) {
                    let chosenColor;
                    const unusedColors = OTHER_COLORS.filter(
                        (color) => !usedColors.includes(color)
                    )
                    if (unusedColors.length > 0) {
                        chosenColor = unusedColors[0]
                    } else {
                        chosenColor = OTHER_COLORS[Math.floor(Math.random() * OTHER_COLORS.length)];
                    }
                    this.compositeChannelInfo[channelName].falseColor = chosenColor
                    usedColors.push(chosenColor)
                }
            })
        },
        toggleColorPicker(channel) {
            this.colorPickerShown = channel
            if (this.colorPickerShown === undefined) {
                document.removeEventListener('click', this.documentClick);
                // Only update style when picker is closed
                this.updateStyle()
            }
            else {
                this.currentColorPickerRef = document.getElementById(channel+'_picker')
                document.addEventListener('click', this.documentClick);
            }
        },
        documentClick(e) {
            const picker = this.currentColorPickerRef;
            if (picker && picker !== e.target && !picker.contains(e.target)) {
                this.toggleColorPicker(undefined);
            }
        },
        updateChannelColor(channel, swatch) {
            this.compositeChannelInfo[channel].falseColor = swatch.hex;
        },
        updateChannelMin(event, channel) {
            const newVal = event.target.value;
            const newMinVal = parseFloat(newVal);
            this.compositeChannelInfo[channel].min = newMinVal;
            this.updateStyle();
        },
        updateChannelMax(event, channel) {
            const newVal = event.target.valueAsNumber;
            const newMaxVal = parseFloat(newVal);
            this.compositeChannelInfo[channel].max = newMaxVal;
            this.updateStyle();
        },
        updateActiveChannels() {
            this.channels.forEach((channel) => {
                this.compositeChannelInfo[channel].enabled = this.enabledChannels.includes(channel);
            })
            this.updateStyle();
        },
        updateStyle() {
            const activeChannels = Object.values(
                this.compositeChannelInfo
            ).filter((channel) => channel.enabled);
            const styleArray = []
            activeChannels.forEach((channel) => {
                const styleEntry = {
                    frameDelta: channel.number,
                };
                if (channel.falseColor) {
                    styleEntry['palette'] = channel.falseColor;
                }
                if (channel.min) {
                    styleEntry['min'] = channel.min;
                }
                if (channel.max) {
                    styleEntry['max'] = channel.max;
                }
                styleArray.push(styleEntry);
            });
            this.$emit('updateStyle', {bands: styleArray});
        },
    },
    mounted() {
        this.initializeChannelInfo()
        this.updateStyle()
    }
}
</script>

<template>
    <div class="table-container">
        <table id="composite-channel-table" class="table table-condensed">
            <thead>
                <tr>
                    <th class="channel-col">Channel</th>
                    <th class="enabled-col">Enabled?</th>
                    <th class="color-col">Color</th>
                    <th class="precision-col">Min</th>
                    <th class="precision-col">Max</th>
                </tr>
            </thead>
            <tbody>
                <tr
                    v-for="channel in channels.filter(c => compositeChannelInfo[c] !== undefined)"
                    :key="channel"
                >
                    <td>{{ channel }}</td>
                    <td>
                        <input
                            type="checkbox"
                            :value="channel"
                            v-model="enabledChannels"
                            @change="updateActiveChannels"
                        >
                    </td>
                    <td :id="channel+'_picker'">
                        <span
                            class="current-color"
                            :style="{ 'background-color': compositeChannelInfo[channel].falseColor }"
                            @click="() => toggleColorPicker(channel)"
                        />
                        <color-picker
                            class="picker-offset"
                            v-if="colorPickerShown === channel"
                            :value="compositeChannelInfo[channel].falseColor"
                            @input="(swatch) => {updateChannelColor(channel, swatch)}"
                        />
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            :value="compositeChannelInfo[channel].min"
                            @change.prevent="(event) => updateChannelMin(event, channel)"
                        >
                    </td>
                    <td>
                        <input
                            type="number"
                            step="0.01"
                            min="0"
                            max="1"
                            :value="compositeChannelInfo[channel].max"
                            @change.prevent="(event) => updateChannelMax(event, channel)"
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
