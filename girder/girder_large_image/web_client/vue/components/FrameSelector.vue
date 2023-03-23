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
            currentChannelCompositeModeId: 1,
            currentBandCompositeModeId: 1,
            indices: [],
            indexInfo: {},
            compositeChannelInfo: [],
            compositedFrames: {},
        };
    },
    watch: {
        currentChannelCompositeModeId(newCompositeModeId) {
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
    computed: {
        nonCompositeIndices() {
            return this.indices.filter((index) => {
                return index != 'IndexC' || this.currentChannelCompositeModeId === 0
            })
        }
    },
    methods: {
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
            let nextFrame = 0;
            _.forEach(this.indices, (index) => {
                const info = this.indexInfo[index];
                nextFrame += info.current * info.stride;
            });
            this.frameUpdate(nextFrame);
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
        if (this.imageMetadata.channels) {
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
                    @updateFrame="updateFrame"
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
