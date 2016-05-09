girder.annotation.Model = Backbone.Model.extend({
    sync: function () {},
    url: function () {
        return girder
    }
});
girder.annotation.Collection = Backbone.Collection.extend({
    model: girder.annotation.Model
});
