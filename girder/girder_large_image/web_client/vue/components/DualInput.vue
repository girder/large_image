<script>
export default {
    props: ['label', 'currentValue', 'valueMax', 'sliderLabels', 'maxMerge'],
    emits: ['updateValue', 'updateMaxMerge'],
    data() {
        return {
            value: this.currentValue,
            merge: this.maxMerge
        };
    },
    watch: {
        currentValue(v) {
            this.value = v;
        },
        value(v) {
            this.$emit('updateValue', v);
        },
        maxMerge(v) {
            this.merge = v;
        },
        merge(v) {
            this.$emit('updateMaxMerge', v);
        }
    }
};
</script>

<template>
  <tr :class="sliderLabels && sliderLabels.length ? 'dual-controls tall' : 'dual-controls'">
    <td><label for="numberControl">{{ label }}: </label></td>
    <td>
      <input
        v-model="value"
        type="number"
        name="numberControl"
        min="0"
        :max="valueMax"
        :disabled="merge"
      >
    </td>
    <td style="width: 100%">
      <input
        v-model="value"
        type="range"
        name="sliderControl"
        min="0"
        :max="valueMax"
        :disabled="merge"
      >
      <div class="bubble-wrap">
        <output
          v-if="sliderLabels && sliderLabels.length > value"
          :style="'left:'+value/valueMax*100+'%; transform:translateX(-'+value/valueMax*100+'%)'"
          class="bubble"
        >
          {{ sliderLabels[value] }}
        </output>
        <span
          v-if="sliderLabels && sliderLabels.length > value"
          :style="'left:'+value/valueMax*100+'%; transform:translateX(-'+value/valueMax*100+'%)'"
          class="bubble-after"
        />
      </div>
    </td>
    <td
      v-show="merge !== undefined"
      style="min-width: 150px; text-align: right;"
    >
      <input
        :id="'maxMerge'+label"
        v-model="merge"
        type="checkbox"
        style="margin: 0px 5px 0px 10px"
      >
      <label :for="'maxMerge'+label">Max Merge</label>
    </td>
  </tr>
</template>

<style scoped>
.dual-controls > * > * {
    margin-right: 15px;
    white-space: nowrap;
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
  white-space: nowrap;
}
.bubble-after {
  position: absolute;
  width: 4px;
  height: 4px;
  background: rgb(120, 120, 120);
  top: -1px;
  left: 50%;
}
</style>
