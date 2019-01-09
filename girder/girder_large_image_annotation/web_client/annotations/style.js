import _ from 'underscore';
import tc from 'tinycolor2';

const props = [
    'label'
];

function colorAlpha(color) {
    if (!color) {
        return null;
    }
    color = tc(color);
    return {
        rgb: color.toHexString(),
        alpha: color.getAlpha()
    };
}

export default function style(json) {
    var color;
    const style = _.pick(json, ...props);

    color = colorAlpha(json.fillColor);
    if (color) {
        style.fillColor = color.rgb;
        style.fillOpacity = color.alpha;
    }

    color = colorAlpha(json.lineColor);
    if (color) {
        style.strokeColor = color.rgb;
        style.strokeOpacity = color.alpha;
    }

    if (json.lineWidth) {
        style.strokeWidth = json.lineWidth;
    }
    return style;
}
