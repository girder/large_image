import $ from 'jquery';
import _ from 'underscore';

import { AccessType } from '@girder/core/constants';
import { confirm } from '@girder/core/dialog';
import { getApiRoot, restRequest } from '@girder/core/rest';
import AccessWidget from '@girder/core/views/widgets/AccessWidget';
import events from '@girder/core/events';
import FileModel from '@girder/core/models/FileModel';
import UserCollection from '@girder/core/collections/UserCollection';
import UploadWidget from '@girder/core/views/widgets/UploadWidget';
import View from '@girder/core/views/View';

import AnnotationCollection from '../collections/AnnotationCollection';

import annotationList from '../templates/annotationListWidget.pug';

import '../stylesheets/annotationListWidget.styl';

const AnnotationListWidget = View.extend({
    events: {
        'change .g-annotation-toggle': '_displayAnnotation',
        'click .g-annotation-delete': '_deleteAnnotation',
        'click .g-annotation-upload': '_uploadAnnotation',
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
            item: this.model,
            accessLevel: this.model.getAccessLevel(),
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
            annotation.fetch().then(() => {
                if (this._drawn.has(id)) {
                    this._viewer.drawAnnotation(annotation);
                }
                return null;
            });
        } else {
            this._drawn.delete(id);
            this._viewer.removeAnnotation(annotation);
        }
    },

    _deleteAnnotation(evt) {
        const $el = $(evt.currentTarget);
        const id = $el.parents('.g-annotation-row').data('annotationId');
        if (!id) {
            confirm({
                text: `Are you sure you want to delete <b>ALL</b> annotations?`,
                escapedHtml: true,
                yesText: 'Delete',
                confirmCallback: () => {
                    restRequest({
                        url: `annotation/item/${this.model.id}`,
                        method: 'DELETE'
                    }).done(() => {
                        this.collection.fetch(null, true);
                    });
                }
            });
            return;
        }
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

    _uploadAnnotation() {
        var uploadWidget = new UploadWidget({
            el: $('#g-dialog-container'),
            title: 'Upload Annotation',
            parent: this._makeUploadParent(),
            parentType: 'file', // invokes special upload widget code
            parentView: this,
            multiFile: true
        }).on('g:uploadFinished', function () {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Uploaded annotations.',
                type: 'success',
                timeout: 4000
            });
        }, this);
        this._uploadWidget = uploadWidget;
        uploadWidget.render();
        uploadWidget.on('g:uploadFinished', () => {
            this.collection.fetch(null, true);
        });
    },

    _makeUploadParent() {
        var parent = new FileModel();
        parent.updateContents = (data) => {
            restRequest({
                url: `annotation/item/${this.model.id}`,
                method: 'POST',
                data: data,
                contentType: 'application/json',
                processData: false
            }).done((resp) => {
                parent.name = this.model.name();
                parent.trigger('g:upload.progress', {
                    startByte: 0,
                    loaded: data.size,
                    total: data.size,
                    file: parent
                });
                this._uploadWidget.parent = this._makeUploadParent();
                parent.trigger('g:upload.complete');
            }).fail((resp) => {
                this._uploadWidget.parent = this._makeUploadParent();
                parent.trigger('g:upload.error', {
                    message: 'An error occurred while uploading, check console.',
                    response: resp
                });
            });
        };
        parent.name = () => {
            return this.model.name();
        };
        parent.get = () => {
            return this.model.get.apply(this.model, arguments);
        };
        return parent;
    },

    _changePermissions(evt) {
        const $el = $(evt.currentTarget);
        let id = $el.parents('.g-annotation-row').data('annotationId');
        if (!id && this.collection.length === 1) {
            id = this.collection.at(0).id;
        }
        const model = id ? this.collection.get(id) : this.collection.at(0).clone();
        if (!id) {
            // if id is not set, override widget's saveAccessList
            model.get('annotation').name = 'All Annotations';
            model.save = () => {};
            model.updateAccess = () => {
                const access = {
                    access: model.get('access'),
                    public: model.get('public'),
                    publicFlags: model.get('publicFlags')
                };
                this.collection.each((loopmodel) => {
                    loopmodel.set(access);
                    loopmodel.updateAccess();
                });
                this.collection.fetch(null, true);
                model.trigger('g:accessListSaved');
            };
        }
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
