/* globals girder, _ */

girder.wrap(girder.views.ItemListWidget, 'render', function (render) {
    render.call(this);
    var items = this.collection.toArray();
    var parent = this.$el;
    var hasAnyLargeImage = _.some(items, function (item) {
        return item.attributes.largeImage;
    });
    if (hasAnyLargeImage) {
        $.each(items, function (idx, item) {
            var elem = $('<span class="large_image_thumbnail"/>');
            if (item.attributes.largeImage) {
                elem.append($('<img/>').attr(
                        'src', girder.apiRoot + '/item/' + item.id +
                        '/tiles/thumbnail?width=160&height=100'));
                $('img', elem).one('error', function () {
                    $('img', elem).addClass('failed-to-load');
                });
            }
            $('a[g-item-cid="' + item.cid + '"]>i', parent).before(elem);
        });
    }
    return this;
});
