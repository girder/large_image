/**
 * Given metadata on a tile source, a GeoJS tileLayer,  and a set of options,
 * add a function to the layer `setFrameQuad(<frame>)` that will, if possible,
 * set the baseQuad to a cropped section of an image that contains excerpts of
 * all frames.
 *
 * @param {object} tileinfo The metadata of the source image.  This expects
 *   ``sizeX`` and ``sizeY`` to be the width and height of the image and
 *   ``frames`` to contain a list of the frames of the image or be undefined if
 *   there is only one frame.
 * @param {geo.tileLayer} layer The GeoJS layer to add the function to.  This
 *   is also used to get a maximal texture size if the layer is a webGL
 *   layer.
 * @param {object} options Additional options for the function.  This must
 *   minimally include ``baseUrl``.
 * @param {string} options.baseUrl The reference to the tile endpoint, e.g.,
 *   <url>/api/v1/item/<item id>/tiles.
 * @param {string} [options.format='encoding=JPEG&jpegQuality=85&jpegSubsampling=1']
 *   The compression and format for the texture.
 * @param {string} [options.query] Additional query options to add to the
 *   tile_frames endpoint, e.g. 'style={"min":"min","max":"max"}'.  Do not
 *   include framesAcross or frameList.  You must specify 'cache=true' if
 *   that is desired.
 * @param {number} [options.frameBase=0] Starting frame number used.
 * @param {number} [options.frameStride=1] Only use ever ``frameStride`` frame
 *   of the image.
 * @param {number} [options.maxTextureSize] Limit the maximum texture size to a
 *   square of this size.  The size is also limited by the WebGL maximum
 *   size for webgl-based layers or 16384 for canvas-based layers.
 * @param {number} [options.maxTextures=1] If more than one, allow multiple
 *   textures to increase the size of the individual frames.  The number of
 *   textures will be capped by ``maxTotalTexturePixels`` as well as this
 *   number.
 * @param {number} [options.maxTotalTexturePixels=1073741824] Limit the
 *   maximum texture size and maximum number of textures so that the combined
 *   set does not exceed this number of pixels.
 * @param {number} [options.alignment=16] Individual frames are buffer to an
 *   alignment of this maxy pixels.  If JPEG compression is used, this should
 *   be 8 for monochrome images or jpegs without subsampling, or 16 for jpegs
 *   with moderate subsampling to avoid compression artifacts from leaking
 *   between frames.
 * @param {number} [options.adjustMinLevel=true] If truthy, adjust the tile
 *   layer's minLevel after the quads are loaded.
 * @param {number} [options.maxFrameSize] If set, limit the maximum width and
 *   height of an individual frame to this value.
 * @param {string} [options.crossOrigin] If specified, use this as the
 *   crossOrigin policy for images.
 */
