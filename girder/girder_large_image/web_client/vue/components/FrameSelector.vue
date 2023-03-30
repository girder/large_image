<script>
import Vue from 'vue';
import CompositeChannels from './CompositeChannels.vue';
import DualInput from './DualInput.vue'
export default Vue.extend({
    props: ['imageMetadata', 'frameUpdate'],
    components: { CompositeChannels, DualInput },
    data() {
        return {
            currentFrame: 0,
            maxFrame: this.imageMetadata.frames.length - 1,
            sliderModes: [
                { id: 0, name: 'Frame' },
                { id: 1, name: 'Axis' }
            ],
            compositeModes: [
                { id: 0, name: 'Single' },
                { id: 1, name: 'Composite' }
            ],
            currentModeId: 1,
            currentChannelNumber: 0,
            currentChannelCompositeModeId: 0,
            currentBandCompositeModeId: 1,
            indices: [],
            indexInfo: {},
            compositedFrames: {},
            activeChannels: [],
        };
    },
    watch: {
        currentChannelCompositeModeId() {
            this.frameUpdate();
        }
    },
    computed: {
        nonCompositeIndices() {
            return this.indices.filter((index) => {
                return index != 'IndexC' || this.currentChannelCompositeModeId === 0
            })
        }
    },
    methods: {
        updateActiveChannels(activeChannels) {
            this.activeChannels = activeChannels
            this.updateFrame()
        },
        updateFrameByAxes(event) {
            this.indexInfo[event.index].current = event.frame;
            this.updateFrame();
        },
        updateFrameSimple(newFrame) {
            Object.keys(this.indexInfo).forEach((key) => {
                this.indexInfo[key].current = Math.floor(
                    this.currentFrame / this.indexInfo[key].stride) % this.indexInfo[key].range;
            });
            this.frameUpdate(newFrame);
        },
        updateChannel(newChannel) {
            this.currentChannelNumber = newChannel
            this.updateFrame()
        },
        updateFrame() {
            const useStyle = this.currentModeId === 1
                && this.currentChannelCompositeModeId === 1
                && this.activeChannels.length > 0
            let style = undefined
            if(useStyle) {
                 const frameOffset = Object.entries(this.indexInfo).map(
                    ([indexName, indexInfo]) => {
                    if (indexName === 'IndexC') return 0
                    return indexInfo.current * indexInfo.stride;
                }).reduce((partialSum, a) => partialSum + a, 0);
                const styleArray = []
                this.activeChannels.forEach((channel) => {
                    const styleEntry = {
                        frame: channel.number + frameOffset,
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
                style = {bands: styleArray}
            }
            let nextFrame = 0;
            _.forEach(this.indices, (index) => {
                const info = this.indexInfo[index];
                nextFrame += info.current * info.stride;
            });
            console.log(style)
            this.frameUpdate(nextFrame, style);
        },
    },
    mounted() {
        Object.keys(this.imageMetadata.IndexRange).forEach((indexName) => {
            this.indices.push(indexName);
            this.indexInfo[indexName] = {
                current: 0,
                range: this.imageMetadata.IndexRange[indexName] -1,
                stride: this.imageMetadata.IndexStride[indexName],
                activeFrames: []
            };
        });
    }
});
</script>

<template>
    <div class="image-frame-control-box">
        <div class="slider-controls">
            <label for="mode">Frame slider mode: </label>
            <select
                v-model="currentModeId"
                name="mode"
            >
                <option
                    v-for="mode in sliderModes"
                    :key="mode.id"
                    :value="mode.id"
                >
                    {{ mode.name }}
                </option>
            </select>
        </div>
        <dual-input
            v-if="currentModeId === 0"
            :currentValue="currentFrame"
            :valueMax="maxFrame"
            label="Frame"
            @updateValue="updateFrameSimple"
        />
        <div class="image-frame-simple-control" v-if="currentModeId === 1">
            <div
                v-for="index in nonCompositeIndices"
                :key="index"
            >
                <dual-input
                    :currentValue="indexInfo[index].current"
                    :valueMax="indexInfo[index].range"
                    :label="index.replace('Index', '')"
                    @updateValue="(v) => updateFrameByAxes({index, frame: v})"
                />
            </div>
        </div>

        <div  v-if="imageMetadata.channels && currentModeId === 1">
            <label for="mode">Channels composite mode: </label>
            <select
                v-model="currentChannelCompositeModeId"
                name="channelMode"
            >
                <option
                    v-for="mode in compositeModes"
                    :key="mode.id"
                    :value="mode.id"
                >
                    {{ mode.name }}
                </option>
            </select>
            <div
                class="image-frame-simple-control"
                v-if="currentChannelCompositeModeId === 1"
            >
                <composite-channels
                    :channels="imageMetadata.channels"
                    :channelMap="imageMetadata.channelmap"
                    :frameIndices="indexInfo"
                    @updateActiveChannels="updateActiveChannels"
                />
            </div>
        </div>

        <div v-if="currentModeId === 1">
            <label for="mode">Bands composite mode: </label>
            <select
                v-model="currentBandCompositeModeId"
                name="channelMode"
                disabled
            >
                <option
                    v-for="mode in compositeModes"
                    :key="mode.id"
                    :value="mode.id"
                >
                    {{ mode.name }}
                </option>
            </select>
        </div>
    </div>
</template>

<style scoped>
.image-frame-control-box {
    display: flex;
    flex-direction: column;
}
.image-frame-simple-control {
    display: flex;
    flex-direction: column;
    column-gap: 15px;
    padding: 5px 10px;
}
</style>
