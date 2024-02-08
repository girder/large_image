<script>
import {restRequest} from '@girder/core/rest';
import Vue from 'vue';

import {makeDraggableSVG} from '../utils/drag';

export default {
    props: [
        'itemId',
        'layerIndex',
        'currentFrame',
        'currentFrameHistogram',
        'histogramParams',
        'framedelta',
        'currentMin',
        'currentMax',
        'autoRange',
        'active'
    ],
    emits: ['updateMin', 'updateMax', 'updateAutoRange'],
    data() {
        return {
            histogram: undefined,
            xRange: [undefined, undefined],
            vRange: [undefined, undefined]
        };
    },
    watch: {
        currentFrame() {
            this.fetchHistogram();
        },
        currentFrameHistogram() {
            this.fetchHistogram();
        },
        histogram() {
            // allow rerender to occur first
            Vue.nextTick().then(() => {
                this.xRange = [5, this.$refs.svg.clientWidth - 5];
                this.vRange = [this.histogram.min, this.histogram.max];
                this.drawHistogram(
                    this.simplifyHistogram(this.histogram.hist)
                );
                makeDraggableSVG(
                    this.$refs.svg,
                    this.validateHandleDrag,
                    this.dragHandle,
                    this.xRange
                );
                this.initializePositions();
                return undefined;
            });
        },
        currentMin() {
            this.initializePositions();
        },
        currentMax() {
            this.initializePositions();
        },
        autoRange() {
            this.initializePositions();
        }
    },
    mounted() {
        this.fetchHistogram();
    },
    methods: {
        fetchHistogram() {
            if (!this.active) return undefined;
            if (this.framedelta !== undefined) {
                restRequest({
                    type: 'GET',
                    url: 'item/' + this.itemId + '/tiles/histogram',
                    data: Object.assign(
                        this.histogramParams,
                        {frame: this.currentFrame + this.framedelta}
                    )
                }).then((response) => {
                    if (response.length < 3) {
                        this.histogram = response[0];
                    } else {
                        this.histogram = response[1];
                    }
                    return undefined;
                });
            } else {
                this.histogram = this.layerIndex < this.currentFrameHistogram.length
                    ? this.currentFrameHistogram[this.layerIndex]
                    : this.currentFrameHistogram[0];
            }
        },
        simplifyHistogram(hist) {
            let aggregationFactor = Math.round(1000 / (this.xRange[1] - this.xRange[0]));
            if (aggregationFactor < 1) aggregationFactor = 1;
            const simpleHistogram = [];
            for (var i = 0; i < hist.length; i += aggregationFactor) {
                simpleHistogram.push(
                    hist.slice(i, i + aggregationFactor)
                        .reduce((a, b) => a + b, 0)
                );
            }
            return simpleHistogram;
        },
        drawHistogram(hist) {
            // this makes the canvas lines not blurry
            const {clientWidth, clientHeight} = this.$refs.canvas;
            this.$refs.canvas.setAttribute('width', clientWidth);
            this.$refs.canvas.setAttribute('height', clientHeight);

            const maxFrequency = Math.max(...hist);
            const minFrequency = Math.min(...hist);
            const secondMaxFrequency = Math.max(...hist.filter((v) => v !== maxFrequency));
            const shortenMaxFrequency = (
                secondMaxFrequency > minFrequency &&
                (maxFrequency - secondMaxFrequency) > secondMaxFrequency / 3
            );

            const {width, height} = this.$refs.canvas;
            const ctx = this.$refs.canvas.getContext('2d');
            const widthBetweenPoints = width / hist.length;
            ctx.clearRect(0, 0, width, height);
            for (var i = 0; i < hist.length; i++) {
                const frequency = hist[i];
                const x0 = widthBetweenPoints * i;
                const x1 = widthBetweenPoints * (i + 1);
                let y0 = height - (frequency / maxFrequency * height);
                if (shortenMaxFrequency) {
                    y0 = frequency === maxFrequency ? 0 : height - (frequency / secondMaxFrequency * height * 2 / 3);
                }
                const y1 = height;

                ctx.rect(x0, y0, (x1 - x0), (y1 - y0));
            }
            ctx.fillStyle = '#888';
            ctx.fill();
        },
        xPositionToValue(xPosition) {
            const xProportion = (xPosition - this.xRange[0]) / (this.xRange[1] - this.xRange[0]);
            return Math.round(
                (this.histogram.max - this.histogram.min) * xProportion + this.histogram.min
            );
        },
        valueToXPosition(value) {
            const xProportion = (value - this.histogram.min) / (this.histogram.max - this.histogram.min);
            return Math.round(
                (this.xRange[1] - this.xRange[0]) * xProportion + this.xRange[0]
            );
        },
        initializePositions() {
            if (!this.histogram) return;

            const currentMinPosition = parseFloat(this.$refs.minHandle.getAttribute('x1'));
            const currentMaxPosition = parseFloat(this.$refs.maxHandle.getAttribute('x1'));
            let newMinPosition = this.xRange[0];
            let newMaxPosition = this.xRange[1];

            if (this.currentMin) {
                newMinPosition = this.valueToXPosition(this.currentMin);
            }
            if (this.currentMax) {
                newMaxPosition = this.valueToXPosition(this.currentMax);
            }
            if (this.autoRange) {
                newMinPosition = this.valueToXPosition(
                    this.fromDistributionPercentage(this.autoRange / 100)
                );
                newMaxPosition = this.valueToXPosition(
                    this.fromDistributionPercentage((100 - this.autoRange) / 100)
                );
            }

            // clamp to available space
            if (newMinPosition < this.xRange[0]) newMinPosition = this.xRange[0];
            if (newMinPosition > this.xRange[1]) newMinPosition = this.xRange[1];
            if (newMaxPosition < this.xRange[0]) newMaxPosition = this.xRange[0];
            if (newMaxPosition > this.xRange[1]) newMaxPosition = this.xRange[1];

            if (newMinPosition !== currentMinPosition) {
                this.setHandlePosition(
                    this.$refs.minHandle,
                    newMinPosition,
                    this.$refs.minExclusionBox,
                    5,
                    newMinPosition - 5
                );
            }
            if (newMaxPosition !== currentMaxPosition) {
                this.setHandlePosition(
                    this.$refs.maxHandle,
                    newMaxPosition,
                    this.$refs.maxExclusionBox,
                    newMaxPosition,
                    this.xRange[1] - newMaxPosition
                );
            }
        },
        validateHandleDrag(selected, newLocation) {
            let moveX = true;
            const moveY = false;
            const handleName = selected.getAttribute('name');
            const newValue = this.xPositionToValue(newLocation.x);
            if (handleName === 'updateMin') {
                if (!this.autoRange && newValue >= this.currentMax) {
                    moveX = false;
                } else if (this.autoRange && this.toDistributionPercentage(newValue) >= 50) {
                    moveX = false;
                }
            } else if (handleName === 'updateMax') {
                if (!this.autoRange && newValue <= this.currentMin) {
                    moveX = false;
                } else if (this.autoRange && this.toDistributionPercentage(newValue) <= 50) {
                    moveX = false;
                }
            }

            return [moveX, moveY];
        },
        dragHandle(selected, newLocation) {
            const funcName = selected.getAttribute('name');
            let newValue = this.xPositionToValue(newLocation.x);
            if (this.autoRange !== undefined) {
                newValue = this.toDistributionPercentage(newValue);
                if (funcName === 'updateMax') {
                    newValue = 100 - newValue;
                }
                newValue = parseFloat(parseFloat(newValue).toFixed(2));
                this.$emit('updateAutoRange', newValue);
            } else {
                if (funcName === 'updateMin') {
                    this.$refs.minExclusionBox.setAttributeNS(null, 'width', `${newLocation.x - 5}`);
                } else if (funcName === 'updateMax') {
                    this.$refs.maxExclusionBox.setAttributeNS(null, 'x', `${newLocation.x}`);
                    this.$refs.maxExclusionBox.setAttributeNS(null, 'width', `${this.xRange[1] - newLocation.x}`);
                }
                this.$emit(funcName, newValue);
            }
        },
        setHandlePosition(handle, position, exclusionBox, exclusionBoxPosition, exclusionBoxWidth) {
            handle.setAttributeNS(null, 'x1', `${position}`);
            handle.setAttributeNS(null, 'x2', `${position}`);
            exclusionBox.setAttributeNS(null, 'x', `${exclusionBoxPosition}`);
            if (exclusionBoxWidth >= 0) {
                exclusionBox.setAttributeNS(null, 'width', `${exclusionBoxWidth}`);
            }
        },
        fromDistributionPercentage(percentage) {
            const numSamples = this.histogram.samples * percentage;
            let bucketIndex = 0;
            let sum = 0;
            this.histogram.hist.forEach((count, index) => {
                sum += count;
                if (sum <= numSamples) {
                    bucketIndex = index;
                }
            });
            return this.histogram.bin_edges[bucketIndex];
        },
        toDistributionPercentage(value) {
            let numSamples = 0;
            this.histogram.hist.forEach((count, index) => {
                if (value >= this.histogram.bin_edges[index]) {
                    numSamples += count;
                }
            });
            return numSamples / this.histogram.samples * 100;
        },
        updateFromInput(funcName, value) {
            let roundedValue;
            if (value) {
                roundedValue = parseFloat(parseFloat(value).toFixed(2));
            }
            this.$emit(funcName, roundedValue);
        }
    }
};
</script>

