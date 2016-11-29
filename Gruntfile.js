
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
            }
        },
        default: {
            'copy:plugin-large_image': {
                dependencies: ['copy:large_image_geojs']
            },
            'copy:large_image_geojs': {
                dependencies: ['large_image_resolve']
            },
            'large_image_resolve': {}
        }
    });
};
