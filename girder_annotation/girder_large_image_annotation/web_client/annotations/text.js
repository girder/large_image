import textDefaults from './defaults/text';

/**
 * Make a string valid for a text annotation element.  The only control
 * character that is allowed is a line feed.  Other line breaks are converted
 * to line feeds, tabs are converted to spaces, and all other control
 * characters are removed.  All other unicode is kept.
 *
 * @param {string} text The text to sanitize.
 * @param {boolean} [trim=true] If true, remove leading and trailing
 *      whitespace.  An element's text must be trimmed and not empty.
 * @returns {string} The sanitized text.  This can be an empty string.
 */
function sanitizeText(text, trim) {
    text = '' + (text === undefined || text === null ? '' : text);
    let result = '';
    // control characters are all in the basic multilingual plane, so checking
    // UTF-16 code units cannot split a surrogate pair.
    for (let i = 0; i < text.length; i += 1) {
        const code = text.charCodeAt(i);
        if (code < 0x20 || (code >= 0x7f && code <= 0x9f)) {
            if (code === 0x09) {
                result += ' ';
            } else if (code === 0x0a || (code === 0x0d && text.charCodeAt(i + 1) !== 0x0a)) {
                result += '\n';
            }
        } else {
            result += text[i];
        }
    }
    return trim === false ? result : result.trim();
}

/**
 * Get the css font used to draw a text annotation element.  The size is in
 * css pixels, so text is the same size on displays with different pixel
 * densities.  The line height is always specified in pixels so that the lines
 * of multiline text are spaced the same wherever the font is used.
 *
 * @param {object} element The text annotation element.
 * @returns {string} A css font specification.
 */
function textFont(element) {
    const fontSize = +(element || {}).fontSize > 0 ? +element.fontSize : textDefaults.fontSize;
    return `${fontSize}px/${Math.round(fontSize * 125) / 100}px sans-serif`;
}

export {
    sanitizeText,
    textFont
};
