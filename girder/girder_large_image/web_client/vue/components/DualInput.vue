<script>
export default {
    props: ['label', 'currentValue', 'valueMax'],
    emits: ['updateValue'],
    data() {
        return {
            value: this.currentValue
        }
    },
    watch: {
        value(v) {
            this.$emit('updateValue', v);
        }
    },
}
</script>

<template>
    <div class="dual-controls">
        <label for="numberControl">{{ label }}: </label>
        <input
            type="number"
            name="numberControl"
            min="0"
            :max="valueMax"
            v-model="value"
        >
        <input
            type="range"
            name="sliderControl"
            min="0"
            :max="valueMax"
            v-model="value"
        >
    </div>
</template>

<style scoped>
.dual-controls {
    display: flex;
    flex-direction: row;
    width: 100%;
}
.dual-controls > * {
    margin-right: 15px;
}
</style>
