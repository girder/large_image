<script>
// import _ from 'underscore';
export default {
    props: ['channels', 'channelMap'],
    emits: ['updateFrame'],
    data() {
        return {
            enabledChannels: this.channels,
        }
    },
    methods: {
        updateChannelColor(event, channel) {
            const newValue = event.target.value;
            this.compositeChannelInfo[channel].falseColor = newValue;
            this.notifyUpdateActiveFrames();
        },
        updateChannelMin(event, channel) {
            const newVal = event.target.value;
            const newMinVal = parseFloat(newVal);
            this.compositeChannelInfo[channel].min = newMinVal;
            this.notifyUpdateActiveFrames();
        },
        updateChannelMax(event, channel) {
            const newVal = event.target.valueAsNumber;
            const newMaxVal = parseFloat(newVal);
            this.compositeChannelInfo[channel].max = newMaxVal;
            this.notifyUpdateActiveFrames();
        },
        updateActiveChannels() {
            this.channels.forEach((channel) => {
                this.compositeChannelInfo[channel].enabled = this.enabledChannels.includes(channel);
            })
            this.notifyUpdateActiveFrames();
        },
        notifyUpdateActiveFrames() {
            const activeFrames = Object.values(
                this.compositeChannelInfo
            ).filter((channel) => channel.enabled);
            this.$emit('updateFrameSingle', activeFrames);
        },
    },
    computed: {
        compositeChannelInfo() {
            return Object.fromEntries(this.channels.map((channel) => {
                return [channel, {
                    number: this.channelMap[channel],
                    falseColorEnabled: false,
                    falseColor: '',
                    minMaxEnabled: false,
                    min: 0,
                    max: 0,
                    enabled: channel === this.initialChannelName,
                }]
            }))
        }
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
.false-color-controls {
    display: flex;
    flex-direction: row;
}
.false-color-controls > * {
    margin-left: 5px;
}
.table-container {
    max-height: 200px;
    overflow: scroll;
}
.table-container input {
    max-width: 70px;
}
</style>
