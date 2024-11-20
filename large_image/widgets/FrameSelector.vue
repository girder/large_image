<script>
import Vue from 'vue';


export default Vue.extend({
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
            modesShown: {1: true},
            histogramParamStyles: {}
        };
    },
    computed: {
    },
    watch: {
    },
    mounted() {
        console.log('here')
        this.metadata = Object.assign({}, this.imageMetadata);
        this.fillMetadata();
        this.maxFrame = this.metadata.frames.length - 1;
        this.populateIndices();
        this.populateModes();
        this.loaded = true;
    },
    methods: {
    }
});
</script>

<template>
  <div
    class="image-frame-control-box"
  >
    <div id="current_image_frame">
        {{ currentFrame }}
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
