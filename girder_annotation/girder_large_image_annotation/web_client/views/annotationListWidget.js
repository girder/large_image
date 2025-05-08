import $ from 'jquery';
import _ from 'underscore';

import {AccessType} from '@girder/core/constants';
import eventStream from '@girder/core/utilities/EventStream';
import {getCurrentUser} from '@girder/core/auth';
import {confirm} from '@girder/core/dialog';
import {getApiRoot, restRequest} from '@girder/core/rest';
import AccessWidget from '@girder/core/views/widgets/AccessWidget';
import events from '@girder/core/events';
import UserCollection from '@girder/core/collections/UserCollection';
import UploadWidget from '@girder/core/views/widgets/UploadWidget';
import View from '@girder/core/views/View';
import largeImageConfig from '@girder/large_image/views/configView';

import AnnotationCollection from '../collections/AnnotationCollection';

import annotationList from '../templates/annotationListWidget.pug';

import '../stylesheets/annotationListWidget.styl';

const AnnotationListWidget = View.extend({
    events: {
        'click .g-annotation-toggle-select': '_displayAnnotation',
        'click .g-annotation-toggle-all': '_displayAllAnnotations',
        'click .g-annotation-select': '_selectAnnotation',
        'click .g-annotation-download-selected': '_downloadSelectedAnnotations',
        'click .g-annotation-delete': '_deleteAnnotation',
        'click .g-annotation-upload': '_uploadAnnotation',
        'click .g-annotation-permissions': '_changePermissions',
        'click .g-annotation-metadata': '_annotationMetadata',
        'click .g-annotation-row'(evt) {
            var $el = $(evt.currentTarget);
            $el.find('.g-annotation-toggle-select').click();
        },
        'click .g-annotation-row a,.g-annotation-toggle-select'(evt) {
            evt.stopPropagation();
        }
    },

    initialize() {
        this._drawn = new Set();
        this._viewer = null;
        this._sort = {
            field: 'name',
            direction: 1
        };

        this.collection = this.collection || new AnnotationCollection([], {comparator: null});
        this.users = new UserCollection();

        this.listenTo(this.collection, 'all', this.render);
        this.listenTo(this.users, 'all', this.render);
        this.listenTo(eventStream, 'g:event.large_image_annotation.create', () => this.collection.fetch(null, true));
        this.listenTo(eventStream, 'g:event.large_image_annotation.remove', () => this.collection.fetch(null, true));

        restRequest({
            type: 'GET',
            url: 'annotation/folder/' + this.model.get('folderId') + '/create',
            error: null
        }).done((createResp) => {
            this.createResp = createResp;
            largeImageConfig.getConfigFile(this.model.get('folderId')).done((val) => {
                this._liconfig = val || {};
                this._confList = this._liconfig.annotationList || {
                    columns: [{
                        type: 'record',
                        value: 'name'
                    }, {
                        type: 'record',
                        value: 'creator',
                        format: 'user'
                    }, {
                        type: 'record',
                        value: 'created',
                        format: 'date'
                    }]
                };
                this.collection.comparator = _.constant(0);
                this._lastSort = this._confList.defaultSort || [{
                    type: 'record',
                    value: 'updated',
                    dir: 'up'
                }, {
                    type: 'record',
                    value: 'updated',
                    dir: 'down'
                }];
                this.collection.sortField = JSON.stringify(this._lastSort.reduce((result, e) => {
                    result.push([
                        (e.type === 'metadata' ? 'annotation.attributes.' : '') + e.value,
                        e.dir === 'down' ? 1 : -1
                    ]);
                    if (e.type === 'record') {
                        result.push([
                            `annotation.${e.value}`,
                            e.dir === 'down' ? 1 : -1
                        ]);
                    }
                    return result;
                }, []));
                this.collection.fetch({
                    itemId: this.model.id,
                    sort: this.collection.sortField || 'created',
                    sortdir: -1
                }).done(() => {
                    this._fetchUsers();
                });
            });
        });
    },

    render() {
        this.$el.html(annotationList({
            item: this.model,
            accessLevel: this.model.getAccessLevel(),
            creationAccess: this.createResp,
            annotations: this.collection,
            users: this.users,
            canDraw: this._viewer && this._viewer.annotationAPI(),
            drawn: this._drawn,
            apiRoot: getApiRoot(),
            confList: this._confList,
            AccessType
        }));
        const anySelected = this.$('.g-annotation-select input:checked').length > 0;

        ['.g-annotation-download-selected', '.g-annotation-delete', '.g-annotation-permissions'].forEach((selector) => {
            this.$(`thead ${selector}`)
                .prop('disabled', !anySelected)
                .toggleClass('disabled', !anySelected)
                .css('color', !anySelected ? 'grey' : '');
        });

        return this;
    },

    setViewer(viewer) {
        this._drawn.clear();
        this._viewer = viewer;
        return this;
    },

    _displayAnnotation(evt) {
        if (!this._viewer || !this._viewer.annotationAPI()) {
            return;
        }
        const $el = $(evt.currentTarget).closest('.g-annotation-row');
        const id = $el.data('annotationId');
        const annotation = this.collection.get(id);
        const startedOn = $el.find('.g-annotation-toggle-select i.icon-eye').length;
        if (!startedOn) {
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
        $el.find('.g-annotation-toggle-select i').toggleClass('icon-eye', !startedOn).toggleClass('icon-eye-off', !!startedOn);
        const anyOn = this.collection.some((annotation) => this._drawn.has(annotation.id));
        this.$el.find('th.g-annotation-toggle i').toggleClass('icon-eye', !!anyOn).toggleClass('icon-eye-off', !anyOn);
    },

    _displayAllAnnotations(evt) {
        if (!this._viewer || !this._viewer.annotationAPI()) {
            return;
        }
        const anyOn = this.collection.some((annotation) => this._drawn.has(annotation.id));
        this.collection.forEach((annotation) => {
            const id = annotation.id;
            let isDrawn = this._drawn.has(annotation.id);
            if (anyOn && isDrawn) {
                this._drawn.delete(id);
                this._viewer.removeAnnotation(annotation);
                isDrawn = false;
            } else if (!anyOn && !isDrawn) {
                this._drawn.add(id);
                annotation.fetch().then(() => {
                    if (this._drawn.has(id)) {
                        this._viewer.drawAnnotation(annotation);
                    }
                    return null;
                });
                isDrawn = true;
            }
            this.$el.find(`.g-annotation-row[data-annotation-id="${id}"] .g-annotation-toggle-select i`).toggleClass('icon-eye', !!isDrawn).toggleClass('icon-eye-off', !isDrawn);
        });
        this.$el.find('th.g-annotation-toggle i').toggleClass('icon-eye', !anyOn).toggleClass('icon-eye-off', !!anyOn);
    },

    _selectAnnotation(evt) {
        // Prevent event from bubbling up to the row click handler
        // that toggles the annotation on and off
        evt.stopPropagation();

        const $el = $(evt.currentTarget);
        const id = $el.parents('.g-annotation-row').data('annotationId');
        const allChecks = this.$el.find('.g-annotation-select input[type=checkbox]');
        const anySelected = this.$('.g-annotation-select input:checked').length > 0;

        this.$('thead .g-annotation-download-selected, thead .g-annotation-delete, thead .g-annotation-permissions')
            .prop('disabled', !anySelected)
            .toggleClass('disabled', !anySelected)
            .css('color', anySelected ? '' : 'grey');
        if (!id) {
            if ($el.find('input').is(':checked')) {
                allChecks.prop('checked', true);
            }
            if (!$el.find('input').is(':checked')) {
                allChecks.prop('checked', false);
            }
        }
    },

    _downloadSelectedAnnotations(evt) {
        evt.preventDefault();

        const selectedAnnotations = this.$('.g-annotation-select input:checked')
            .closest('.g-annotation-row')
            .map((_, el) => $(el).data('annotationId'))
            .get();

        selectedAnnotations.forEach((id) => {
            const annotation = this.collection.get(id);
            if (annotation) {
                annotation.fetch().then(() => {
                    const url = `${getApiRoot()}/annotation/${annotation.id}`;
                    const downloadAnchor = document.createElement('a');
                    downloadAnchor.setAttribute('href', url);
                    downloadAnchor.setAttribute('download', `${annotation.get('annotation').name}.json`);
                    document.body.appendChild(downloadAnchor);
                    downloadAnchor.click();
                    document.body.removeChild(downloadAnchor);
                    return null;
                });
            }
        });
    },

    _deleteAnnotation(evt) {
        const $el = $(evt.currentTarget);
        const id = $el.parents('.g-annotation-row').data('annotationId');
        const checkedAnnotations = this.$el.find('.g-annotation-select input[type=checkbox]:checked');
        const checkedAnnotationIds = [];
        if (!id) {
            for (let i = 0; i < checkedAnnotations.length; i++) {
                const annotationId = $(checkedAnnotations[i]).parents('.g-annotation-row').data('annotationId');
                checkedAnnotationIds.push(annotationId);
            }
            if (checkedAnnotations.length !== 0) {
                confirm({
                    text: `<h3>Are you sure you want to delete the following annotations?</h3>
                        <ul
                          style="max-height: 200px; padding-left: 0; overflow-y: auto;"
                        >${_.map(checkedAnnotationIds, (annotationId) => {
        const model = this.collection.get(annotationId);
        return `<li>${_.escape(model.get('annotation').name)}</li>`;
    }).join('')}</ul>`,
                    escapedHtml: true,
                    yesText: 'Delete',
                    confirmCallback: () => {
                        for (let i = 0; i < checkedAnnotationIds.length; i++) {
                            this._drawn.delete(checkedAnnotationIds[i]);
                            const model = this.collection.get(checkedAnnotationIds[i]);
                            model.destroy();
                        }
                    }
                });
                return;
            }
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
            parent: this.model,
            parentType: 'item',
            parentView: this,
            multiFile: true,
            otherParams: {
                reference: JSON.stringify({
                    identifier: 'LargeImageAnnotationUpload',
                    itemId: this.model.id,
                    fileId: this.model.get('largeImage') && this.model.get('largeImage').fileId,
                    userId: (getCurrentUser() || {}).id
                })
            }
        }).on('g:uploadFinished', () => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Uploaded annotations.',
                type: 'success',
                timeout: 4000
            });
            this.collection.fetch(null, true);
        }, this);
        this._uploadWidget = uploadWidget;
        uploadWidget.render();
    },

    _changePermissions(evt) {
        const $el = $(evt.currentTarget);
        let id = $el.parents('.g-annotation-row').data('annotationId');
        const checkedAnnotations = this.$el.find('.g-annotation-select input[type=checkbox]:checked');
        const checkedAnnotationIds = [];
        if (!id && this.collection.length === 1) {
            id = this.collection.at(0).id;
        }
        const model = id ? this.collection.get(id) : this.collection.at(0).clone();
        if (!id) {
            // if id is not set, override widget's saveAccessList with selected annotations
            for (let i = 0; i < checkedAnnotations.length; i++) {
                const annotationId = $(checkedAnnotations[i]).parents('.g-annotation-row').data('annotationId');
                checkedAnnotationIds.push(annotationId);
            }
            model.get('annotation').name = 'Selected Annotations';
            model.save = () => {};
            model.updateAccess = () => {
                const access = {
                    access: model.get('access'),
                    public: model.get('public'),
                    publicFlags: model.get('publicFlags')
                };
                for (let i = 0; i < checkedAnnotationIds.length; i++) {
                    const selectedModel = this.collection.get(checkedAnnotationIds[i]);
                    if (!selectedModel) {
                        continue;
                    }
                    selectedModel.set(access);
                    selectedModel.updateAccess();
                }
                this.collection.fetch(null, true);
                model.trigger('g:accessListSaved');
            };
        }
        new AccessWidget({
            el: $('#g-dialog-container'),
            type: 'annotation',
            hideRecurseOption: true,
            parentView: this,
            model,
            noAccessFlag: true
        }).on('g:accessListSaved', () => {
            this.collection.fetch(null, true);
        });
    },

    _fetchUsers() {
        this.collection.each((model) => {
            this.users.add({_id: model.get('creatorId')});
            this.users.add({_id: model.get('updatedId')});
        });
        $.when.apply($, this.users.map((model) => {
            return model.fetch();
        })).always(() => {
            this.render();
        });
    }
});

export default AnnotationListWidget;
