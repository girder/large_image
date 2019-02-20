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

export default function style(json) {
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
    return style;
}
