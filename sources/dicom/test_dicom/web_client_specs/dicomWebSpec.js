girderTest.importPlugin('jobs', 'large_image', 'dicomweb');

girderTest.startApp();

describe('DICOMWeb assetstore', function () {
    // maybe see how this is done in other tests -- it may not be necessary
    it('register a user (first is admin)',
        girderTest.createUser('admin',
            'admin@girder.test',
            'Admin',
            'Admin',
            'adminpassword!'));
    it('go to assetstore page', function () {
        runs(function () {
            $('a.g-nav-link[g-target="admin"]').trigger('click');
        });

        waitsFor(function () {
            return $('.g-assetstore-config:visible').length > 0;
        }, 'navigate to admin page');

        runs(function () {
            $('a.g-assetstore-config').trigger('click');
        });

        waitsFor(function () {
            return $('#g-create-dwas-tab').length > 0;
        }, 'create to be visible');

        runs(function () {
            expect($('#g-create-dwas-tab').length);
        });
    });
});
