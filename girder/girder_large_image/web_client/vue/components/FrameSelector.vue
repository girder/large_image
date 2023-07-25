<script>
import Vue from 'vue';
import CompositeLayers from './CompositeLayers.vue';
import DualInput from './DualInput.vue';
import PresetsMenu from './PresetsMenu.vue';

export default Vue.extend({
    props: ['itemId', 'imageMetadata', 'frameUpdate'],
    components: { CompositeLayers, DualInput, PresetsMenu },
    data() {
        return {
            loaded: false,
            currentFrame: 0,
            maxFrame: 0,
            sliderModes: [],
            currentModeId: 0,
            indices: [],
            indexInfo: {},
            style: {},
            modesShown: {1: true},
        };
    },
    watch: {
        currentModeId() {
            this.modesShown[this.currentModeId] = true;
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
        },
        currentStyle() {
            const curStyle = this.style[this.currentModeId];
            return curStyle ? JSON.stringify(curStyle, null, null) : '';
        }
    },
    methods: {
        setCurrentMode(mode) {
            this.currentModeId = mode.id
        },
        setCurrentFrame(frame) {
            this.currentFrame = frame
            this.indexInfo = Object.fromEntries(
                Object.entries(this.indexInfo)
                .map(([index, info]) => {
                    info.current = Math.floor(frame / info.stride) % (info.range + 1)
                    return [index, info]
                })
            )
        },
        updateStyle(idx, style) {
            this.$set(this.style, idx, style);
            this.update()
        },
        updateAxisSlider(event) {
            this.indexInfo[event.index].current = event.frame;
            this.update();
        },
        updateFrameSlider(frame) {
            this.currentFrame = frame
            this.frameUpdate(frame, undefined);
        },
        update() {
            let frame = 0;
            _.forEach(this.indices, (index) => {
                if (this.sliderIndices.includes(index)){
                    const info = this.indexInfo[index];
                    frame += info.current * info.stride;
                }
            });
            this.currentFrame = frame
            let style = this.currentModeId > 1 ? this.style[this.currentModeId] : undefined
            this.frameUpdate(frame, style);
        },
        fillMetadata() {
            if (!this.imageMetadata.frames) {
                this.imageMetadata.frames = [{
                    Frame: 0,
                    Index: 0,
                }]
            }
            if (!this.imageMetadata.IndexRange || !this.imageMetadata.IndexStride) {
                this.imageMetadata.IndexRange = {}
                this.imageMetadata.IndexStride = {}
            }
            if (
                (!this.imageMetadata.channels || !this.imageMetadata.channelmap)
                && Object.keys(this.imageMetadata.IndexRange).includes('IndexC')
            ) {
                this.imageMetadata.channelmap = Object.fromEntries(
                    [...Array(this.imageMetadata.IndexRange['IndexC']).keys()].map(
                        (i) => [`Channel ${i + 1}`, i]
                    )
                )
                this.imageMetadata.channels = Object.keys(this.imageMetadata.channelmap)
            }
            if (!this.imageMetadata.bands) {
                switch (this.imageMetadata.bandCount) {
                    case 1:
                        this.imageMetadata.bands = [ 'gray' ];
                        break;
                    case 2:
                        this.imageMetadata.bands = [ 'gray', 'alpha' ];
                        break;
                    case 3:
                        this.imageMetadata.bands = [ 'red', 'green', 'blue' ];
                        break;
                    case 4:
                        this.imageMetadata.bands = [ 'red', 'green', 'blue', 'alpha' ];
                        break;
                }
            } else {
                this.imageMetadata.bands = Object.values(this.imageMetadata.bands).map(
                    (b, i) => {
                        if (!b.interpretation) {
                            return `Band ${i + 1}`
                        } else {
                            return b.interpretation.split("=")[0]
                        }
                    }
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
                if(
                    Object.keys(this.imageMetadata.IndexRange).length > 0
                    && Object.keys(this.imageMetadata.IndexStride).length > 0
                ) {
                    this.sliderModes.push(
                        { id: 1, name: 'Axis' }
                    )
                    this.currentModeId = 1
                }
            } else {
                this.sliderModes.push(
                    { id: -1, name: 'Default' }
                )
                this.currentModeId = -1
            }
            if (this.imageMetadata.channels && this.imageMetadata.channels.length > 1) {
                this.sliderModes.push(
                    { id: 2, name: 'Channel Compositing' }
                )
            }
            if (this.imageMetadata.bandCount > 1) {
                this.sliderModes.push(
                    { id: 3, name: 'Band Compositing' }
                )
            }
        }
    },
    mounted() {
        this.fillMetadata()
        this.maxFrame = this.imageMetadata.frames.length - 1
        this.populateIndices()
        this.populateModes()
        this.loaded = true
    }
});
</script>

<template>
    <div class="image-frame-control-box" v-if="loaded">
        <div id="current_image_frame" class="invisible">{{ currentFrame }}</div>
        <div id="current_image_style" class="invisible">{{ currentStyle }}</div>
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
            <presets-menu
                :itemId="itemId"
                :currentMode="sliderModes.find((m) => m.id === currentModeId)"
                :currentFrame="currentFrame"
                :currentStyle="style[currentModeId]"
                @setCurrentMode="setCurrentMode"
                @setCurrentFrame="setCurrentFrame"
                @updateStyle="updateStyle"
            />
        </div>
        <dual-input
            v-if="currentModeId === 0"
            :currentValue="currentFrame"
            :valueMax="maxFrame"
            label="Frame"
            @updateValue="updateFrameSlider"
        />
        <table v-if="currentModeId > 0">
            <dual-input
                v-for="index in sliderIndices"
                :key="index"
                :currentValue="indexInfo[index].current"
                :valueMax="indexInfo[index].range"
                :label="index.replace('Index', '')"
                :sliderLabels="index === 'IndexC' ? imageMetadata.channels : []"
                @updateValue="(v) => updateAxisSlider({index, frame: v})"
            />
        </table>

        <!-- Use composite layers component twice so state for each one is maintained while invisible -->
        <!-- Use styling instead of v-if to make each invisible so that the components are not unmounted -->
        <div class="image-frame-simple-control">
            <composite-layers
                key="channels"
                v-if="imageMetadata.channels && modesShown[2]"
                :itemId="itemId"
                :currentFrame="currentFrame"
                :currentStyle="style[2]"
                :layers="imageMetadata.channels"
                :layerMap="imageMetadata.channelmap"
                :active="currentModeId === 2"
                :class="currentModeId === 2 ? '' : 'invisible'"
                @updateStyle="(style) => updateStyle(2, style)"
            />
            <composite-layers
                key="bands"
                v-if="imageMetadata.bands && modesShown[3]"
                :itemId="itemId"
                :currentFrame="currentFrame"
                :currentStyle="style[3]"
                :layers="imageMetadata.bands"
                :layerMap="undefined"
                :active="currentModeId === 3"
                :class="currentModeId === 3 ? '' : 'invisible'"
                @updateStyle="(style) => updateStyle(3, style)"
            />
        </div>
    </div>
</template>

<style scoped>
.invisible {
    display: none;
}
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
