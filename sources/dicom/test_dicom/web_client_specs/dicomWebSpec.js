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
    it('Create an assetstore and import data', function () {
        var parentId;
        var parentType;

        // After importing, we will verify that this item exists
        const verifyItemName = '1.3.6.1.4.1.5962.99.1.3510881361.982628633.1635598486609.2.0';

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

        runs(function () {
            // Create the DICOMweb assetstore
            $('#g-new-dwas-name').val('DICOMweb');
            $('#g-edit-dwas-url').val('https://idc-external-006.uc.r.appspot.com/dcm4chee-arc/aets/DCM4CHEE/rs');
            $('#g-new-dwas-form input.btn-primary').click();
        });

        waitsFor(function () {
            const assetstores = girder.rest.restRequest({
                url: 'assetstore',
                type: 'GET',
                async: false
            }).responseJSON;
            return assetstores.length === 2 && assetstores[0].type === 'dicomweb';
        }, 'DICOMweb assetstore to be created');

        runs(function () {
            // Select the parentId and parentType
            // Get the user ID
            const resp = girder.rest.restRequest({
                url: 'user',
                type: 'GET',
                async: false
            });

            const userId = resp.responseJSON[0]._id;

            // Find the user's public folder
            const resp = girder.rest.restRequest({
                url: 'folder',
                type: 'GET',
                async: false,
                data: {
                    parentType: 'user',
                    parentId: userId,
                    name: 'Public',
                }
            });

            // Use the user's public folder
            parentType = 'folder';
            parentId = resp.responseJSON[0]._id;
        });

        runs(function () {
            // Navigate to the import page
            $('.g-dwas-import-button').eq(0).trigger('click');
        });

        waitsFor(function () {
            // Wait for the import page to load
            return $('.g-submit-assetstore-import:visible').length > 0;
        }, 'Import page to load');

        runs(function () {
            // Set the needed options and begin the import
            $('#g-dwas-import-dest-type').val(parentType);
            $('#g-dwas-import-dest-id').val(parentId);
            $('.g-submit-assetstore-import').trigger('click');
        });

        // Verify that the item we were looking for was imported
        waitsFor(function () {
            const items = girder.rest.restRequest({
                url: 'resource/search',
                type: 'GET',
                async: false,
                data: {
                    q: '"' + verifyItemName + '"',
                    types: '["item"]'
                }
            }).responseJSON.item;

            return items.length > 0 && items[0].largeImage !== undefined;
        }, 'Wait for large images to be present');
    });
});
