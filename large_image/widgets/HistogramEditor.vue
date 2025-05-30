<script>
const dtypeAliases = {
    i1: 'int8',
    u1: 'uint8',
    i2: 'int16',
    u2: 'uint16',
    i4: 'int32',
    u4: 'uint32',
    i8: 'int64',
    u8: 'uint64',
    f2: 'float16',
    f4: 'float32',
    f: 'float32',
    f8: 'float64',
    d: 'float64'
};

const dtypeRanges = {
    int8: [-128, 127],
    uint8: [0, 255],
    int16: [-32768, 32767],
    uint16: [0, 65535],
    int32: [-2147483648, 2147483647],
    uint32: [0, 4294967295],
    int64: [-9.22e18, 9.22e18],
    uint64: [0, 1.84e19],
    float16: [-65500, 65500],
    float32: [-3.4e38, 3.4e38],
    float64: [-1.7e308, 1.7e308]
};

function clamp(num, min, max) {
    return Math.min(Math.max(num, min), max);
}

function makeDraggableSVG(svg, validateDrag, callback, xRange) {
    // Modified from https://www.w3schools.com/howto/howto_js_draggable.asp
    let selectedShape;
    let posOffset;
    svg.addEventListener('mousedown', startDrag);
    window.addEventListener('mousemove', drag);
    window.addEventListener('mouseup', endDrag);

    function getMousePosition(evt) {
        if (!svg) return {x: 0, y: 0};
        const CTM = svg.getScreenCTM();
        if (!CTM) return {x: 0, y: 0};
        return {
            x: (evt.clientX - CTM.e) / CTM.a,
            y: (evt.clientY - CTM.f) / CTM.d
        };
    }

    function startDrag(evt) {
        const target = evt.target;
        Array.from(document.body.getElementsByClassName('range-editor')).forEach(
            (el) => {
                el.style.userSelect = 'none';
            }
        );
        if (target && target.classList.contains('draggable')) {
            selectedShape = target;
            posOffset = getMousePosition(evt);
            posOffset.x -= parseFloat(
                selectedShape.getAttribute('x1') || '0'
            );
            posOffset.y -= parseFloat(
                selectedShape.getAttribute('y1') || '0'
            );
        }
    }

    function drag(evt) {
        if (selectedShape) {
            evt.preventDefault();
            const coord = getMousePosition(evt);
            if (posOffset) {
                coord.x -= posOffset.x;
                coord.y -= posOffset.y;
            }
            coord.x = clamp(coord.x, xRange[0], xRange[1]);
            const [moveX, moveY] = validateDrag(selectedShape, coord);
            if (!moveX) {
                coord.x = parseFloat(selectedShape.getAttribute('x1') || '0');
            }
            if (!moveY) {
                coord.y = parseFloat(selectedShape.getAttribute('y1') || '0');
            }

            selectedShape.setAttribute('x1', `${coord.x}`);
            selectedShape.setAttribute('x2', `${coord.x}`);
            selectedShape.setAttribute('y1', `${coord.y}`);
            callback(selectedShape, coord);
        }
    }

    function endDrag() {
        Array.from(document.body.getElementsByClassName('range-editor')).forEach(
            (el) => {
                el.style.userSelect = 'auto';
            }
        );
        selectedShape = undefined;
    }
}

