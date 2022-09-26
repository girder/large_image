import $ from 'jquery';
import { AccessType } from '@girder/core/constants';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import { wrap } from '@girder/core/utilities/PluginUtils';
import ItemView from '@girder/core/views/body/ItemView';
import View from '@girder/core/views/View';

/* This should all be refactored for codemirror 6 */
import jsyaml from 'js-yaml';
import jsonlint from 'jsonlint-mod';
import CodeMirror from 'codemirror';
import 'codemirror/lib/codemirror.css';
import 'codemirror/addon/lint/lint.css';
import 'codemirror/addon/fold/foldgutter.css';

import 'codemirror/addon/fold/brace-fold';
import 'codemirror/addon/fold/foldcode';
import 'codemirror/addon/fold/foldgutter';
import 'codemirror/addon/lint/lint';
import 'codemirror/addon/lint/json-lint';
import 'codemirror/addon/lint/yaml-lint';
import 'codemirror/mode/javascript/javascript';
import 'codemirror/mode/yaml/yaml';

import itemViewCodemirror from '../templates/itemViewCodemirror.pug';
import '../stylesheets/itemViewCodemirror.styl';

/* codemirror expects linters to be window level objects */
window.jsonlint = jsonlint;
window.jsyaml = jsyaml;

const Formats = {
    'application/json': {
        name: 'JSON',
        mode: {
            name: 'javascript',
            json: true
        },
        validator: JSON.parse,
        format: (val) => JSON.stringify(val, undefined, 2)
    },
    'text/yaml': {
        name: 'YAML',
        mode: 'yaml',
        validator: jsyaml.load,
        /* This removes comments.  Maybe the yaml package could be used to not
         * do so, or we could use sort of regex parsing, but both of those are
         * more work. */
        format: (val) => jsyaml.dump(val, {lineWidth: -1, noRefs: true})
    }
};
Formats['text/x-yaml'] = Formats['text/yaml'];

var CodemirrorEditWidget = View.extend({
    events: {
        'click .g-view-codemirror-revert-button': 'revert',
        'click .g-view-codemirror-format-button': 'format',
        'click .g-view-codemirror-save-button': 'save'
    },

    initialize: function (settings) {
        this.file = settings.file;
        this.accessLevel = settings.accessLevel;
        this.mimeType = settings.mimeType;
        restRequest({
            url: `file/${this.file.id}/download`,
            processData: false,
            dataType: 'text',
            error: null
        }).done((resp) => {
            this._contents = resp;
            this._lastSave = this._contents;
            this.render();
        });
    },

    render: function () {
        this.$el.html(itemViewCodemirror({
            formatName: Formats[this.mimeType].name,
            accessLevel: this.accessLevel,
            AccessType: AccessType
        }));
        this.code = CodeMirror(this.$el.find('.editor')[0], {
            value: this._contents,
            mode: Formats[this.mimeType].mode,
            lineNumbers: true,
            gutters: ['CodeMirror-lint-markers'],
            lint: true,
            readOnly: this.accessLevel < AccessType.WRITE
        });
        return this;
    },

    format: function () {
        let content = this.code.getValue();
        let validated;
        try {
            validated = Formats[this.mimeType].validator(content);
        } catch (e) {
            events.trigger('g:alert', {
                text: 'Contents do not validate. ' + e,
                type: 'warning'
            });
            return;
        }
        try {
            content = Formats[this.mimeType].format(validated);
        } catch (e) {
            events.trigger('g:alert', {
                text: 'Contents do not format. ' + e,
                type: 'warning'
            });
            return;
        }
        this.code.setValue(content);
    },

    revert: function () {
        this.code.setValue(this._contents);
    },

    save: function () {
        const content = this.code.getValue();
        try {
            Formats[this.mimeType].validator(content);
        } catch (e) {
            events.trigger('g:alert', {
                text: 'Contents do not validate. ' + e,
                type: 'warning'
            });
            return;
        }
        if (content !== this._lastSave) {
            this.file.updateContents(content);
            // functional, this just marks the parent item's updated time
            this.parentView.model._sendMetadata({});
            this._lastSave = content;
        }
    }
});

wrap(ItemView, 'render', function (render) {
    this.once('g:rendered', () => {
        if (this.codemirrorEditWidget) {
            this.codemirrorEditWidget.remove();
        }
        if (this.fileListWidget.collection.models.length !== 1) {
            return;
        }
        const firstFile = this.fileListWidget.collection.models[0];
        const mimeType = firstFile.get('mimeType');
        if (!Formats[mimeType] || firstFile.get('size') > 100000) {
            return;
        }
        this.codemirrorEditWidget = new CodemirrorEditWidget({
            el: $('<div>', {class: 'g-codemirror-edit-container'})
                .insertAfter(this.$('.g-item-files')),
            file: firstFile,
            parentView: this,
            mimeType: mimeType,
            accessLevel: this.accessLevel
        });
    });
    return render.call(this);
});

export default ItemView;
