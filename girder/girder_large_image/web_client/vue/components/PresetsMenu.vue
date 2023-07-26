<script>
import { restRequest } from '@girder/core/rest';

export default {
    props: ['itemId', 'currentMode', 'currentFrame', 'currentStyle'],
    emits: ['setCurrentMode', 'setCurrentFrame', 'updateStyle'],
    data() {
        return {
            availablePresets: [],
            selectedPreset: undefined,
            showPresetCreation: false,
            newPresetName: undefined,
            errorMessage: undefined,
        }
    },
    methods: {
        getPresets() {
            restRequest({
                type: 'GET',
                url: 'item/' + this.itemId + '/internal_metadata/presets',
            }).then((presets) => {
                if (presets) {
                    this.availablePresets = presets
                }
            })
        },
        addPreset(e, overwrite=false) {
            const newPreset = {
                'name': this.newPresetName || this.generatedPresetName,
                'mode': this.currentMode,
                'frame': this.currentFrame,
                'style': this.currentStyle,
            }
            newPreset.name = newPreset.name.trim()
            if (!overwrite && this.availablePresets.find((p) => p.name === newPreset.name)) {
                this.errorMessage = `There is already a preset named "${newPreset.name}". Overwrite "${newPreset.name}"?`
            } else {
                this.availablePresets = this.availablePresets.filter((p) => p.name !== newPreset.name)
                this.availablePresets.push(newPreset)
                this.selectedPreset = newPreset.name
                this.savePresetsList()
                this.newPresetName = undefined
                this.errorMessage = undefined
                this.showPresetCreation = false
            }
        },
        deleteSelectedPreset() {
            this.availablePresets = this.availablePresets.filter((p) => p.name !== this.selectedPreset)
            this.selectedPreset = undefined
            this.savePresetsList()
        },
        savePresetsList() {
            restRequest({
                type: 'PUT',
                url: 'item/' + this.itemId + '/internal_metadata/presets',
                data: JSON.stringify(this.availablePresets),
                contentType: 'application/json',
            })
        },
        styleEqual(style1, style2) {
            if (style1 === style2) {
                return true
            }
            if (style1.bands.length !== style2.bands.length) {
                return false
            }
            return style1.bands.every((b1) => {
                b1 = Object.fromEntries(Object.entries(b1).filter(([k, v]) => v !== undefined))
                return style2.bands.some((b2) => {
                    b2 = Object.fromEntries(Object.entries(b2).filter(([k, v]) => v !== undefined))
                    return (
                        Object.entries(b1).every(([k, v]) => b2[k] === v)
                        && Object.entries(b2).every(([k, v]) => b1[k] === v)
                    )
                })
            })
        },
        checkPresetMatch() {
            const targetStyle = this.currentStyle && this.currentStyle.bands ? {
                bands: this.currentStyle.bands.map((b) => {
                    if (b.min && b.max && b.min.includes("min:") && b.max.includes("max:")) {
                        b.autoRange = parseFloat(
                            b.min.replace("min:", '')
                        ) * 100
                        b.min = undefined
                        b.max = undefined
                    }
                    return b
                })
            } : this.currentStyle
            const match = this.availablePresets.find((p) => (
                p.mode.id === this.currentMode.id
                && p.frame === this.currentFrame
                && this.styleEqual(targetStyle, p.style)
            ))
            this.selectedPreset = match ? match.name : undefined
        }
    },
    computed: {
        generatedPresetName() {
            let name = `${this.currentMode.name} control - Frame ${this.currentFrame}`;
            if (this.currentMode.id === 2) {
                name = `${this.currentStyle.bands.length} channels`
            } else if (this.currentMode.id === 3) {
                name = `${this.currentStyle.bands.length} bands`
            }
            return name;
        }
    },
    watch: {
        newPresetName() {
            if (this.newPresetName){
                this.errorMessage = undefined;
            }
        },
        selectedPreset() {
            if (this.selectedPreset) {
                const preset = this.availablePresets.find((p) => p.name === this.selectedPreset)
                if (preset.mode && preset.mode.id !== undefined) {
                    this.$emit('setCurrentMode', preset.mode);
                }
                if (preset.frame !== undefined) {
                    this.$emit('setCurrentFrame', preset.frame)
                }
                if (preset.style && Object.keys(preset.style.bands).length) {
                    this.$emit('updateStyle', preset.mode.id, preset.style)
                }
            }
        },
        currentMode() {
            this.checkPresetMatch()
        },
        currentFrame() {
            this.checkPresetMatch()
        },
        currentStyle() {
            this.checkPresetMatch()
        }
    },
    mounted() {
        this.getPresets()
    },
}
</script>

<template>
    <div class="presets-menu">
        Image View Presets:
        <select v-model="selectedPreset">
            <option v-if="availablePresets.length === 0" :value="undefined" selected disabled>
                No presets available
            </option>
            <option v-else :value="undefined" selected disabled>
                Select a preset
            </option>
            <option
                v-for="preset in availablePresets"
                :key="preset.id"
                >
                {{ preset.name }}
            </option>
        </select>
        <i
            class="icon-trash"
            v-if="selectedPreset"
            @click="deleteSelectedPreset"
        />
        <i
            class="icon-plus"
            @click="showPresetCreation = !showPresetCreation"
        />
        <div v-if="showPresetCreation" class="preset-creation">
            Save Current State as New Preset:
            <input
                v-model="newPresetName"
                :placeholder="generatedPresetName"
            >
            <span class="red--text">{{ errorMessage }}</span>
            <button @click="addPreset" v-if="errorMessage === undefined">
                Save Preset
            </button>
            <button @click="(e) => addPreset(e, true)" v-else>
                Update Preset
            </button>
        </div>
    </div>
</template>

<style scoped>
.presets-menu {
    float: right;
    text-align: right;
}
.preset-creation {
    display: flex;
    flex-direction: column;
    align-items: end;
    padding-top: 5px;
}
.red--text {
    color: red;
    max-width: 250px;
}
</style>
