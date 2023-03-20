<script>
export default {
    props: ['indexName', 'range', 'stride', 'initialFrame'],
    emits: ['updateFrame'],
    data() {
        return {
            currentFrame: 0
        }
    },
    watch: {
        currentFrame(newFrame) {
            const event = {
                frame: newFrame,
                index: this.indexName
            };
            this.$emit('updateFrame', event);
        }
    },
    mounted() {
        this.currentFrame = this.initialFrame;
    }
}
</script>

<template>
    <div class="index-frame-control">
        <div class="slider-controls">
            <label for="indexFrame">{{ indexName }}: </label>
            <input
                class="index-number-input"
                type="number"
                name="indexFrame"
                min="0"
                :max="range"
                v-model="currentFrame"
            >
            <input
                class="index-slider-input"
                type="range"
                name="indexFrameSlider"
                min="0"
                :max="range"
                v-model="currentFrame"
            >
        </div>
    </div>
</template>

<style scoped>
.index-frame-control {
    display: flex;
}
.slider-controls {
    display: flex;
    flex-direction: row;
    width: 100%;
}
.slider-controls > * {
    margin-left: 5px;
}
.index-slider-input {
    width: 30%;
}
</style>
