girder.wrap(girder.views.ItemView, 'render', function (render) {
    // ItemView is a special case in which rendering is done asynchronously,
    // so we must listen for a render event.
    this.once('g:rendered', function () {

        this.$('.g-item-info').after(
            girder.templates.openseadragonWidget()
        );

        var itemId = this.model.id;
        itemId = 'test';
        var viewer = OpenSeadragon({
            id: 'openseadragon-viewer',
            //prefixUrl: '/static/images/',
            prefixUrl: 'https://openseadragon.github.io/openseadragon/images/',
            tileSources: {
                height: 256*32,
                width:  256*32,
                tileSize: 256,
                minLevel: 0,
                maxLevel: 6,
                getTileUrl: function (level, x, y) {
                    return '/api/v1/item/' + itemId + '/tiles/zxy/' +
                        level + '/' + x + '/' + y;
                }
            }
        });

    }, this);
    render.call(this);
});
