<script>
import { makeDraggableSVG } from '../utils/drag';

export default {
    props: ['histogram', 'currentMin', 'currentMax'],
    emits: ['updateMin', 'updateMax'],
    data() {
        return {
            xRange: [undefined, undefined],
            vRange: [undefined, undefined],
            tailsMode: false,
        }
    },
    methods: {
        simplifyHistogram(hist) {
            let aggregationFactor = Math.round(1000 / (this.xRange[1] - this.xRange[0]))
            if (aggregationFactor < 1) aggregationFactor = 1
            const simpleHistogram = []
            for (var i = 0; i < hist.length; i += aggregationFactor) {
                simpleHistogram.push(
                    hist.slice(i, i + aggregationFactor)
                    .reduce((a,b) => a + b, 0)
                )
            }
            return simpleHistogram
        },
        drawHistogram(hist){
            // this makes the canvas lines not blurry
            const {clientWidth, clientHeight} = this.$refs.canvas
            this.$refs.canvas.setAttribute('width', clientWidth)
            this.$refs.canvas.setAttribute('height', clientHeight)

            const maxFrequency = Math.max(...hist)
            const {width, height} = this.$refs.canvas
            const ctx = this.$refs.canvas.getContext("2d");
            const widthBetweenPoints = width / hist.length
            ctx.clearRect(0, 0, width, height);
            ctx.lineWidth = 4;
            ctx.beginPath()
            ctx.moveTo(0, height)
            for (var i = 0; i < hist.length; i++) {
                const frequency = hist[i]
                const pointX = widthBetweenPoints * i
                const pointY = height - (frequency / maxFrequency * height)
                ctx.lineTo(pointX, pointY)
            }
            ctx.stroke();
        },
        xPositionToValue(xPosition) {
            const xProportion = (xPosition - this.xRange[0]) / (this.xRange[1] - this.xRange[0])
            return Math.round(
                (this.histogram.max - this.histogram.min) * xProportion + this.histogram.min
            )
        },
        valueToXPosition(value) {
            const xProportion = (value - this.histogram.min) / (this.histogram.max - this.histogram.min)
            return Math.round(
                (this.xRange[1] - this.xRange[0]) * xProportion + this.xRange[0]
            )
        },
        validateHandleDrag(selected, newLocation) {
            let moveX = true;
            let moveY = false;
            const handleName = selected.getAttribute("name")
            const newValue = this.xPositionToValue(newLocation.x)
            if (handleName === 'updateMin' && newValue >= this.currentMax) {
                moveX = false;
            } else if (handleName === 'updateMax' && newValue <= this.currentMin) {
                moveX = false;
            }

            return [moveX, moveY]
        },
        dragHandle(selected, newLocation) {
            const funcName = selected.getAttribute("name")
            const newValue = this.xPositionToValue(newLocation.x)
            if (funcName === 'updateMin') {
                this.$refs.minExclusionBox.setAttributeNS(null, 'width', `${newLocation.x - 5}`)
            } else {
                const exclusionBoxWidth = this.xRange[1] - newLocation.x
                this.$refs.maxExclusionBox.setAttributeNS(null, 'x', `${newLocation.x}`)
                this.$refs.maxExclusionBox.setAttributeNS(null, 'width', `${exclusionBoxWidth}`)
            }

            this.$emit(funcName, newValue)
        },
        fromDistributionPercentage(percentage) {
            const numSamples = this.histogram.samples * percentage
            let bucketIndex = 0
            let sum = 0
            this.histogram.hist.forEach((count, index) => {
                sum += count
                if (sum <= numSamples) {
                    bucketIndex = index
                }
            })
            return Math.round(this.histogram.bin_edges[bucketIndex]);

        },
        toDistributionPercentage(value) {
            let numSamples = 0
            this.histogram.hist.forEach((count, index) => {
                if (value >= this.histogram.bin_edges[index]) {
                    numSamples += count
                }
            })
            return Math.round(numSamples / this.histogram.samples * 100)
        },
        updateFromInput(funcName, value) {
            if (this.tailsMode) {
                this.$emit(funcName, this.fromDistributionPercentage(parseFloat(value) / 100))
            } else {
                this.$emit(funcName, parseFloat(value))
            }
        },
        update() {
            this.vRange = [this.histogram.min, this.histogram.max]
            this.drawHistogram(
                this.simplifyHistogram(this.histogram.hist)
            );
        },
    },
    mounted() {
        this.xRange = [5, this.$refs.svg.clientWidth - 5]
        this.$refs.minHandle.setAttributeNS(null, 'x1', `${this.xRange[0]}`);
        this.$refs.minHandle.setAttributeNS(null, 'x2', `${this.xRange[0]}`);
        this.$refs.maxHandle.setAttributeNS(null, 'x1', `${this.xRange[1]}`);
        this.$refs.maxHandle.setAttributeNS(null, 'x2', `${this.xRange[1]}`);
        this.$refs.maxExclusionBox.setAttributeNS(null, 'x', `${this.xRange[1]}`)
        this.update()
        makeDraggableSVG(
            this.$refs.svg,
            this.validateHandleDrag,
            this.dragHandle,
            this.xRange,
        )
    },
    watch: {
        histogram() {
            this.update()
        },
        currentMin() {
            const currentPosition = parseFloat(this.$refs.minHandle.getAttribute('x1'))
            const newPosition = this.valueToXPosition(this.currentMin)
            if (newPosition !== currentPosition) {
                this.$refs.minHandle.setAttributeNS(null, 'x1', `${newPosition}`)
                this.$refs.minHandle.setAttributeNS(null, 'x2', `${newPosition}`)
                this.$refs.minExclusionBox.setAttributeNS(null, 'width', `${newPosition - 5}`)
            }
        },
        currentMax() {
            const currentPosition = parseFloat(this.$refs.maxHandle.getAttribute('x1'))
            const newPosition = this.valueToXPosition(this.currentMax)
            const exclusionBoxWidth = this.xRange[1] - newPosition
            if (newPosition !== currentPosition) {
                this.$refs.maxHandle.setAttributeNS(null, 'x1', `${newPosition}`)
                this.$refs.maxHandle.setAttributeNS(null, 'x2', `${newPosition}`)
                this.$refs.maxExclusionBox.setAttributeNS(null, 'x', `${newPosition}`)
                this.$refs.maxExclusionBox.setAttributeNS(null, 'width', `${exclusionBoxWidth}`)
            }
        },
        tailsMode() {
            if (this.tailsMode) {
                this.$emit('updateMin', this.fromDistributionPercentage(0.05)),
                this.$emit('updateMax', this.fromDistributionPercentage(0.95))
            }
        }
    }
}
</script>

