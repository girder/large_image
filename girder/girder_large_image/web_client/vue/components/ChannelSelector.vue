<script>
import _ from 'underscore';
export default {
    props: ['channels', 'channelMap', 'initialChannelName'],
    emits: ['updateFrameSingle', 'updateFrameComposite'],
    data() {
        return {
            compositeChannelInfo: {},
            enabledChannels: [],
            currentChannelFalseColorEnabled: false,
            currentChannelFalseColor: '',
            currentChannelMinMaxEnabled: false,
            currentChannelMin: 0,
            currentChannelMax: 0,
            currentChannelEnabled: true,
            currentChannelNumber: this.channelMap[this.initialChannelName],
            modes: [
                { id: 0, name: 'Single' },
                { id: 1, name: 'Composite' }
            ],
            histogramModes: [
                { id: 0, name: 'Precision' },
                { id: 2, name: 'Absolute Value' }
            ],
            currentModeId: 0,
            currentHistogramModeId: 0,
        }
    },
    watch: {
        enabledChannels: {
            handler(newValue, oldValue) {
                console.log('updated enabledChannels');
                console.log({ newValue, oldValue });
            },
            deep: true
        }
    },
    methods: {
        preventDisableChannel() { const numChannelsEnabled = _.reduce(Object.keys(this.compositeChannelInfo), (memo, channelKey) => {
                return memo + (this.compositeChannelInfo[channelKey].enabled ? 1 : 0);
            }, 0);
            return this.currentModeId === 1 && numChannelsEnabled === 1 && this.currentChannelEnabled;
        },
        updateChannel() {
            const newChannelName = this.channels[this.currentChannelNumber];
            const newChannelInfo = this.compositeChannelInfo[newChannelName];
            this.currentChannelFalseColorEnabled = newChannelInfo.falseColorEnabled;
            this.currentChannelFalseColor = newChannelInfo.falseColor;
            this.currentChannelMin = newChannelInfo.min;
            this.currentChannelMax = newChannelInfo.max;
            this.currentChannelEnabled = newChannelInfo.enabled;
            if (this.currentModeId === 0) {
                Object.keys(this.compositeChannelInfo).forEach((channel) => {
                    this.compositeChannelInfo[channel].enabled = (channel === newChannelName);
                });
                this.currentChannelEnabled = true;
                this.enabledChannels = [newChannelName];
                const activeFrames = _.filter(this.compositeChannelInfo, (channel) => channel.enabled);
                this.$emit('updateFrameSingle', activeFrames);
            } else {
                const activeFrames = _.filter(this.compositeChannelInfo, (channel) => channel.enabled);
                this.$emit('updateFrameSingle', activeFrames);
            }
        },
        notifyUpdateActiveFrames() {
            const activeFrames = _.filter(this.compositeChannelInfo, (channel) => channel.enabled);
            this.$emit('updateFrameSingle', activeFrames);
        },
        updateChannelColor(event, channel) {
            const newValue = event.target.value;
            this.compositeChannelInfo[channel].falseColor = newValue;
            this.notifyUpdateActiveFrames();
        },
        updateChannelMin(event, channel) {
            const newVal = event.target.value;
            const newMinVal = this.currentHistogramModeId === 0 ? `min:${newVal}` : parseFloat(newVal);
            this.compositeChannelInfo[channel].min = newMinVal;
            this.notifyUpdateActiveFrames();
        },
        updateChannelMax(event, channel) {
            const newVal = event.target.valueAsNumber;
            const newMaxVal = this.currentHistogramModeId === 0 ? `max:${newVal}` : parseFloat(newVal);
            this.compositeChannelInfo[channel].max = newMaxVal;
            this.notifyUpdateActiveFrames();
        },
        updateActiveChannels() {
            _.forEach(this.channels, (channel) => {
                this.compositeChannelInfo[channel].enabled = this.enabledChannels.includes(channel);
            })
            this.notifyUpdateActiveFrames();
        }
    },
    mounted() {
        this.channels.forEach((channel) => {
            this.compositeChannelInfo[channel] = {
                number: this.channelMap[channel],
                falseColorEnabled: false,
                falseColor: '',
                minMaxEnabled: false,
                min: 0,
                max: 0,
                enabled: channel === this.initialChannelName,
            };
        });
        this.currentChannelNumber = this.channelMap[this.initialChannelName];
        this.enabledChannels.push(this.initialChannelName);
    },
}
</script>

<template>
    <div class="single-index-frame-control">
        <div class="slider-mode-controls">
            <label for="channel">Channel: </label>
            <input
                class="channel-number-input"
                type="number"
                name="channel"
                min="0"
                :max="channels.length - 1"
                v-model="currentChannelNumber"
                :disabled="currentModeId === 1"
                @change.prevent="updateChannel"
            >
            <input
                class="single-index-slider"
                type="range"
                name="channelSlider"
                min="0"
                :max="channels.length -1"
                v-model="currentChannelNumber"
                :disabled="currentModeId === 1"
                @change.prevent="updateChannel"
            >
            <select
                v-model="currentModeId"
                name="mode"
            >
                <option
                    v-for="mode in modes"
                    :key="mode.id"
                    :value="mode.id"
                >
                    {{ mode.name }}
                </option>
            </select>
        </div>
        <div
            v-if="currentModeId === 1"
            class="channel-list-controls"
        >
            <label for="histogramMode">Histogram mode: </label>
            <select
                v-model="currentHistogramModeId"
                name="histogramMode"
            >
                <option
                    v-for="mode in histogramModes"
                    :key="mode.id"
                    :value="mode.id"
                >
                    {{ mode.name }}
                </option>
            </select>
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
                            v-for="channel in channels"
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
                            <td>
                                <input
                                    class="single-channel-color-input"
                                    type="text"
                                    :value="compositeChannelInfo[channel].falseColor"
                                    @change.prevent="(event) => updateChannelColor(event, channel)"
                                >
                            </td>
                            <td>
                                <input
                                    type="number"
                                    step="0.001"
                                    min="0"
                                    max="1"
                                    :value="compositeChannelInfo[channel].min"
                                    @change.prevent="(event) => updateChannelMin(event, channel)"
                                >
                            </td>
                            <td>
                                <input
                                    type="number"
                                    step="0.001"
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
        </div>
    </div>
</template>

<style scoped>
.single-index-frame-control {
    display: flex;
    flex-direction: column;
}
.slider-mode-controls, .false-color-controls {
    display: flex;
    flex-direction: row;
}
.false-color-controls > * {
    margin-left: 5px;
}
.channel-number-input {
    margin-left: 5px;
}
.single-index-slider {
    width: 30%;
}
.single-channel-options {
    display: flex;
    flex-direction: row;
}
.single-channel-options > * {
    padding-right: 10px;
    vertical-align: center;
}
.single-channel-enable {
    width: 100px;
}
.single-channel-color-input {
    width: 100px;
}
.table-container {
    max-width: 500px;
    max-height: 200px;
    overflow: scroll;
}
.channel-col {
    width: 100px;
}
.enabled-col {
    width: 70px;
}
.color-col {
    width: 125px;
}
.precision-col {
    width: 80px;
}
</style>
