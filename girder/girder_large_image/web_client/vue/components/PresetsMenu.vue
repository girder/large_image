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
        addPreset() {
            const newPreset = {
                'name': this.newPresetName || this.generatedPresetName,
                'mode': this.currentMode,
                'frame': this.currentFrame,
                'style': this.currentStyle,
            }
            if (this.availablePresets.find((p) => p.name === newPreset.name)) {
                this.errorMessage = `There is already a preset named "${newPreset.name}".`
            } else {
                this.availablePresets.push(newPreset)
                this.selectedPreset = newPreset.name
                this.savePresetsList()
            }
            this.newPresetName = undefined
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
                No presets available.
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
            @click="showPresetCreation = true"
        />
        <div v-if="showPresetCreation" class="preset-creation">
            Save Current State as New Preset:
            <input
                v-model="newPresetName"
                :placeholder="generatedPresetName"
            >
            <span class="red--text">{{ errorMessage }}</span>
            <button @click="addPreset">
                Save Preset
            </button>
        </div>
    </div>
</template>

<style scoped>
.presets-menu {
    float: right;
}
.preset-creation {
    display: flex;
    flex-direction: column;
    align-items: end;
    padding-top: 5px;
}
.red--text {
    color: red;
}
</style>