<template>
    <div>
        <div style="height: 20px">
            <input
                type="checkbox"
                v-model="tailsMode"
            >
            Exclude distribution tails
        </div>
        <div class="range-editor">
            <span
                :class="tailsMode ? 'percentage-input' : ''"
            >
                <input
                    type="number"
                    :min="tailsMode ? 0 : histogram.min"
                    :max="tailsMode ? toDistributionPercentage(currentMax): currentMax"
                    :value="tailsMode ? toDistributionPercentage(currentMin) : currentMin"
                    style="width: 70px"
                    @input="(e) => updateFromInput('updateMin', e.target.value)"
                >
            </span>
            <svg ref="svg" class="handles-svg">
                <text x="5" y="43" class="small">{{ this.vRange[0] }}</text>
                <rect ref="minExclusionBox" x="5" y="0" width="0" height="30" opacity="0.2"/>
                <line
                    class="draggable"
                    name="updateMin"
                    ref="minHandle"
                    stroke="#f00"
                    stroke-width="4"
                    x1="5" x2="5"
                    y1="0" y2="30"
                />
                <text x="90%" y="43" class="small">{{ this.vRange[1] }}</text>
                <rect ref="maxExclusionBox" x="5" y="0" width="0" height="30" opacity="0.2"/>
                <line
                    class="draggable"
                    name="updateMax"
                    ref="maxHandle"
                    stroke="#f00"
                    stroke-width="4"
                    x1="5" x2="5"
                    y1="0" y2="30"
                />
            </svg>
            <canvas ref="canvas" class="canvas" />
            <span
                :class="tailsMode ? 'percentage-input' : ''"
            >
                <input
                    type="number"
                    :max="tailsMode ? 100 - toDistributionPercentage(currentMin) : histogram.max"
                    :min="tailsMode ? 0: currentMin"
                    :value="tailsMode ? 100 - toDistributionPercentage(currentMax) : currentMax"
                    style="width: 70px"
                    @input="(e) => updateFromInput('updateMax', 100 - e.target.value)"
                >
            </span>
        </div>
    </div>
</template>

<style scoped>
.range-editor {
    position: absolute;
    top: 20px;
    display: flex;
    height: 30px;
    width: 100%;
}
.canvas {
    width: calc(100% - 150px);
    max-height: 100%;
    padding: 0px 5px;
}
.handles-svg {
    position: absolute;
    left: 70px;
    width: calc(100% - 150px);
    height: calc(100% + 15px);
}
.draggable {
  cursor: move;
}
.percentage-input {
    position: relative;
}
.percentage-input::after {
    position: absolute;
    content: '%';
    left: 35px;
    top: 3px;
}
</style>
