<script>
import Vue from 'vue';

import CompositeLayers from './CompositeLayers.vue';
import DualInput from './DualInput.vue';
import PresetsMenu from './PresetsMenu.vue';

export default Vue.extend({
    components: {CompositeLayers, DualInput, PresetsMenu},
    props: ['itemId', 'imageMetadata', 'frameUpdate', 'liConfig'],
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
            modesShown: {1: true}
        };
    },
    computed: {
        sliderIndices() {
            return this.indices.filter(
                (i) => {
                    if (this.currentModeId === 2 && i === 'IndexC') return false;
                    return true;
                }
            );
        },
        currentStyle() {
            const curStyle = this.style[this.currentModeId];
            return curStyle ? JSON.stringify(curStyle, null, null) : '';
        }
    },
    watch: {
        currentModeId() {
            this.modesShown[this.currentModeId] = true;
            this.update();
        }
    },
    mounted() {
        this.metadata = Object.assign({}, this.imageMetadata);
        this.fillMetadata();
        this.maxFrame = this.metadata.frames.length - 1;
        this.populateIndices();
        this.populateModes();
        this.loaded = true;
    },
    methods: {
        setCurrentMode(mode) {
            this.currentModeId = mode.id;
        },
        setCurrentFrame(frame) {
            this.currentFrame = frame;
            this.indexInfo = Object.fromEntries(
                Object.entries(this.indexInfo)
                    .map(([index, info]) => {
                        info.current = Math.floor(frame / info.stride) % (info.range + 1);
                        return [index, info];
                    })
            );
        },
        updateStyle(idx, style) {
            this.$set(this.style, idx, style);
            this.update();
        },
        updateAxisSlider(event) {
            this.indexInfo[event.index].current = event.frame;
            this.update();
        },
        updateFrameSlider(frame) {
            this.currentFrame = frame;
            this.frameUpdate(frame, undefined);
        },
        update() {
            let frame = 0;
            this.indices.forEach((index) => {
                if (this.sliderIndices.includes(index)) {
                    const info = this.indexInfo[index];
                    frame += info.current * info.stride;
                }
            });
            this.currentFrame = frame;
            const style = this.currentModeId > 1 ? Object.assign({}, this.style[this.currentModeId]) : undefined;
            if (style && style.preset) delete style.preset;
            this.frameUpdate(frame, style);
        },
        fillMetadata() {
            if (!this.metadata.frames) {
                this.metadata.frames = [{
                    Frame: 0,
                    Index: 0
                }];
            }
            if (!this.metadata.IndexRange || !this.metadata.IndexStride) {
                this.metadata.IndexRange = {};
                this.metadata.IndexStride = {};
            }
            if (
                (!this.metadata.channels || !this.metadata.channelmap) &&
                Object.keys(this.metadata.IndexRange).includes('IndexC')
            ) {
                this.metadata.channelmap = Object.fromEntries(
                    [...Array(this.metadata.IndexRange.IndexC).keys()].map(
                        (i) => [`Channel ${i + 1}`, i]
                    )
                );
                this.metadata.channels = Object.keys(this.metadata.channelmap);
            }
            if (!this.metadata.bands) {
                switch (this.metadata.bandCount) {
                    case 1:
                        this.metadata.bands = ['gray'];
                        break;
                    case 2:
                        this.metadata.bands = ['gray', 'alpha'];
                        break;
                    case 3:
                        this.metadata.bands = ['red', 'green', 'blue'];
                        break;
                    case 4:
                        this.metadata.bands = ['red', 'green', 'blue', 'alpha'];
                        break;
                }
            } else {
                this.metadata.bands = Object.values(this.metadata.bands).map(
                    (b, i) => {
                        if (!b.interpretation) {
                            return `Band ${i + 1}`;
                        } else {
                            return b.interpretation.split('=')[0];
                        }
                    }
                );
            }
        },
        populateIndices() {
            Object.keys(this.metadata.IndexRange).forEach((indexName) => {
                this.indices.push(indexName);
                this.indexInfo[indexName] = {
                    current: 0,
                    range: this.metadata.IndexRange[indexName] - 1,
                    stride: this.metadata.IndexStride[indexName],
                    activeFrames: []
                };
            });
        },
        populateModes() {
            if (this.metadata.frames.length > 1) {
                this.sliderModes.push(
                    {id: 0, name: 'Frame'}
                );
                if (
                    Object.keys(this.metadata.IndexRange).length > 0 &&
                    Object.keys(this.metadata.IndexStride).length > 0
                ) {
                    this.sliderModes.push(
                        {id: 1, name: 'Axis'}
                    );
                    this.currentModeId = 1;
                }
            } else {
                this.sliderModes.push(
                    {id: -1, name: 'Default'}
                );
                this.currentModeId = -1;
            }
            if (this.metadata.channels && this.metadata.channels.length > 1) {
                this.sliderModes.push(
                    {id: 2, name: 'Channel Compositing'}
                );
            }
            if (this.metadata.bandCount) {
                this.sliderModes.push(
                    {id: 3, name: 'Band Compositing'}
                );
            }
        }
    }
});
</script>

<template>
  <div
    v-if="loaded"
    class="image-frame-control-box"
  >
    <div
      id="current_image_frame"
      class="invisible"
    >
      {{ currentFrame }}
    </div>
    <div
      id="current_image_style"
      class="invisible"
    >
      {{ currentStyle }}
    </div>
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
        :item-id="itemId"
        :li-config="liConfig"
        :image-metadata="imageMetadata"
        :available-modes="sliderModes.map((m) => m.id)"
        :current-mode="sliderModes.find((m) => m.id === currentModeId)"
        :current-frame="currentFrame"
        :current-style="style[currentModeId]"
        @setCurrentMode="setCurrentMode"
        @setCurrentFrame="setCurrentFrame"
        @updateStyle="updateStyle"
      />
    </div>
    <dual-input
      v-if="currentModeId === 0"
      :current-value="currentFrame"
      :value-max="maxFrame"
      label="Frame"
      @updateValue="updateFrameSlider"
    />
    <table v-if="currentModeId > 0">
      <dual-input
        v-for="index in sliderIndices"
        :key="index"
        :current-value="indexInfo[index].current"
        :value-max="indexInfo[index].range"
        :label="index.replace('Index', '')"
        :slider-labels="index === 'IndexC' ? imageMetadata.channels : []"
        @updateValue="(v) => updateAxisSlider({index, frame: v})"
      />
    </table>

    <!-- Use composite layers component twice so state for each one is maintained while invisible -->
    <!-- Use styling instead of v-if to make each invisible so that the components are not unmounted -->
    <div class="image-frame-simple-control">
      <composite-layers
        v-if="metadata.channels && modesShown[2]"
        key="channels"
        :item-id="itemId"
        :current-frame="currentFrame"
        :current-style="style[2]"
        :layers="metadata.channels"
        :layer-map="metadata.channelmap"
        :active="currentModeId === 2"
        :class="currentModeId === 2 ? '' : 'invisible'"
        @updateStyle="(style) => updateStyle(2, style)"
      />
      <composite-layers
        v-if="metadata.bands && modesShown[3]"
        key="bands"
        :item-id="itemId"
        :current-frame="currentFrame"
        :current-style="style[3]"
        :layers="metadata.bands"
        :layer-map="undefined"
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
