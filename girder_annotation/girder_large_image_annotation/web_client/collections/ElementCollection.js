import Backbone from 'backbone';

import ElementModel from '../models/ElementModel';

export default Backbone.Collection.extend({
    initialize: function () {
        this.on('add', this.track_addition, this);
        this.on('remove', this.track_remove, this);
        this.on('change', this.track_change, this);
    },

    model: ElementModel,
    comparator: undefined,

    track_addition: function (element) {
        if (!this.annotation || !this.annotation.get || !this.annotation.get('_version')) {
            return;
        }
        if (!this.annotation._changeLog) {
            this.annotation._changeLog = {};
        }
        this.annotation._changeLog[element.id] = {op: 'add', path: `elements/id:${element.id}`, value: element.toJSON()};
    },

    track_remove: function (element) {
        if (!this.annotation || !this.annotation.get || !this.annotation.get('_version')) {
            return;
        }
        if (!this.annotation._changeLog) {
            this.annotation._changeLog = {};
        }
        if (this.annotation._changeLog[element.id] && this.annotation._changeLog[element.id].op === 'add') {
            delete this.annotation._changeLog[element.id];
        } else {
            this.annotation._changeLog[element.id] = {op: 'remove', path: `elements/id:${element.id}`};
        }
    },
    track_change: function (element) {
        if (!this.annotation || !this.annotation.get || !this.annotation.get('_version')) {
            return;
        }
        if (!this.annotation._changeLog) {
            this.annotation._changeLog = {};
        }
        this.annotation._changeLog[element.id] = {op: 'replace', path: `elements/id:${element.id}`, value: element.toJSON()};
    }
});
