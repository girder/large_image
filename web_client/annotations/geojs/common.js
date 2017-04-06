import tc from 'tinycolor2';
import _ from 'underscore';

/**
 * Generate an rgba string from a color value and opacity.
 */
function color(value, opacity) {
    // geojs uses [0,1] color scales
    var c = tc.fromRatio(value);
    if (_.isNumber(opacity)) {
        c.setAlpha(opacity);
    }
    return c.toRgbString();
}

/**
 * Generate an rgba string from a particular component of
 * a geojs style object.  property should be 'stroke' or 'fill'.
 */
function setColorType(style, property) {
    const value = style[property + 'Color'];
    const opacity = style[property + 'Opacity'];
    const present = style[property];

    // set the color to 100% transparent if the property is off
    if (!present) {
        return color(value, 0);
    }

    return color(value, opacity);
}

/**
 * Convert properties from geojs options to annotation
 * elements that all types have in common.  At the moment,
 * this handles style information, but could be expanded
 * to handle labels, names, id's, etc.
 */
function common(annotation) {
    const style = annotation.options().style;
    const fillColor = setColorType(style, 'fill');
    const lineColor = setColorType(style, 'stroke');

    return {
        fillColor,
        lineColor
    };
}

export default common;
