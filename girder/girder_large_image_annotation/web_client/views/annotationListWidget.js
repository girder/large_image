import _ from 'underscore';

import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';
import { getApiRoot } from '@girder/core/rest';
import AccessWidget from '@girder/core/views/widgets/AccessWidget';
import UserCollection from '@girder/core/collections/UserCollection';
import View from '@girder/core/views/View';

import AnnotationCollection from '../collections/AnnotationCollection';

import annotationList from '../templates/annotationListWidget.pug';

import '../stylesheets/annotationListWidget.styl';

const AnnotationListWidget = View.extend({
    events: {
        'change .g-annotation-toggle': '_displayAnnotation',
        'click .g-annotation-delete': '_deleteAnnotation',
        'click .g-annotation-permissions': '_changePermissions',
        'click .g-annotation-row'(evt) {
            var $el = $(evt.currentTarget);
            $el.find('.g-annotation-toggle > input').click();
        },
        'click .g-annotation-row a,input'(evt) {
            evt.stopPropagation();
        }
    },

    initialize() {
        this._drawn = new Set();
        this._viewer = null;
        this._sort = {
            'field': 'name',
            'direction': 1
        };

        this.collection = this.collection || new AnnotationCollection([], {comparator: null});
        this.users = new UserCollection();

        this.listenTo(this.collection, 'all', this.render);
        this.listenTo(this.users, 'all', this.render);

        this.collection.fetch({
            itemId: this.model.id,
            sort: 'created',
            sortdir: -1
        }).done(() => {
            this._fetchUsers();
        });
    },

    render() {
        this.$el.html(annotationList({
            annotations: this.collection,
            users: this.users,
            canDraw: this._viewer && this._viewer.annotationAPI(),
            drawn: this._drawn,
            apiRoot: getApiRoot(),
            AccessType
        }));
        return this;
    },

    setViewer(viewer) {
        this._drawn.clear();
        this._viewer = viewer;
        return this;
    },

    _displayAnnotation(evt) {
        const $el = $(evt.currentTarget);
        const id = $el.parent().data('annotationId');
        const annotation = this.collection.get(id);
        if ($el.find('input').prop('checked')) {
            this._drawn.add(id);
            this._viewer.drawAnnotation(annotation);
        } else {
            this._drawn.delete(id);
            this._viewer.removeAnnotation(annotation);
        }
    },

    _deleteAnnotation(evt) {
        const $el = $(evt.currentTarget);
        const id = $el.parents('.g-annotation-row').data('annotationId');
        const model = this.collection.get(id);

        confirm({
            text: `Are you sure you want to delete <b>${_.escape(model.get('annotation').name)}</b>?`,
            escapedHtml: true,
            yesText: 'Delete',
            confirmCallback: () => {
                this._drawn.delete(id);
                model.destroy();
            }
        });
    },

    _changePermissions(evt) {
        const $el = $(evt.currentTarget);
        const id = $el.parents('.g-annotation-row').data('annotationId');
        const model = this.collection.get(id);
        new AccessWidget({
            el: $('#g-dialog-container'),
            type: 'annotation',
            hideRecurseOption: true,
            parentView: this,
            model
        }).on('g:accessListSaved', () => {
            this.collection.fetch(null, true);
        });
    },

    _fetchUsers() {
        this.collection.each((model) => {
            this.users.add({'_id': model.get('creatorId')});
        });
        $.when.apply($, this.users.map((model) => {
            return model.fetch();
        })).always(() => {
            this.render();
        });
    }
});

export default AnnotationListWidget;
