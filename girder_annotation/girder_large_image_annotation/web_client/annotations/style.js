import tc from 'tinycolor2';

var memoizeColorAlpha = {entries: 0};

function colorAlpha(color) {
    if (memoizeColorAlpha[color]) {
        return memoizeColorAlpha[color];
    }
    var tccolor = tc(color),
        value = {
            rgb: tccolor.toHexString(),
            alpha: tccolor.getAlpha()
        };
    memoizeColorAlpha.entries += 1;
    if (memoizeColorAlpha.entries > 100) {
        memoizeColorAlpha = {entries: 0};
    }
    memoizeColorAlpha[color] = value;
    return value;
}

export default function style(json, levels) {
    var color;
    const style = {};

    if (json.label) {
        style.label = json.label;
    }
    if (json.fillColor) {
        color = colorAlpha(json.fillColor);
        style.fillColor = color.rgb;
        style.fillOpacity = color.alpha;
    }
    if (json.lineColor) {
        color = colorAlpha(json.lineColor);
        style.strokeColor = color.rgb;
        style.strokeOpacity = color.alpha;
    }
    if (json.lineWidth) {
        style.strokeWidth = json.lineWidth;
    }
    if (json.pattern) {
        const pattern = '' + json.pattern;
        if (window.geo.markerFeature.symbols[pattern] !== undefined) {
            let symbolValue = 1;
            if (pattern.startsWith('flower') || pattern.startsWith('jack')) {
                symbolValue = 0.3;
            } else if (pattern.startsWith('star')) {
                symbolValue = 0.6;
            }
            // scaling with zoom often makes the zoomed out view appear
            // unpatterned.  disable scale with zoom by settings levels to
            // undefined -- though this is somewhat distracting while zooming
            levels = undefined;
            const rad = 48 / (levels !== undefined ? 2 ** levels : 4);
            style.pattern = {
                symbol: window.geo.markerFeature.symbols[pattern],
                symbolValue: symbolValue,
                strokeWidth: 0,
                radius: rad,
                rotation: -Math.PI / 2,
                scaleWithZoom: levels !== undefined ? window.geo.markerFeature.scaleMode.all : window.geo.markerFeature.scaleMode.none,
                spacing: -2.2 * rad
            };
        }
    }
    return style;
}
