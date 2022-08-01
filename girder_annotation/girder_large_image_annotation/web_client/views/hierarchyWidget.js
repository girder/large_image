import $ from 'jquery';

import { wrap } from '@girder/core/utilities/PluginUtils';
import { restRequest } from '@girder/core/rest';
import AccessWidget from '@girder/core/views/widgets/AccessWidget';
import HierarchyWidget from '@girder/core/views/widgets/HierarchyWidget';
import UserCollection from '@girder/core/collections/UserCollection';

import AnnotationCollection from '../collections/AnnotationCollection';

wrap(HierarchyWidget, 'initialize', function (initialize, settings) {
    initialize.call(this, settings);

    if (this.parentModel.get('_modelType') === 'folder') {
        fetchCollections(this, this.parentModel.id);
    }
    this.folderListView.on('g:folderClicked', () => {
        fetchCollections(this, this.parentModel.id);
        addAccessControl(this);
    });
});

wrap(HierarchyWidget, 'render', function (render) {
    render.call(this);

    if (this.parentModel.get('_modelType') === 'folder' && this.recurseCollection) {
        addAccessControl(this);
    }
});

function fetchCollections(root, folderId) {
    restRequest({
        type: 'GET',
        url: 'annotation/folder/' + folderId + '/present',
        data: {
            id: folderId,
            recurse: true
        }
    }).done((resp) => {
        if (resp[0]) {
            root.users = new UserCollection();

            root.recurseCollection = new AnnotationCollection([], {comparator: null});
            root.recurseCollection.altUrl = 'annotation/folder/' + folderId;
            root.recurseCollection.fetch({
                id: folderId,
                sort: 'created',
                sortDir: -1,
                recurse: true
            }).done(() => {
                root.recurseCollection.each((model) => {
                    root.users.add({'_id': model.get('creatorId')});
                });
                $.when.apply($, root.users.map((model) => {
                    return model.fetch();
                })).always(() => {
                    root.render();
                });
            });

            root.collection = new AnnotationCollection([], {comparator: null});
            root.collection.altUrl = 'annotation/folder/' + folderId;
            root.collection.fetch({
                id: folderId,
                sort: 'created',
                sortDir: -1,
                recurse: false
            }).done(() => {
                root.collection.each((model) => {
                    root.users.add({'_id': model.get('creatorId')});
                });
                $.when.apply($, root.users.map((model) => {
                    return model.fetch();
                })).always(() => {
                    root.render();
                });
            });
        }
    });
}

function addAccessControl(root) {
    if (root.$('.g-edit-annotation-access').length === 0) {
        if (root.$('.g-folder-actions-menu > .divider').length > 0) {
            root.$('.g-folder-actions-menu > .divider').before(
                '<li role="presentation">' +
                    '<a class="g-edit-annotation-access" role="menuitem">' +
                        '<i class="icon-lock"></i>' +
                        'Annotation access control' +
                    '</a>' +
                '</li>'
            );
        } else {
            root.$('.g-folder-actions-menu > .dropdown-header').after(
                '<li role="presentation">' +
                    '<a class="g-edit-annotation-access" role="menuitem">' +
                        '<i class="icon-lock"></i>' +
                        'Annotation access control' +
                    '</a>' +
                '</li>' +
                '<li class="divider" role="presentation">'
            );
        }
        root.events['click .g-edit-annotation-access'] = editAnnotAccess;
        root.delegateEvents();
    }
}

function editAnnotAccess() {
    const model = this.recurseCollection.at(0).clone();
    model.get('annotation').name = 'Your Annotations';
    model.save = () => {};
    model.updateAccess = (settings) => {
        const access = {
            access: model.get('access'),
            public: model.get('public'),
            publicFlags: model.get('publicFlags')
        };
        if (settings.recurse) {
            this.recurseCollection.each((loopModel) => {
                loopModel.set(access);
                loopModel.updateAccess();
            });
        } else {
            this.collection.each((loopModel) => {
                loopModel.set(access);
                loopModel.updateAccess();
            });
        }

        this.collection.fetch(null, true);
        this.recurseCollection.fetch(null, true);
        model.trigger('g:accessListSaved');
    };
    model.fetchAccess(true)
        .done(() => {
            new AccessWidget({
                el: $('#g-dialog-container'),
                modelType: 'annotation',
                model,
                hideRecurseOption: false,
                parentView: this
            }).on('g:accessListSaved', () => {
                this.collection.fetch(null, true);
                this.recurseCollection.fetch(null, true);
            });
        });
}

export default HierarchyWidget;