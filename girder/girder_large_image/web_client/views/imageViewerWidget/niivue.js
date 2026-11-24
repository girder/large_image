import $ from 'jquery';

import ImageViewerWidget from './base';

// ponytail: loaded from a CDN like openseadragon, since webpack 3 cannot parse
// NiiVue's ES2022 modules. uikit's +esm imports niivue@NIIVUE, so both share
// one module instance. Bundle via npm when the build moves past webpack 3.
const NIIVUE = 'https://cdn.jsdelivr.net/npm/@niivue/niivue@1.0.0-rc.237/+esm';
const UIKIT = 'https://cdn.jsdelivr.net/npm/@niivue/uikit@1.0.0-rc.241/+esm';
// eslint-disable-next-line no-new-func
const importUrl = new Function('url', 'return import(url)');

var NiivueImageViewerWidget = ImageViewerWidget.extend({
    initialize: function (settings) {
        $.when(
            ImageViewerWidget.prototype.initialize.call(this, settings),
            importUrl(NIIVUE),
            importUrl(UIKIT)
        )
            .then((info, nv, uikit) => this._start(nv, uikit))
            .fail(() => this.$el.text('NiiVue failed to load.'));
    },

    // no async/await: Girder 3's babel 6 build would need regeneratorRuntime
    _start: function (nv, uikit) {
        if (this.deleted) {
            return;
        }
        const canvas = document.createElement('canvas');
        this.el.appendChild(canvas);
        return nv.createSlideView(canvas, {
            // as in niivue.com's demo-ext-tile: left drag pans, right drag zooms to a box
            controller: {
                primaryDragMode: nv.DRAG_MODE.pan,
                secondaryDragMode: nv.DRAG_MODE.roiSelection
            },
            overlayStyle: {isRulerVisible: true}
        }).then((view) => {
            if (this.deleted) {
                view.destroy();
                return;
            }
            this.view = view;
            this.slide = nv.NVSlide.fromSource(this._source());
            view.setSlide(this.slide);
            this._toggleMinimap = (on) => {
                if (this.detachMinimap) {
                    this.detachMinimap();
                }
                this.detachMinimap = on ? uikit.attachSlideMinimap(view, {corner: 'top-right'}) : null;
            };
            this._toggleMinimap(true);
            this._addToolbar();
            this.trigger('g:imageRendered', this);
        });
    },

    _addToolbar: function () {
        const view = this.view;
        const zoom = (factor) => {
            const screen = view.screen();
            this.slide.zoomBy(factor, screen.widthCss / 2, screen.heightCss / 2, screen);
        };
        const bar = document.createElement('div');
        bar.className = 'li-niivue-toolbar';
        const button = (text, title, onclick) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = text;
            b.title = title;
            b.setAttribute('aria-label', title);
            b.onclick = onclick;
            bar.appendChild(b);
        };
        const toggle = (text, checked, onchange) => {
            const label = document.createElement('label');
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = checked;
            input.onchange = () => onchange(input.checked);
            label.append(input, text);
            bar.appendChild(label);
        };
        button('+', 'Zoom in', () => zoom(2));
        button('−', 'Zoom out', () => zoom(0.5));
        button('⌂', 'Fit slide', () => view.fit());
        toggle('Scale bar', true, (on) => { view.overlayStyle = {isRulerVisible: on}; });
        toggle('Minimap', true, this._toggleMinimap);
        this.el.appendChild(bar);
    },

    /* An NVSlide tile source over large_image's /tiles/zxy pyramid: z=0 is
     * the coarsest level, NVSlide wants finest first. */
    _source: function () {
        const levels = [];
        for (let z = this.levels - 1; z >= 0; z--) {
            const scale = 2 ** (this.levels - 1 - z);
            // floor matches large_image's edge-crop size (tilesource/base.py)
            const width = Math.max(1, Math.floor(this.sizeX / scale));
            const height = Math.max(1, Math.floor(this.sizeY / scale));
            const columns = Math.ceil(width / this.tileWidth);
            const rows = Math.ceil(height / this.tileHeight);
            const tiles = [];
            for (let y = 0; y < rows; y++) {
                for (let x = 0; x < columns; x++) {
                    tiles.push({
                        x,
                        y,
                        width: Math.min(this.tileWidth, width - x * this.tileWidth),
                        height: Math.min(this.tileHeight, height - y * this.tileHeight)
                    });
                }
            }
            levels.push({
                index: levels.length,
                z,
                width,
                height,
                downsample: scale,
                tileWidth: this.tileWidth,
                tileHeight: this.tileHeight,
                columns,
                rows,
                // createImageBitmap sniffs the bytes, so PNG tiles decode too
                codec: 'image/jpeg',
                tiles
            });
        }
        const {mm_x: mmX, mm_y: mmY} = this.metadata;
        const manifest = {
            id: this.itemId,
            name: this.itemId,
            width: this.sizeX,
            height: this.sizeY,
            dtype: 'uint8',
            channels: 'encoded-rgb',
            displayYAxis: 'down',
            pixelSpacingMM: mmX && mmY ? [mmX, mmY] : undefined,
            levels
        };
        return {
            manifest,
            bind: () => {},
            fetchTileBytes: (level, tile, label, signal) => {
                const url = this._getTileUrl(level.z, tile.x, tile.y, {edge: 'crop'});
                return fetch(url, {signal}).then((response) => {
                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status} for ${url}`);
                    }
                    return response.arrayBuffer();
                }).then((bytes) => new Uint8Array(bytes));
            }
        };
    },

    destroy: function () {
        this.deleted = true;
        if (this.detachMinimap) {
            this.detachMinimap();
        }
        if (this.view) {
            this.view.destroy(); // also disposes the slide
            this.view = this.slide = null;
        }
        ImageViewerWidget.prototype.destroy.call(this);
    }
});

export default NiivueImageViewerWidget;
