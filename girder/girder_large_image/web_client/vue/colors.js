
export const CHANNEL_COLORS = {
    BRIGHTFIELD: '#FFFFFF',
    DAPI: '#0000FF',
    A594: '#FF0000',
    CY3: '#FF8000',
    CY5: '#FF00FF',
    YFP: '#00FF00',
    GFP: '#00FF00'
};

export const OTHER_COLORS = [
    '#FF0000',
    '#00FF00',
    '#0000FF',
    '#FFFF00',
    '#FF00FF',
    '#00FFFF',
    '#FF8000',
    '#FF0080',
    '#00FF80',
    '#80FF00',
    '#8000FF',
    '#0080FF',
    '#FF8080',
    '#80FF80',
    '#8080FF',
    '#FFFF80',
    '#80FFFF',
    '#FF80FF',
    '#FF4000',
    '#FF0040',
    '#00FF40',
    '#40FF00',
    '#4000FF',
    '#0040FF',
    '#FF4040',
    '#40FF40',
    '#4040FF',
    '#FFFF40',
    '#40FFFF',
    '#FF40FF',
    '#FFC000',
    '#FF00C0',
    '#00FFC0',
    '#C0FF00',
    '#C000FF',
    '#00C0FF',
    '#FFC0C0',
    '#C0FFC0',
    '#C0C0FF',
    '#FFFFC0',
    '#C0FFFF',
    '#FFC0FF',
    '#FF8040',
    '#FF4080',
    '#40FF80',
    '#80FF40',
    '#8040FF',
    '#4080FF',
    '#FF80C0',
    '#FFC080',
    '#C0FF80',
    '#80FFC0',
    '#80C0FF',
    '#C080FF',
    '#FFC040',
    '#FF40C0',
    '#40FFC0',
    '#C0FF40',
    '#C040FF',
    '#40C0FF'
];

export function getCompositeLayerColor(layerName, usedColors) {
    if (layerName in CHANNEL_COLORS) {
        return CHANNEL_COLORS[layerName];
    } else {
        const unusedColors = OTHER_COLORS.filter((c) => !usedColors.includes(c));
        if (unusedColors.length > 0) {
            return unusedColors[0];
        } else {
            // All colors have been used, just return a random one
            return OTHER_COLORS[Math.floor(Math.random() * OTHER_COLORS.length)];
        }
    }
}
