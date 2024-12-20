/**
 * Create a color table that can be used for a heatmap.
 *
 * @param record: the heatmap or griddata heatmap annotation element.
 * @param values: a list of data values.
 * @returns: an object with:
 *      color: a color object that can be passed to the heatmap.
 *      min: the minIntensity for the heatmap.
 *      max: the maxIntensity for the heatmap.
 */
function heatmapColorTable(record, values) {
    let range0 = 0;
    let range1 = 1;
    let min = 0;
    let max = null;
    const color = {
        0: {r: 0, g: 0, b: 0, a: 0},
        1: {r: 1, g: 1, b: 0, a: 1}
    };
    if (record.colorRange && record.rangeValues) {
        if (record.normalizeRange || !values.length) {
            for (let i = 0; i < record.colorRange.length && i < record.rangeValues.length; i += 1) {
                const val = Math.max(0, Math.min(1, record.rangeValues[i]));
                color[val] = record.colorRange[i];
                if (val >= 1) {
                    break;
                }
            }
        } else if (record.colorRange.length >= 2 && record.rangeValues.length >= 2) {
            range0 = range1 = record.rangeValues[0] || 0;
            for (let i = 1; i < record.rangeValues.length; i += 1) {
                const val = record.rangeValues[i] || 0;
                if (val < range0) {
                    range0 = val;
                }
                if (val > range1) {
                    range1 = val;
                }
            }
            if (range0 === range1) {
                range0 -= 1;
            }
            min = undefined;
            for (let i = 0; i < record.colorRange.length && i < record.rangeValues.length; i += 1) {
                let val = (record.rangeValues[i] - range0) / ((range1 - range0) || 1);
                if (val <= 0 || min === undefined) {
                    min = record.rangeValues[i];
                }
                max = record.rangeValues[i];
                val = Math.max(0, Math.min(1, val));
                color[val] = record.colorRange[i];
                if (val >= 1) {
                    break;
                }
            }
        }
    }
    return {
        color: color,
        min: min,
        max: max
    };
}

/**
 * Convert a heatmap annotation to a geojs feature.
 *
 * @param record: the heatmap annotation element.
 * @param properties: a property map of additional data, such as the original
 *      annotation id.
 * @param layer: the layer where this may be added.
 */
function convertHeatmap(record, properties, layer) {
    /* Heatmaps need to be in their own layer */
    const map = layer.map();
    /* when scaleWithZoom is set, use the base pixel level of the first tile
     * layer for scaling rather than the 0-resolution level. */
    const tileLayer = map.layers().find((l) => l instanceof window.geo.tileLayer && l.options && l.options.maxLevel !== undefined);
    const scaleZoomFactor = tileLayer ? 2 ** -tileLayer.options.maxLevel : 1;
    const heatmapLayer = map.createLayer('feature', {features: ['heatmap']});
    const colorTable = heatmapColorTable(record, record.points.map((d) => d[3]));
    const heatmap = heatmapLayer.createFeature('heatmap', {
        style: {
            radius: (record.radius || 25) * (record.scaleWithZoom ? scaleZoomFactor : 1),
            blurRadius: 0,
            gaussian: true,
            color: colorTable.color,
            scaleWithZoom: record.scaleWithZoom || false
        },
        position: (d) => ({x: d[0], y: d[1], z: d[2]}),
        intensity: (d) => d[3] || 0,
        minIntensity: colorTable.min,
        maxIntensity: colorTable.max,
        updateDelay: 100
    }).data(record.points);
    heatmap._ownLayer = true;
    return [heatmap];
}

/**
 * Convert a griddata heatmap annotation to a geojs feature.
 *
 * @param record: the griddata heatmap annotation element.
 * @param properties: a property map of additional data, such as the original
 *      annotation id.
 * @param layer: the layer where this may be added.
 */
function convertGridToHeatmap(record, properties, layer) {
    /* Heatmaps need to be in their own layer */
    const map = layer.map();
    const heatmapLayer = map.createLayer('feature', {features: ['heatmap']});
    const x0 = (record.origin || [0, 0, 0])[0] || 0;
    const y0 = (record.origin || [0, 0, 0])[1] || 0;
    const z = (record.origin || [0, 0, 0])[2] || 0;
    const dx = (record.dx || 1);
    const dy = (record.dy || 1);
    const colorTable = heatmapColorTable(record, record.values);
    const tileLayer = map.layers().find((l) => l instanceof window.geo.tileLayer && l.options && l.options.maxLevel !== undefined);
    const scaleZoomFactor = tileLayer ? 2 ** -tileLayer.options.maxLevel : 1;
    const heatmap = heatmapLayer.createFeature('heatmap', {
        style: {
            radius: (record.radius || 25) * (record.scaleWithZoom ? scaleZoomFactor : 1),
            blurRadius: 0,
            gaussian: true,
            color: colorTable.color,
            scaleWithZoom: record.scaleWithZoom || false
        },
        position: (d, i) => ({
            x: x0 + dx * (i % record.gridWidth),
            y: y0 + dy * Math.floor(i / record.gridWidth),
            z: z
        }),
        intensity: (d) => d || 0,
        minIntensity: colorTable.min,
        maxIntensity: colorTable.max,
        updateDelay: 100
    }).data(record.values);
    heatmap._ownLayer = true;
    return [heatmap];
}

/**
 * Convert a griddata heatmap contour to a geojs feature.
 *
 * @param record: the griddata contour annotation element.
 * @param properties: a property map of additional data, such as the original
 *      annotation id.
 * @param layer: the layer where this may be added.
 */
function convertGridToContour(record, properties, layer) {
    let min = record.values[0] || 0;
    let max = min;
    for (let i = 1; i < record.values.length; i += 1) {
        if (record.values[i] > max) {
            max = record.values[i];
        }
        if (record.values[i] < max) {
            min = record.values[i];
        }
    }
    if (min >= 0) {
        min = -1; /* any negative number will do */
    }
    const contour = layer.createFeature('contour', {
        style: {
            value: (d) => d || 0
        },
        contour: {
            gridWidth: record.gridWidth,
            x0: (record.origin || [])[0] || 0,
            y0: (record.origin || [])[1] || 0,
            dx: record.dx || 1,
            dy: record.dy || 1,
            stepped: false,
            colorRange: [
                record.minColor || {r: 0, g: 0, b: 1, a: 1},
                record.zeroColor || {r: 0, g: 0, b: 0, a: 0},
                record.maxColor || {r: 1, g: 1, b: 0, a: 1}
            ],
            rangeValues: [min, 0, Math.max(0, max)]
        }
    }).data(record.values);
    return [contour];
}

const converters = {
    griddata_contour: convertGridToContour,
    griddata_heatmap: convertGridToHeatmap,
    heatmap: convertHeatmap
};

function convertFeatures(json, properties = {}, layer) {
    try {
        var features = [];
        json.forEach((element) => {
            const func = converters[element.type + '_' + element.interpretation] || converters[element.type];
            if (func) {
                features = features.concat(func(element, properties, layer));
            }
        });
        return features;
    } catch (err) {
        console.error(err);
    }
}

export {
    convertFeatures,
    heatmapColorTable
};
