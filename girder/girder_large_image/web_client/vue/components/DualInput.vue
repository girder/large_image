<script>
export default {
    props: ['label', 'currentValue', 'valueMax', 'sliderLabels'],
    emits: ['updateValue'],
    data() {
        return {
            value: this.currentValue,
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
    <tr :class="this.sliderLabels.length ? 'dual-controls tall' : 'dual-controls'">
        <td><label for="numberControl">{{ label }}: </label></td>
        <td><input
            type="number"
            name="numberControl"
            min="0"
            :max="valueMax"
            v-model="value"
        ></td>
        <td style="width:90%">
            <input
                type="range"
                name="sliderControl"
                min="0"
                :max="valueMax"
                v-model="value"
            >
            <div class="bubble-wrap">
                <output
                    v-if="this.sliderLabels.length > value"
                    :style="'left:'+value/valueMax*100+'%'"
                    class="bubble"
                >
                    {{ this.sliderLabels[value] }}
                </output>
            </div>
        </td>
    </tr>
</template>

<style scoped>
.dual-controls > * > * {
    margin-right: 15px;
}
.dual-controls.tall {
    height: 40px;
    vertical-align: top;
}
.bubble-wrap {
  position: relative;
  width: calc(100% - 20px);
  left: 10px;
}
.bubble {
  background: rgb(120, 120, 120);
  font-size: 10px;
  color: white;
  padding: 4px 12px;
  position: absolute;
  border-radius: 4px;
  transform: translateX(-50%);
  z-index: 10;
}
.bubble::after {
  content: "";
  position: absolute;
  width: 2px;
  height: 2px;
  background: rgb(120, 120, 120);
  top: -1px;
  left: 50%;
}
</style>
