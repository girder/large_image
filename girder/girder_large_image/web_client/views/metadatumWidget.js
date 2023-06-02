import _ from 'underscore';

import View from '@girder/core/views/View';
import {AccessType} from '@girder/core/constants';
import events from '@girder/core/events';

var MetadatumWidget = View.extend({
    className: 'g-widget-metadata-row',

    events: {
        'click .g-widget-metadata-edit-button': 'editMetadata'
    },

    initialize: function (settings) {
        if (!_.has(this.parentView.modes, settings.mode)) {
            throw new Error('Unsupported metadatum mode ' + settings.mode + ' detected.');
        }

        this.mode = settings.mode;
        this.key = settings.key;
        this.value = settings.value;
        this.accessLevel = settings.accessLevel;
        this.parentView = settings.parentView;
        this.fieldName = settings.fieldName;
        this.apiPath = settings.apiPath;
        this.onMetadataEdited = settings.onMetadataEdited;
        this.onMetadataAdded = settings.onMetadataAdded;
    },

    _validate: function (from, to, value) {
        var newMode = this.parentView.modes[to];

        if (_.has(newMode, 'validation') &&
            _.has(newMode.validation, 'from') &&
            _.has(newMode.validation.from, from)) {
            var validate = newMode.validation.from[from][0];
            var msg = newMode.validation.from[from][1];

            if (!validate(value)) {
                events.trigger('g:alert', {
                    text: msg,
                    type: 'warning'
                });
                return false;
            }
        }

        return true;
    },

    // @todo too much duplication with editMetadata
    toggleEditor: function (event, newEditorMode, existingEditor, overrides) {
        var fromEditorMode = 'simple';
        var newValue = (overrides || {}).value || existingEditor.$el.attr('g-value');
        if (!this._validate(fromEditorMode, newEditorMode, newValue)) {
            return;
        }

        var row = existingEditor.$el;
        existingEditor.destroy();
        row.addClass('editing').empty();

        var opts = _.extend({
            el: row,
            item: this.parentView.item,
            key: row.attr('g-key'),
            value: row.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this,
            fieldName: this.fieldName,
            apiPath: this.apiPath,
            onMetadataEdited: this.onMetadataEdited,
            onMetadataAdded: this.onMetadataAdded
        }, overrides || {});

        this.parentView.modes[newEditorMode].editor(opts).render();
    },

    editMetadata: function (event) {
        this.$el.addClass('editing');
        this.$el.empty();

        var opts = {
            item: this.parentView.item,
            key: this.$el.attr('g-key'),
            value: this.$el.attr('g-value'),
            accessLevel: this.accessLevel,
            newDatum: false,
            parentView: this,
            fieldName: this.fieldName,
            apiPath: this.apiPath,
            onMetadataEdited: this.onMetadataEdited,
            onMetadataAdded: this.onMetadataAdded
        };

        // If they're trying to open false, null, 6, etc which are not stored as strings
        if (this.mode === 'json') {
            try {
                var jsonValue = JSON.parse(this.$el.attr('g-value'));

                if (jsonValue !== undefined && !_.isObject(jsonValue)) {
                    opts.value = jsonValue;
                }
            } catch (e) {}
        }

        this.parentView.modes[this.mode].editor(opts)
            .render()
            .$el.appendTo(this.$el);
    },

    render: function () {
        this.$el.attr({
            'g-key': this.key,
            'g-value': _.bind(this.parentView.modes[this.mode].displayValue, this)()
        }).empty();

        this.$el.html(this.parentView.modes[this.mode].template({
            key: this.key,
            value: _.bind(this.parentView.modes[this.mode].displayValue, this)(),
            accessLevel: this.accessLevel,
            AccessType: AccessType
        }));

        return this;
    }
});

export default MetadatumWidget;
