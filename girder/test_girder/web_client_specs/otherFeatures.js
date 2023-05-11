/* globals girderTest, describe, it, expect, waitsFor, runs, $, _ */

girderTest.importPlugin('jobs', 'worker', 'large_image');

girderTest.startApp();

describe('setup', function () {
    it('mock Webgl', function () {
        var girder = window.girder;
        var GeojsViewer = girder.plugins.large_image.views.imageViewerWidget.geojs;
        girder.utilities.PluginUtils.wrap(GeojsViewer, 'initialize', function (initialize) {
            this.once('g:beforeFirstRender', function () {
                window.geo.util.mockWebglRenderer();
                window.geo.webgl.webglRenderer._maxTextureSize = 256;
            });
            initialize.apply(this, _.rest(arguments));
        });
    });
    it('create the admin user', function () {
        girderTest.createUser(
            'admin', 'admin@email.com', 'Admin', 'Admin', 'testpassword')();
    });
});
describe('Test features added by the large image plugin but not directly related to large images', function () {
    it('go to users page', girderTest.goToUsersPage());
    it('Go to a user page and then the Public folder', function () {
        runs(function () {
            $('a.g-user-link').trigger('click');
        });
        waitsFor(function () {
            return $('button:contains("Actions")').length === 1;
        }, 'user page to appear');
        waitsFor(function () {
            return $('a.g-folder-list-link:contains(Public):visible').length === 1;
        }, 'the Public folder to be clickable');
        runs(function () {
            $('a.g-folder-list-link:contains(Public)').trigger('click');
        });
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'the folder to appear');
    });
    it('upload test file', function () {
        girderTest.waitForLoad();
        runs(function () {
            $('.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            girderTest.binaryUpload('${large_image}/../../test/test_files/multi_test_source3.yml'); // eslint-disable-line no-template-curly-in-string
        });
        girderTest.waitForLoad();
    });
    it('navigate to item and see if the yaml editor is present', function () {
        runs(function () {
            $('a.g-item-list-link').click();
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.li-item-view-codemirror>.editor').length;
        }, 'editor to show');
        runs(function () {
            expect($('.li-item-view-codemirror>.editor').length).toBe(1);
        });
    });
    it('test buttons', function () {
        runs(function () {
            $('.g-view-codemirror-format-button').click();
            $('.g-view-codemirror-save-button').click();
            $('.g-view-codemirror-revert-button').click();
            $('.g-view-codemirror-save-button').click();
            $('.g-view-codemirror-save-button').click();
            expect($('.li-item-view-codemirror>.editor').length).toBe(1);
        });
    });
    it('Go up a folder', function () {
        runs(function () {
            $('a.g-item-breadcrumb-link:last').trigger('click');
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'the folder to appear');
    });
    it('upload test file', function () {
        girderTest.waitForLoad();
        runs(function () {
            $('.g-folder-list-link:first').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            girderTest.binaryUpload('${large_image}/../../test/test_files/sample.girder.cfg'); // eslint-disable-line no-template-curly-in-string
        });
        girderTest.waitForLoad();
    });
    it('navigate to item and change the mime type', function () {
        runs(function () {
            $('a.g-item-list-link:last').click();
        });
        girderTest.waitForLoad();
        runs(function () {
            $('.g-file-actions-container .g-update-info').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            $('#g-mimetype').val('application/x-girder-ini');
            $('button.g-save-file').click();
        });
        girderTest.waitForLoad();
    });
    it('navigate away and back', function () {
        runs(function () {
            $('a.g-item-breadcrumb-link:last').trigger('click');
        });
        girderTest.waitForLoad();
        waitsFor(function () {
            return $('.g-folder-actions-button:visible').length === 1;
        }, 'the folder to appear');
        runs(function () {
            $('a.g-item-list-link:last').click();
        });
        girderTest.waitForLoad();
    });
    it('test buttons', function () {
        runs(function () {
            expect($('.li-item-view-codemirror>.editor').length).toBe(1);
        });
        runs(function () {
            $('.g-view-codemirror-format-button').click();
            $('.g-view-codemirror-save-button').click();
            $('.g-view-codemirror-revert-button').click();
            $('.g-view-codemirror-save-button').click();
            $('.g-view-codemirror-format-button').click();
        });
        girderTest.waitForLoad();
    });
    it('test replace button', function () {
        runs(function () {
            $('.g-view-codemirror-general-button[button-key="replace"]').click();
        });
        girderTest.waitForDialog();
        runs(function () {
            expect($('#g-confirm-button').text()).toEqual('Save, Replace, and Restart');
            $('a.btn-default').click();
        });
        girderTest.waitForLoad();
    });
});
