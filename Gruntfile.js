
module.exports = function (grunt) {
    var geojs = require.resolve('geojs');
    grunt.config.merge({
        copy: {
            large_image_geojs: {
                files: [{
                    src: geojs,
                    dest: '<%= pluginDir %>/large_image/web_client/extra/geojs.js'
                }]
            }
        },
        default: {
            'copy:plugin-large_image': {
                dependencies: ['copy:large_image_geojs']
            },
            'copy:large_image_geojs': {}
        }
    });
};