module.exports = {
    props: [
        'itemId',
        'layerIndex',
        'currentFrame',
        'histogramParams',
        'frameHistograms',
        'getFrameHistogram',
        'framedelta',
        'currentMin',
        'currentMax',
        'dtype',
        'autoRange',
        'active',
        'updateMin',
        'updateMax',
        'updateAutoRange',
        'expanded',
        'expand',
        'mounted'
    ],
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
        frameHistograms() {
            const framedelta = this.framedelta || 0;
            const targetFrame = this.currentFrame + framedelta;
            if (this.frameHistograms[targetFrame]) {
                this.histogram = this.frameHistograms[targetFrame][0];
            }
        },
        expanded() {
            if (this.expanded) {
                // wait until svg ref is defined;
                // nextTick is not available so use setTimeout
                window.setTimeout(() => {
                    this.fetchHistogram();
                    this.histogramUpdated();
                }, 1);
            }
        },
        histogram() {
            this.histogramUpdated();
        },
        currentMin() {
            this.initializePositions();
        },
        currentMax() {
            this.initializePositions();
        },
        autoRange() {
            this.initializePositions();
        },
        invert() {
            this.drawHistogram(this.simplifyHistogram(this.histogram.hist));
            if (this.invert) {
                this.$refs.maxExclusionBox.setAttribute('visibility', 'hidden');
            } else {
                this.$refs.maxExclusionBox.setAttribute('visibility', 'visible');
            }
        }
    },
    computed: {
        minVal() {
            if (!this.histogram) return 0;
            if (this.autoRange !== undefined) return Math.round(this.fromDistributionPercentage(this.autoRange / 100));
            if (this.currentMin === undefined) return parseFloat(this.histogram.min.toFixed(2));
            return this.currentMin;
        },
        maxVal() {
            if (!this.histogram) return 1;
            if (this.autoRange !== undefined) return Math.round(this.fromDistributionPercentage((100 - this.autoRange) / 100));
            if (this.currentMax === undefined) return parseFloat(this.histogram.max.toFixed(2));
            return this.currentMax;
        },
        invert() {
            return this.currentMin > this.currentMax;
        },
        dtypeRange() {
            // remove byte-order characters
            let dtype = this.dtype.replace('>', '').replace('<', '').replace('=', '').replace('|', '');
            if (dtypeAliases[dtype]) dtype = dtypeAliases[dtype];
            const range = dtypeRanges[dtype];
            if (range && range.length === 2) {
                return range;
            } else {
                return [this.histogram.min, this.histogram.max];
            }
        }
    },
    mounted() {
        this.mounted();
    },
    methods: {
        fetchHistogram() {
            if (!this.active) return undefined;
            if (this.framedelta !== undefined) {
                const targetFrame = this.currentFrame + this.framedelta;
                if (this.frameHistograms[targetFrame]) {
                    this.histogram = this.frameHistograms[targetFrame][0];
                } else {
                    const params = Object.assign(
                        this.histogramParams,
                        {frame: targetFrame}
                    );
                    this.getFrameHistogram(params);
                }
            } else {
                const currentFrameHistogram = this.frameHistograms[this.currentFrame] || [];
                this.histogram = this.layerIndex < currentFrameHistogram.length
                    ? currentFrameHistogram[this.layerIndex]
                    : currentFrameHistogram[0];
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
        histogramUpdated() {
            if (!this.$refs.svg) return;
            this.xRange = [5, this.$refs.svg.clientWidth];
            if (this.histogram) {
                this.vRange = [this.histogram.min, this.histogram.max];
                this.drawHistogram(
                    this.simplifyHistogram(this.histogram.hist)
                );
            } else {
                this.vRange = [0, 1];
                this.drawHistogram([0, 0, 0]);
            }
            makeDraggableSVG(
                this.$refs.svg,
                this.validateHandleDrag,
                this.dragHandle,
                this.xRange
            );
            this.initializePositions();
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

                if (this.invert) {
                    ctx.rect(x0, 0, (x1 - x0), (y0)); // inverted colors
                } else {
                    ctx.rect(x0, y0, (x1 - x0), (y1 - y0));
                }
            }
            ctx.fillStyle = '#aaa';
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
            if (this.autoRange !== undefined) {
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
                    newMaxPosition - 5,
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
            if (handleName === 'min') {
                if (this.autoRange !== undefined) {
                    const percentage = this.toDistributionPercentage(newValue);
                    if (
                        percentage >= 50 ||
                        parseFloat(parseFloat(percentage).toFixed(2)) === this.autoRange
                    ) {
                        moveX = false;
                    }
                }
            } else if (handleName === 'max') {
                if (this.autoRange !== undefined) {
                    const percentage = this.toDistributionPercentage(newValue);
                    if (
                        percentage <= 50 ||
                        parseFloat(parseFloat(100 - percentage).toFixed(2)) === this.autoRange
                    ) {
                        moveX = false;
                    }
                }
            }

            return [moveX, moveY];
        },
        dragHandle(selected, newLocation) {
            const name = selected.getAttribute('name');
            let newValue = this.xPositionToValue(newLocation.x);
            if (this.autoRange !== undefined) {
                newValue = this.toDistributionPercentage(newValue);
                if (name === 'max') {
                    newValue = 100 - newValue;
                }
                newValue = parseFloat(parseFloat(newValue).toFixed(2));
                this.updateAutoRange(newValue);
            } else {
                if (name === 'min') this.updateMin(newValue);
                if (name === 'max') this.updateMax(newValue);

                // resize gray boxes
                const minX = this.$refs.minHandle.getAttribute('x1');
                const maxX = this.$refs.maxHandle.getAttribute('x1');
                if (this.invert && minX - maxX > 0) {
                    this.$refs.minExclusionBox.setAttribute('x', `${maxX}`);
                    this.$refs.minExclusionBox.setAttribute('width', `${minX - maxX}`);
                } else {
                    this.$refs.minExclusionBox.setAttribute('x', '0');
                    this.$refs.minExclusionBox.setAttribute('width', `${minX}`);
                    this.$refs.maxExclusionBox.setAttribute('x', `${maxX}`);
                    this.$refs.maxExclusionBox.setAttribute('width', `${this.xRange[1] - maxX}`);
                }
            }
        },
        setHandlePosition(handle, position, exclusionBox, exclusionBoxPosition, exclusionBoxWidth) {
            handle.setAttribute('x1', `${position}`);
            handle.setAttribute('x2', `${position}`);
            exclusionBox.setAttribute('x', `${exclusionBoxPosition}`);
            if (exclusionBoxWidth >= 0) {
                exclusionBox.setAttribute('width', `${exclusionBoxWidth}`);
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
        updateFromInput(target, value) {
            value = parseFloat(parseFloat(value).toFixed(2));
            if (target === 'min') {
                this.updateMin(value);
            } else if (target === 'max') {
                this.updateMax(value);
            }
        }
    }
};
</script>

<template>
  <td>
      <i
          :class="expanded ? 'expand-btn icon-up-open fa fa-angle-up' : 'expand-btn icon-down-open fa fa-angle-down'"
          @click="expand"
      ></i>
    <div
      v-if="expanded"
      class="range-editor"
    >
      <input
        v-if="histogram"
        type="number"
        class="input-80 min-input"
        :disabled="autoRange !== undefined"
        :min="dtypeRange[0]"
        :max="dtypeRange[1]"
        :value="minVal"
        @input="(e) => updateFromInput('min', e.target.value)"
      >
      <canvas
        ref="canvas"
        class="canvas"
      ></canvas>
      <svg
        ref="svg"
        class="handles-svg"
      >
        <text
          v-if="vRange[0] !== undefined"
          x="5"
          y="40"
          class="small"
        >
          {{ +vRange[0].toFixed(2) || 0 }}
        </text>
        <rect
          ref="minExclusionBox"
          x="5"
          y="0"
          width="0"
          height="30"
          opacity="0.2"
        />
        <rect
          ref="maxExclusionBox"
          x="5"
          y="0"
          width="0"
          height="30"
          opacity="0.2"
        />
        <line
          ref="minHandle"
          class="draggable"
          name="min"
          stroke="#000"
          stroke-width="5"
          x1="5"
          x2="5"
          y1="0"
          y2="30"
        >
          <title>{{ minVal }}</title>
        </line>
        <text
          v-if="vRange[1] !== undefined"
          :x="xRange[1] && vRange[1] ? xRange[1] - (`${vRange[1]}`.length * 8): 0"
          y="40"
          class="small"
        >
          {{ +vRange[1].toFixed(2) || 1 }}
        </text>
        <line
          ref="maxHandle"
          class="draggable"
          name="max"
          stroke="#000"
          stroke-width="5"
          x1="5"
          x2="5"
          y1="0"
          y2="30"
        >
          <title>{{ maxVal }}</title>
        </line>
      </svg>
      <input
        v-if="histogram"
        type="number"
        class="input-80 max-input"
        :disabled="autoRange !== undefined"
        :min="dtypeRange[0]"
        :max="dtypeRange[1]"
        :value="maxVal"
        @input="(e) => updateFromInput('max', e.target.value)"
      >
    </div>
  </td>
</template>

<style scoped>
.range-editor {
    position: absolute;
    display: flex;
    left: 0px;
    top: 30px;
    width: calc(100% - 10px);
    margin-bottom: 10px;
    height: 30px;
}
.canvas {
    position: absolute;
    left: 90px;
    width: calc(100% - 180px);
    max-height: 100%;
}
.handles-svg {
    position: absolute;
    left: 90px;
    width: calc(100% - 180px);
    height: calc(100% + 15px);
}
.draggable {
  cursor: move;
}
.min-input {
    position: absolute;
    left: 0;
}
.max-input {
    position: absolute;
    right: 0;
}
</style>
