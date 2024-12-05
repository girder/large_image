<script>
modules.export = {
    name: 'FrameSelector',
    props: ['currentFrame', 'itemId', 'imageMetadata', 'frameUpdate', 'liConfig'],
    data() {
        return {
            currentModeId: 0,
            maxFrame: 10,
        };
    },
    created() {
        console.log(this.imageMetadata)
        this.maxFrame = this.imageMetadata.frames.length - 1;
    },
    watch: {
        currentFrame() {
            this.frameUpdate(this.currentFrame)
        }
    },
    methods: {
        updateCurrentFrame(value) {
            this.currentFrame = value;
        }
    }
};
</script>

<template>
  <div
    class="image-frame-control-box"
  >
    <div id="current_image_frame" class="invisible">
        {{ currentFrame }}
    </div>
    <dual-input
        v-if="currentModeId === 0"
        :currentValue.sync="currentFrame"
        :valueMax="maxFrame"
        :maxMerge="false"
        label="Frame"
        @update="updateCurrentFrame"
    />
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
