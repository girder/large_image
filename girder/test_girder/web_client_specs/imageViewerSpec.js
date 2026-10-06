/* globals describe, it, expect, _, girderTest, $, runs, waitsFor, waits, xit */

girderTest.importPlugin('large_image');

girderTest.startApp();

$(function () {
    describe('setup', function () {
        it('mock Webgl', function () {
            var girder = window.girder;
            var GeojsViewer = girder.plugins.large_image.views.imageViewerWidget.geojs;
            girder.utilities.PluginUtils.wrap(GeojsViewer, 'initialize', function (initialize) {
                this.once('g:beforeFirstRender', function () {
                    try {
                        window.geo.util.mockWebglRenderer();
                    } catch (err) {
                        // if this is already mocked, do nothing.
                    }
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
    describe('test accessing a multi-frame image', function () {
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
        it('navigate to item and wait for an image', function () {
            runs(function () {
                $('a.g-item-list-link').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-item-image-viewer-select').length !== 0;
            }, 'image to load', 15000);
        });
        it('adjust frame slider', function () {
            runs(function () {
                expect($('.image-frame-control-box').length).toBe(1);
                $('.image-frame-control-box input:visible').eq(1).val(1).trigger('input');
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.image-frame-control-box input:visible').eq(1).val() === '1';
            }, 'control slider to update');
        });
    });
    describe('test layer hotkeys in band compositing', function () {
        // CompositeLayers listens on the document with addEventListener, which
        // jQuery's trigger does not reach, so dispatch native events.
        function pressKey(key, mods) {
            var evt = document.createEvent('Event');
            evt.initEvent('keydown', true, true);
            var props = _.extend({key: key, ctrlKey: false, altKey: false, shiftKey: false, metaKey: false}, mods || {});
            _.each(props, function (value, name) {
                Object.defineProperty(evt, name, {value: value});
            });
            document.dispatchEvent(evt);
        }
        function bandEnabled(band) {
            return $('.image-frame-control-box .enable-col input[value="' + band + '"]').prop('checked');
        }
        function frameSelector() {
            return $('.image-frame-control-box')[0].__vue__;
        }

        it('upload a multi-band image', function () {
            runs(function () {
                $('.g-item-breadcrumb-link[data-type="folder"]:last').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('${large_image}/../../test/test_files/multi_test_source_bands.yml'); // eslint-disable-line no-template-curly-in-string
            });
            girderTest.waitForLoad();
        });
        it('navigate to the item and use band compositing', function () {
            waitsFor(function () {
                return $('a.g-item-list-link:contains(multi_test_source_bands)').length > 0;
            }, 'item link to appear');
            runs(function () {
                $('a.g-item-list-link:contains(multi_test_source_bands)').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.image-frame-control-box select[name="mode"] option[value="3"]').length > 0;
            }, 'band compositing mode to be available', 15000);
            runs(function () {
                var select = $('.image-frame-control-box select[name="mode"]')[0];
                select.value = '3';
                var evt = document.createEvent('HTMLEvents');
                evt.initEvent('change', true, true);
                select.dispatchEvent(evt);
            });
            waitsFor(function () {
                return $('.image-frame-control-box .enable-col input[value="green"]:visible').length > 0;
            }, 'band table to appear');
            runs(function () {
                expect(bandEnabled('red')).toBe(true);
                expect(bandEnabled('green')).toBe(true);
            });
        });
        it('toggle a band with the default keys', function () {
            runs(function () {
                pressKey('1', {ctrlKey: true});
            });
            waitsFor(function () {
                return bandEnabled('red') === false;
            }, 'ctrl+1 to hide the first band');
            runs(function () {
                pressKey('1', {ctrlKey: true});
            });
            waitsFor(function () {
                return bandEnabled('red') === true;
            }, 'ctrl+1 to show the first band');
        });
        it('replace the layer hotkeys', function () {
            runs(function () {
                frameSelector()._props.layerHotkeys = {
                    layerForEvent: function (evt) {
                        return evt.key === 'q' && !evt.ctrlKey ? 1 : undefined;
                    },
                    labels: [undefined, 'Q']
                };
            });
            waits(100);
            runs(function () {
                pressKey('1', {ctrlKey: true});
                pressKey('q');
            });
            waitsFor(function () {
                return bandEnabled('green') === false;
            }, 'q to hide the second band');
            runs(function () {
                expect(bandEnabled('red')).toBe(true);
            });
        });
        it('list the replaced keys in the help', function () {
            runs(function () {
                $('.image-frame-control-box .icon-keyboard:visible').click();
            });
            waitsFor(function () {
                return $('.image-frame-control-box .shortcuts:visible').length > 0;
            }, 'shortcut help to show');
            runs(function () {
                var text = $('.image-frame-control-box .shortcuts:visible').text().replace(/\s+/g, ' ');
                expect(text).toContain('Q Toggle visibility of green');
                expect(text).not.toContain('ctrl + number');
                $('.image-frame-control-box .icon-keyboard:visible').click();
                frameSelector()._props.layerHotkeys = undefined;
            });
            // Toggling bands requests histograms; let them finish before the
            // next test navigates away from this viewer.
            waitsFor(function () {
                return $.active === 0;
            }, 'histogram requests to finish');
            girderTest.waitForLoad();
        });
    });
    describe('upload test file', function () {
        it('go to collections page', function () {
            runs(function () {
                $("a.g-nav-link[g-target='collections']").click();
            });

            waitsFor(function () {
                return $('.g-collection-create-button:visible').length > 0;
            }, 'navigate to collections page');

            runs(function () {
                expect($('.g-collection-list-entry').length).toBe(0);
            });
        });
        it('create collection', girderTest.createCollection('test', '', 'image'));
        it('upload test file', function () {
            girderTest.waitForLoad();
            runs(function () {
                $('.g-folder-list-link:first').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('${large_image}/../../test/test_files/yb10kx5k.png'); // eslint-disable-line no-template-curly-in-string
            });
            girderTest.waitForLoad();
        });
        it('navigate to item and make a large image', function () {
            runs(function () {
                $('a.g-item-list-link').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-large-image-create').length !== 0;
            });
            runs(function () {
                $('.g-large-image-create').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-item-image-viewer-select').length !== 0;
            }, 'job to complete', 15000);
            girderTest.waitForLoad();
        });
    });

    describe('removal', function () {
        it('unmake a large image', function () {
            runs(function () {
                $('.g-large-image-remove').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return !$('.g-item-image-viewer-select').length;
            }, 'select button to vanish', 15000);
            girderTest.waitForLoad();
        });
        it('remake a large image and then remove the image file', function () {
            waitsFor(function () {
                return $('.g-large-image-create').length > 0;
            }, 'make large image button to appear');
            runs(function () {
                $('.g-large-image-create').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-item-image-viewer-select').length !== 0;
            }, 'job to complete', 15000);
            girderTest.waitForLoad();
            runs(function () {
                $('.g-delete-file').click();
            });
            girderTest.waitForDialog();
            runs(function () {
                $('#g-confirm-button').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return !$('.g-item-image-viewer-select').length;
            }, 'select button to vanish', 15000);
            girderTest.waitForLoad();
        }, 30000);
        it('upload test file', function () {
            girderTest.waitForLoad();
            runs(function () {
                $('.g-item-breadcrumb-link[data-type="folder"]:last').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('${large_image}/../../test/test_files/yb10kx5k.png'); // eslint-disable-line no-template-curly-in-string
            });
            girderTest.waitForLoad();
        }, 30000);
        it('navigate to item and make a large image', function () {
            waitsFor(function () {
                return $('a.g-item-list-link').length > 0;
            }, 'link to appear');
            runs(function () {
                $('a.g-item-list-link').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-large-image-create').length !== 0;
            });
            runs(function () {
                $('.g-large-image-create').click();
            });
            girderTest.waitForLoad();
            waitsFor(function () {
                return $('.g-item-image-viewer-select').length > 0 && $('.g-large-image-remove').length > 0;
            }, 'job to complete', 15000);
            girderTest.waitForLoad();
        }, 30000);
    });
    describe('test metadata in item lists', function () {
        it('go to users page', girderTest.goToUsersPage());
        it('Go to a user page and then the Public folder', function () {
            runs(function () {
                $('a.g-user-link').trigger('click');
            });
            waitsFor(function () {
                return (
                    $('button:contains("Actions")').length === 1 &&
                    $('a.g-folder-list-link:contains(Public):visible').length === 1);
            }, 'user page to appear');
            runs(function () {
                $('a.g-folder-list-link:contains(Public)').trigger('click');
            });
            waitsFor(function () {
                return $('.g-folder-actions-button:visible').length === 1;
            }, 'the folder to appear');
            girderTest.waitForLoad();
        });
        it('test the metadata columns are not shown', function () {
            runs(function () {
                expect($('.large_image_container').length).toBe(0);
                expect($('.large_image_thumbnail').length).toBeGreaterThan(0);
                expect($('.li-column-metadata').length).toBe(0);
            });
        });
        it('upload test file', function () {
            girderTest.waitForLoad();
            runs(function () {
                $('.g-folder-list-link:first').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                girderTest.binaryUpload('${large_image}/../../test/test_files/.large_image_config.yaml'); // eslint-disable-line no-template-curly-in-string
            });
            girderTest.waitForLoad();
        });
        it('test the metadata columns are shown', function () {
            runs(function () {
                expect($('.large_image_container').length).toBe(0);
                expect($('.large_image_thumbnail').length).toBeGreaterThan(0);
                expect($('.li-column-metadata').length).toBeGreaterThan(0);
            });
        });
        it('apply a filter', function () {
            runs(function () {
                $('.li-item-list-filter-input').val('yb').trigger('input');
            });
            girderTest.waitForLoad();
            runs(function () {
                expect($('.g-item-list-entry').length >= 1);
            });
            runs(function () {
                $('.li-item-list-filter-input').val('ybxxx 1.2 -0.6').trigger('input');
            });
            girderTest.waitForLoad();
            runs(function () {
                expect(!$('.g-item-list-entry').length);
            });
            runs(function () {
                $('.li-item-list-filter-input').val('').trigger('input');
            });
            girderTest.waitForLoad();
            runs(function () {
                expect(!$('.g-item-list-entry').length);
            });
        });
        it('flatten the item list', function () {
            runs(function () {
                $('.li-flatten-item-list #flattenitemlist').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                expect($('.li-flatten-item-list #flattenitemlist:checked').length);
            });
            runs(function () {
                $('.li-flatten-item-list #flattenitemlist').click();
            });
            girderTest.waitForLoad();
            runs(function () {
                expect(!$('.li-flatten-item-list #flattenitemlist:checked').length);
            });
        });
        it('navigate back to image', function () {
            waitsFor(function () {
                return $('span.g-item-list-link').filter(function () { return $(this).text() !== '.large_image_config.yaml'; }).length > 0;
            }, 'link to appear');
            runs(function () {
                $('span.g-item-list-link').filter(function () { return $(this).text() !== '.large_image_config.yaml'; }).click();
            });
            girderTest.waitForLoad();
        });
    });

    describe('Image Viewer selection', function () {
        var viewers = [], jQuery; // use the original jQuery
        it('One viewer is loaded', function () {
            waitsFor(function () {
                return $('.image-viewer').not('.hidden').not(':empty').length !== 0;
            }, 'one viewer to be shown');
            runs(function () {
                expect($('.image-viewer').not('.hidden').length).toBe(1);
                var selected = $('.g-item-image-viewer-select .g-item-info-header select').val();
                expect($('.image-viewer').not('.hidden').attr('id')).toBe(selected);
                $('.g-item-image-viewer-select .g-item-info-header select option').each(function () {
                    viewers.push($(this).val());
                });
                expect(viewers.length).toBe(5);
                jQuery = $;
            }, 'get list of viewers');
        });
        xit('Select each viewer in turn via change, then return to geojs', function () {
            viewers.push('geojs');
            _.each(viewers, function (vid, idx) {
                girderTest.waitForLoad();
                runs(function () {
                    var $ = jQuery;
                    $('.g-item-image-viewer-select .g-item-info-header select').val(vid).change();
                }, 'select ' + vid + ' (' + idx + ')');
                waitsFor(function () {
                    var $ = jQuery;
                    return !$('.image-viewer:empty').not('.hidden').length &&
                           !$('.image-viewer.hidden').not(':empty').length &&
                           $('.image-viewer').not('.hidden').not(':empty').length &&
                           $('.image-viewer').not('.hidden').length === 1 &&
                           $('.image-viewer').not('.hidden').attr('id') === vid;
                }, 'wait for ' + vid + ' (' + idx + ') to be visible');
                runs(function () {
                    var $ = jQuery;
                    expect($('.image-viewer').not('.hidden').length).toBe(1);
                }, 'check ' + vid + ' (' + idx + ')');
            });
        });
    });
});
