<script>
module.exports = {
    props: ['label', 'currentValue', 'valueMax', 'sliderLabels', 'maxMerge'],
    watch: {
        currentValue() {
            this.$emit('update', this.currentValue)
        }
    }
};
</script>

<template>
  <tr :class="sliderLabels && sliderLabels.length ? 'dual-controls tall' : 'dual-controls'">
    <td><label for="numberControl">{{ label }}:</label></td>
    <td>
      <input
        v-model="currentValue"
        type="number"
        name="numberControl"
        min="0"
        :max="valueMax"
        :disabled="maxMerge"
      >
    </td>
    <td class="slider-control-cell">
      <input
        v-model="currentValue"
        type="range"
        name="sliderControl"
        min="0"
        :max="valueMax"
        :disabled="maxMerge"
        style="width: 100%"
      >
      <div class="bubble-wrap">
        <output
          v-if="sliderLabels && sliderLabels.length > currentValue"
          :style="'left:'+currentValue/valueMax*100+'%; transform:translateX(-'+currentValue/valueMax*100+'%)'"
          class="bubble"
        >
          {{ sliderLabels[currentValue] }}
        </output>
        <span
          v-if="sliderLabels && sliderLabels.length > currentValue"
          :style="'left:'+currentValue/valueMax*100+'%; transform:translateX(-'+currentValue/valueMax*100+'%)'"
          class="bubble-after"
        />
      </div>
    </td>
    <td
      v-show="maxMerge !== undefined"
      class="max-merge-cell"
      :title="'Max Merge ' + label"
    >
      <input
        :id="'maxMerge'+label"
        v-model="maxMerge"
        type="checkbox"
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
    height: 50px;
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
.slider-control-cell {
  width: 100%;
}
.max-merge-cell {
  min-width: 125px;
  text-align: right;
}
.max-merge-cell input[type="checkbox"] {
  margin: 0px 2px 0px 0px;
}
</style>