function setFrameQuad(tileinfo, layer, options) {
    layer.setFrameQuad = function () { };
    if (!tileinfo || !tileinfo.sizeX || !tileinfo.sizeY || !options || !options.baseUrl) {
        return;
    }
    let maxTextureSize;
    try {
        maxTextureSize = layer.renderer()._maxTextureSize || layer.renderer().constructor._maxTextureSize;
    } catch (err) { }
    const w = tileinfo.sizeX,
        h = tileinfo.sizeY,
        maxTotalPixels = options.maxTotalTexturePixels || 1073741824,
        alignment = options.alignment || 16;
    let numFrames = (tileinfo.frames || []).length || 1,
        texSize = maxTextureSize || 16384,
        textures = options.maxTextures || 1;
    const frames = [];
    for (let fidx = options.frameBase || 0; fidx < numFrames; fidx += options.frameStride || 1) {
        frames.push(fidx);
    }
    numFrames = frames.length;
    if (numFrames === 0 || !Object.getOwnPropertyDescriptor(layer, 'baseQuad')) {
        return;
    }
    texSize = Math.min(texSize, options.maxTextureSize || texSize);
    while (texSize ** 2 > maxTotalPixels) {
        texSize /= 2;
    }
    while (textures && texSize ** 2 * textures > maxTotalPixels) {
        textures -= 1;
    }
    let fw, fh, fhorz, fvert;
    /* Iterate in case we can reduce the number of textures or the texture
     * size */
    while (true) {
        const f = Math.ceil(numFrames / textures); // frames per texture
        const texScale2 = texSize ** 2 / f / w / h;
        // frames across the texture
        fhorz = Math.ceil(texSize / (Math.floor(w * texScale2 ** 0.5 / alignment) * alignment));
        fvert = Math.ceil(texSize / (Math.floor(h * texScale2 ** 0.5 / alignment) * alignment));
        // tile sizes
        fw = Math.floor(texSize / fhorz / alignment) * alignment;
        fh = Math.floor(texSize / fvert / alignment) * alignment;
        if (options.maxFrameSize) {
            const maxFrameSize = Math.floor(options.maxFrameSize / alignment) * alignment;
            fw = Math.min(fw, maxFrameSize);
            fh = Math.min(fh, maxFrameSize);
        }
        if (fw > w) {
            fw = Math.ceil(w / alignment) * alignment;
        }
        if (fh > h) {
            fh = Math.ceil(h / alignment) * alignment;
        }
        // shrink one dimension so account for aspect ratio
        fw = Math.min(Math.ceil(fw * w / h / alignment) * alignment, fw);
        fh = Math.min(Math.ceil(fw * h / w / alignment) * alignment, fh);
        // recompute frames across the texture
        fhorz = Math.floor(texSize / fw);
        fvert = Math.min(Math.floor(texSize / fh), Math.ceil(numFrames / fhorz));
        // check if we are not using all textires or are using less than a
        // quarter of one texture.  If not, stop, if so, reduce and recalculate
        if (textures > 1 && numFrames <= fhorz * fvert * (textures - 1)) {
            textures -= 1;
            continue;
        }
        if (fhorz >= 2 && Math.ceil(f / Math.floor(fhorz / 2)) * fh <= texSize / 2) {
            texSize /= 2;
            continue;
        }
        break;
    }
    // used area of each tile
    const usedw = Math.floor(w / Math.max(w / fw, h / fh)),
        usedh = Math.floor(h / Math.max(w / fw, h / fh));
    // get the set of texture images
    const status = {
        tileinfo: tileinfo,
        options: options,
        images: [],
        src: [],
        quads: [],
        frames: frames,
        framesToIdx: {}
    };
    if (tileinfo.tileWidth && tileinfo.tileHeight) {
        // report that tiles below this level are not needed
        status.minLevel = Math.ceil(Math.log(Math.min(usedw / tileinfo.tileWidth, usedh / tileinfo.tileHeight)) / Math.log(2));
    }
    frames.forEach((frame, idx) => { status.framesToIdx[frame] = idx; });
    for (let idx = 0; idx < textures; idx += 1) {
        const img = new Image();
        if (options.baseUrl.indexOf(':') >= 0 && options.baseUrl.indexOf('/') === options.baseUrl.indexOf(':') + 1) {
            img.crossOrigin = options.crossOrigin || 'anonymous';
        }
        const frameList = frames.slice(idx * fhorz * fvert, (idx + 1) * fhorz * fvert);
        let src = `${options.baseUrl}/tile_frames?framesAcross=${fhorz}&width=${fw}&height=${fh}&fill=corner:black&exact=false`;
        if (frameList.length !== (tileinfo.frames || []).length) {
            src += `&frameList=${frameList.join(',')}`;
        }
        src += '&' + (options.format || 'encoding=JPEG&jpegQuality=85&jpegSubsampling=1').replace(/(^&|^\?|\?$|&$)/g, '');
        if (options.query) {
            src += '&' + options.query.replace(/(^&|^\?|\?$|&$)/g, '');
        }
        status.src.push(src);
        if (idx === textures - 1) {
            img.onload = function () {
                status.loaded = true;
                if (layer._options && layer._options.minLevel !== undefined && (options.adjustMinLevel === undefined || options.adjustMinLevel) && status.minLevel && status.minLevel > layer._options.minLevel) {
                    layer._options.minLevel = Math.min(layer._options.maxLevel, status.minLevel);
                }
            };
        } else {
            ((idx) => {
                img.onload = function () {
                    status.images[idx + 1].src = status.src[idx + 1];
                };
            })(idx);
        }
        status.images.push(img);
        // the last image can have fewer frames than the other images
        const f = frameList.length;
        const ivert = Math.ceil(f / fhorz),
            ihorz = Math.min(f, fhorz);
        frameList.forEach((frame, fidx) => {
            const quad = {
                // z = -1 to place under other tile layers
                ul: {x: 0, y: 0, z: -1},
                // y coordinate is inverted
                lr: {x: w, y: -h, z: -1},
                crop: {
                    x: w,
                    y: h,
                    left: (fidx % ihorz) * fw,
                    top: (ivert - Math.floor(fidx / ihorz)) * fh - usedh,
                    right: (fidx % ihorz) * fw + usedw,
                    bottom: (ivert - Math.floor(fidx / ihorz)) * fh
                },
                image: img
            };
            status.quads.push(quad);
        });
    }
    status.images[0].src = status.src[0];

    layer.setFrameQuad = function (frame) {
        if (status.framesToIdx[frame] !== undefined) {
            layer.baseQuad = Object.assign({}, status.quads[status.framesToIdx[frame]]);
            status.frame = frame;
        }
    };
    layer.setFrameQuad.status = status;
}

export default setFrameQuad;
