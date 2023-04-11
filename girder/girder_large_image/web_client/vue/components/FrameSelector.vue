<script>
import Vue from 'vue';
import CompositeLayers from './CompositeLayers.vue';
import DualInput from './DualInput.vue'
export default Vue.extend({
    props: ['imageMetadata', 'frameUpdate'],
    components: { CompositeLayers, DualInput },
    data() {
        return {
            currentFrame: 0,
            maxFrame: this.imageMetadata.frames.length - 1,
            sliderModes: [],
            currentModeId: 1,
            indices: [],
            indexInfo: {},
        };
    },
    watch: {
        currentModeId() {
            this.update();
        }
    },
    computed: {
        sliderIndices() {
            return this.indices.filter(
                (i) => {
                    if (this.currentModeId === 2 && i === 'IndexC') return false
                    return true
                }
            )
        }
    },
    methods: {
        updateStyle(style) {
            this.style = style
            this.update()
        },
        updateAxisSlider(event) {
            this.indexInfo[event.index].current = event.frame;
            this.update();
        },
        updateFrameSlider(frame) {
            this.frameUpdate(frame, undefined);
        },
        update() {
            let frame = 0;
            _.forEach(this.indices, (index) => {
                const info = this.indexInfo[index];
                frame += info.current * info.stride;
            });
            let style = this.currentModeId > 1 ? this.style : undefined
            this.frameUpdate(frame, style);
        },
        fillMetadata() {
            if (
                (!this.imageMetadata.channels || !this.imageMetadata.channelmap)
                && Object.keys(this.imageMetadata.IndexRange).includes('IndexC')
            ) {
                this.imageMetadata.channelmap = Object.fromEntries(
                    [...Array(this.imageMetadata.IndexRange['IndexC']).keys()].map(
                        (i) => [`Channel ${i}`, i]
                    )
                )
                this.imageMetadata.channels = Object.keys(this.imageMetadata.channelmap)
            }
            if (!this.imageMetadata.bands) {
                this.imageMetadata.bands = [ 'red', 'green', 'blue' ]
            } else {
                this.imageMetadata.bands = Object.values(this.imageMetadata.bands).map(
                    // interpretation values come as a string: "name=min-max"
                    // TODO: don't ignore min and max values
                    (b) => b.interpretation ?b.interpretation.split("=")[0] :b
                )
            }
        },
        populateIndices() {
            Object.keys(this.imageMetadata.IndexRange).forEach((indexName) => {
                this.indices.push(indexName);
                this.indexInfo[indexName] = {
                    current: 0,
                    range: this.imageMetadata.IndexRange[indexName] -1,
                    stride: this.imageMetadata.IndexStride[indexName],
                    activeFrames: []
                };
            });
        },
        populateModes() {
            if (this.imageMetadata.frames.length > 1) {
                this.sliderModes.push(
                    { id: 0, name: 'Frame' }
                )
                this.sliderModes.push(
                    { id: 1, name: 'Axis' }
                )
            } else {
                this.sliderModes.push(
                    { id: -1, name: 'Default' }
                )
            }
            if (this.imageMetadata.channels && this.imageMetadata.channels.length > 1) {
                this.sliderModes.push(
                    { id: 2, name: 'Channel Compositing' }
                )
            }
            this.sliderModes.push(
                { id: 3, name: 'Advanced Band Compositing' }
            )
        }
    },
    mounted() {
        this.fillMetadata()
        this.populateIndices()
        this.populateModes()
    }
});
</script>

<template>
    <div class="image-frame-control-box">
        <div>
            <label for="mode">Image control mode: </label>
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
            @updateValue="updateFrameSlider"
        />
        <div class="image-frame-simple-control" v-if="currentModeId > 0">
            <div
                v-for="index in sliderIndices"
                :key="index"
            >
                <dual-input
                    :currentValue="indexInfo[index].current"
                    :valueMax="indexInfo[index].range"
                    :label="index.replace('Index', '')"
                    @updateValue="(v) => updateAxisSlider({index, frame: v})"
                />
            </div>
        </div>

        <div v-if="currentModeId > 1" class="image-frame-simple-control">
            <composite-layers
                :layers="currentModeId === 2 ? imageMetadata.channels : imageMetadata.bands"
                :layerMap="currentModeId === 2 ? imageMetadata.channelmap : undefined"
                :frameIndices="indexInfo"
                @updateStyle="updateStyle"
            />
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
