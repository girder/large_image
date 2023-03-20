<script>
import Vue from 'vue';
import ChannelSelector from './ChannelSelector.vue';
import IndexSelector from './IndexSelector.vue';
export default Vue.extend({
    props: ['imageMetadata', 'frameUpdate'],
    components: { ChannelSelector, IndexSelector },
    data() {
        return {
            currentFrame: 0,
            maxFrame: this.imageMetadata.frames.length - 1,
            modes: [
                { id: 0, name: 'Frame' },
                { id: 1, name: 'Axis' }
            ],
            currentModeId: 0,
            indices: [],
            indexInfo: {},
            hasChannels: false,
            compositeModes: [
                { id: 0, name: 'Single' },
                { id: 1, name: 'Composite' }
            ],
            currentCompositeModeId: 0,
            compositeChannelInfo: {},
            compositedFrames: {},
        };
    },
    computed: {
        nonChannelIndices() {
            return this.indices.filter((index) => index !== 'IndexC');
        },
        currentChannelName() {
            if (!this.indexInfo['IndexC']) {
                return '';
            }
            return this.imageMetadata.channels[this.indexInfo['IndexC'].current];
        }
    },
    watch: {
        currentCompositeModeId(newCompositeModeId) {
            if (newCompositeModeId === 0) {
                this.compositeChannelInfo = [];
                this.frameUpdate(this.currentFrame);
            } else if (newCompositeModeId === 1) {
                const frameName = this.imageMetadata.channels[this.currentFrame];
                this.compositeChannelInfo.push({
                    channel: frameName,
                    color: '#f00'
                });
            }
        }
    },
    methods: {
        buildStyleArray() {
            // TODO: support selecting more than one Z/T/XY index value at a time
            // For now, assume channels can be composite and other indices
            // will be limited to one value.
            const activeChannels = this.indexInfo['IndexC'].activeFrames;
            const styleArray = [];
            _.forEach(activeChannels, (channel) => {
                let frame = channel.number;
                _.forEach(this.nonChannelIndices, (index) => {
                    frame += this.indexInfo[index].current * this.indexInfo[index].stride;
                });
                const styleEntry = {
                    frame: frame,
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
            return { bands: styleArray };
        },
        singleModeUpdateChannel(activeChannelInfo) {
            this.indexInfo['IndexC'].activeFrames = activeChannelInfo;
            this.indexInfo['IndexC'].current = activeChannelInfo[0].number;
            this.updateFrame();
        },
        updateFrameByAxes(event) {
            this.indexInfo[event.index].current = event.frame;
            this.updateFrame();
        },
        updateFrame() {
            const useStyle = (
                this.indexInfo['IndexC'].activeFrames.length > 1
                || this.indexInfo['IndexC'].activeFrames[0].falseColor
                || this.indexInfo['IndexC'].activeFrames[0].min
                || this.indexInfo['IndexC'].activeFrames[0].max
            );
            if (useStyle) {
                const styleArray = this.buildStyleArray();
                this.frameUpdate(this.currentFrame, styleArray);
            } else {
                // For now, assume we have 'IndexC'
                let nextFrame = 0;
                _.forEach(this.indices, (index) => {
                    const info = this.indexInfo[index];
                    nextFrame += info.current * info.stride;
                });
                this.frameUpdate(nextFrame);
            }
        },
        updateFrameSimple(event) {
            // update 'current' property of frameInfo objects
            const target = event.target;
            const newFrame = target.valueAsNumber;
            Object.keys(this.indexInfo).forEach((key) => {
                this.indexInfo[key].current = Math.floor(
                    this.currentFrame / this.indexInfo[key].stride) % this.indexInfo[key].range;
            });
            this.frameUpdate(newFrame);
        },
        getCurrentChannelName() {
            if (!this.indexInfo['IndexC']) {
                return '';
            }
            return this.imageMetadata.channels[this.indexInfo['IndexC'].current];
        }
    },
    mounted() {
        Object.keys(this.imageMetadata.IndexRange).forEach((indexName) => {
            this.indices.push(indexName);
            this.indexInfo[indexName] = {
                current: 0,
                range: this.imageMetadata.IndexRange[indexName],
                stride: this.imageMetadata.IndexStride[indexName],
                activeFrames: []
            };
        });
        if (this.imageMetadata.channels) {
            this.hasChannels = true;
            this.imageMetadata.channels.forEach((channel) => {
                this.compositeChannelInfo[channel] = {
                    enabled: false,
                    color: null,
                    min: null,
                    max: null,
                    channel: channel
                };
            });
            this.compositeChannelInfo[this.imageMetadata.channels[0]].enabled = true;
        }
    }
});
</script>

<template>
    <div class="image-frame-control">
        <div class="image-frame-simple-control">
            <label for="frame">Frame: </label>
            <input
                type="number"
                name="frame"
                min="0"
                :max="maxFrame"
                :disabled="currentModeId === 1"
                v-model="currentFrame"
                @input.prevent="updateFrameSimple"
            >
            <input
                class="image-frame-slider"
                type="range"
                name="frameSlider"
                min="0"
                :max="maxFrame"
                :disabled="currentModeId === 1"
                v-model="currentFrame"
                @change.prevent="updateFrameSimple"
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
            class="image-frame-advanced-controls"
        >
            <channel-selector
                :channels="imageMetadata.channels"
                :channelMap="imageMetadata.channelmap"
                :initialChannelName="getCurrentChannelName()"
                @updateFrameSingle="singleModeUpdateChannel"
            >
            </channel-selector>
            <div v-if="currentModeId === 1">
                <div
                    v-for="index in nonChannelIndices"
                    :key="index"
                >
                    <index-selector
                        :indexName="index"
                        :range="indexInfo[index].range"
                        :stride="indexInfo[index].stride"
                        :initialFrame="indexInfo[index].current"
                        @updateFrame="updateFrameByAxes"
                    >
                    </index-selector>
                </div>
            </div>
        </div>
    </div>
</template>

<style scoped>
.image-frame-simple-control {
    display: flex;
    flex-direction: row;
}
.image-frame-index-slider {
    display: flex;
    flex-direction: column;
}
.image-frame-slider {
    display: flex;
    flex-direction: row;
}
.single-channel-advanced-controls {
    display: flex;
    flex-direction: row;
}
.image-frame-simple-control > * {
    margin-right: 5px;
}
.image-frame-index-slider > * {
    margin-right: 5px;
}
.image-frame-slider {
    width: 30%;
}
</style>
