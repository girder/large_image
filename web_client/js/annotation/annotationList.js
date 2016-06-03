/**
 * This widget shows a list of annotations in a given item.  This view
 * is largely based on girder.views.FileListWidget.
 */
girder.views.AnnotationListWidget = girder.View.extend({
    events: {
        'click a.g-show-more-annotations': function () {
            this.collection.fetchNextPage();
        },

        'click a.g-delete-annotation': function (e) {
            var cid = $(e.currentTarget).parent().attr('annotation-cid');
            var annotation = this.collection.get(cid);

            girder.confirm({
                text: 'Are you sure you want to delete the annotation <b>' +
                    annotation.escape('name') + '<b>',
                yesText: 'Delete',
                escapedHtml: true,
                confirmCallback: _.bind(function () {
                    annotation.once('g:deleted', _.bind(function () {
                        girder.events.trigger('g:alert', {
                            icon: 'ok',
                            type: 'success',
                            text: 'Annotation deleted',
                            timeout: 4000
                        });

                        this.render();
                    }, this)).once('g:error', function () {
                        girder.events.trigger('g:alert', {
                            icon: 'cancel',
                            text: 'Failed to delete file.',
                            type: 'danger',
                            timeout: 4000
                        });
                    }).destroy();
                }, this)
            });
        }

    },

    initialize: function (settings) {
        this.parentItem = settings.item;
        this.collection = settings.item.annotations;
        this.collection.append = true;

        this.collection.on('g:changed', function () {
            this.render();
            this.trigger('g:changed');
        }, this).fetch();
    },

    render: function () {
        this.$el.html(girder.templates.annotationList({
            annotations: this.collection.toArray(),
            hasMore: this.collection.hasNextPage(),
            girder: girder,
            parentItem: this.parentItem
        }));

        this.$('.g-annotation-actions-container a[title]').tooltip({
            container: 'body',
            placement: 'auto',
            delay: 100
        });

        return this;
    }
});

// extend the ItemView to show annotations at the bottom
girder.wrap(girder.views.ItemView, 'initialize', function (initialize, settings) {
    initialize.apply(this, _.rest(arguments, 1));

    settings = settings || {};
    this.annotationList = new girder.views.AnnotationListWidget({
        item: settings.item,
        parentView: this,
        el: $('<div class="g-annotatation-list-container g-item-files"/>')
    });
    this.on('g:rendered', function () {
        this.$('.g-annotation-list-container').remove();
        if (this.annotationList.collection.length) {
            this.$el.append(this.annotationList.render().el);
        }
    }, this);
    return this;
});