<template>
  <div v-if="histogram">
    <div class="range-editor">
      <input
        v-if="autoRange === undefined"
        type="number"
        class="input-80"
        :min="histogram.min"
        :max="currentMax"
        :value="currentMin"
        @input="(e) => updateFromInput('updateMin', e.target.value)"
      >
      <span
        v-else
        class="input-80"
      />
      <svg
        ref="svg"
        class="handles-svg"
      >
        <text
          v-if="vRange[0] !== undefined"
          x="5"
          y="43"
          class="small"
        >{{ +vRange[0].toFixed(2) || 0 }}</text>
        <rect
          ref="minExclusionBox"
          x="5"
          y="0"
          width="0"
          height="30"
          opacity="0.2"
        />
        <line
          ref="minHandle"
          class="draggable"
          name="updateMin"
          stroke="#000"
          stroke-width="4"
          x1="5"
          x2="5"
          y1="0"
          y2="30"
        />
        <text
          v-if="vRange[1] !== undefined"
          :x="xRange[1] && vRange[1] ? xRange[1] - (`${vRange[1]}`.length * 6): 0"
          y="43"
          class="small"
        >{{ +vRange[1].toFixed(2) || 1 }}</text>
        <rect
          ref="maxExclusionBox"
          x="5"
          y="0"
          width="0"
          height="30"
          opacity="0.2"
        />
        <line
          ref="maxHandle"
          class="draggable"
          name="updateMax"
          stroke="#000"
          stroke-width="4"
          x1="5"
          x2="5"
          y1="0"
          y2="30"
        />
      </svg>
      <canvas
        ref="canvas"
        class="canvas"
      />
      <input
        v-if="autoRange === undefined"
        type="number"
        class="input-80"
        :max="histogram.max"
        :min="currentMin"
        :value="currentMax"
        @input="(e) => updateFromInput('updateMax', e.target.value)"
      >
      <span
        v-else
        class="percentage-input"
      >
        <input
          type="number"
          class="input-80"
          :max="50"
          :min="0"
          :value="autoRange"
          @input="(e) => updateFromInput('updateAutoRange', e.target.value)"
        >
      </span>
    </div>
  </div>
</template>

<style scoped>
.range-editor {
    position: absolute;
    display: flex;
    height: 30px;
    width: 100%;
}
.canvas {
    width: calc(100% - 160px);
    max-height: 100%;
    padding: 0px 5px;
}
.handles-svg {
    position: absolute;
    left: 80px;
    width: calc(100% - 160px);
    height: calc(100% + 15px);
}
.draggable {
  cursor: move;
}
</style>
