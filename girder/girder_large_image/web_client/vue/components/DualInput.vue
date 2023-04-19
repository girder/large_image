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
    <tr class="dual-controls">
        <td><label for="numberControl">{{ label }}: </label></td>
        <td><input
            type="number"
            name="numberControl"
            min="0"
            :max="valueMax"
            v-model="value"
        ></td>
        <td style="width:90%"><input
            type="range"
            name="sliderControl"
            min="0"
            :max="valueMax"
            v-model="value"
        ></td>
    </tr>
</template>

<style scoped>
.dual-controls > * > * {
    margin-right: 15px;
}
</style>
