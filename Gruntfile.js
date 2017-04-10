
module.exports = function (grunt) {
    // Create a task to resolve the path to geojs.  This cannot be
    // done statically, because on first run geojs is not yet
    // installed.
    grunt.registerTask('large_image_resolve', function () {
        grunt.config('large_image.geojs_path', require.resolve('geojs'));
    });
    grunt.config.merge({
        copy: {
            large_image_geojs: {
                files: [{
                    src: '<%= large_image.geojs_path %>',
                    dest: '<%= pluginDir %>/large_image/web_client/extra/geojs.js'
                }]
            },
            large_image_slideatlas: {
                files: [{
                    expand: true,
                    cwd: 'node_modules/slideatlas-viewer/dist/',
                    src: '**',
                    dest: '<%= pluginDir %>/large_image/web_client/extra/slideatlas/'
                }]
            },
            large_image_sinon: {
                files: [{
                    src: 'node_modules/sinon/pkg/sinon.js',
                    dest: '<%= pluginDir %>/large_image/web_client/extra/sinon.js'
                }]
            }
        },
        default: {
            'copy:plugin-large_image': {
                dependencies: [
                    'copy:large_image_geojs',
                    'copy:large_image_slideatlas',
                    'copy:large_image_sinon'
                ]
            },
            'copy:large_image_geojs': {
                dependencies: ['large_image_resolve']
            },
            'copy:large_image_slideatlas': {},
            'large_image_resolve': {},
            'copy:large_image_sinon': {}
        }
    });
};
