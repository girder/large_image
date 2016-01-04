/**
 * Copyright 2015 Kitware Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

module.exports = function (grunt) {

    var path = require('path');

    // This gruntfile is only designed to be used with girder's build system.
    // Fail if grunt is executed here.
    if (path.resolve(__dirname) === path.resolve(process.cwd())) {
        grunt.fail.fatal('To build large_image, run grunt from Girder\'s root directory');
    }

    grunt.config.merge({
        plugin: {
            large_image: {
                root: '<%= pluginDir %>/large_image',
                static: '<%= staticDir %>/built/plugins/large_image',
                node_modules: '<%= plugin.large_image.root %>/node_modules',
                geojs: '<%= plugin.large_image.node_modules %>/geojs',
                geojs_modules: '<%= plugin.large_image.geojs %>/node_modules',
                geojs_components: '<%= plugin.large_image.geojs %>/bower_components',
                pnltri: '<%= plugin.large_image.geojs_modules %>/pnltri/pnltri.js',
                proj4: '<%= plugin.large_image.geojs_components %>/proj4/dist/proj4-src.js',
                d3: '<%= plugin.large_image.geojs_components %>/d3/d3.js',
                glmatrix: '<%= plugin.large_image.geojs_components %>/gl-matrix/dist/gl-matrix.js'
            }
        },
        uglify: {
            'plugin-image-viewer-geojs': { // Bundle together geojs + dependencies
                files: [
                    {   // leaving out jquery because girder includes it
                        src: [
                            '<%= plugin.large_image.pnltri %>',
                            '<%= plugin.large_image.proj4 %>',
                            '<%= plugin.large_image.d3 %>',
                            '<%= plugin.large_image.glmatrix %>',
                            '<%= plugin.large_image.geojs %>/geo.js'
                        ],
                        dest: '<%= plugin.large_image.static %>/geo.min.js'
                    }
                ]
            }
        },
        default: { // Tell girder about our custom tasks
            'uglify:plugin-image-viewer-geojs': {}
        }
    });

    // add watch tasks
    grunt.config.merge({
        watch: {
            'plugin-image-viewer-geojs': {
                files: grunt.config.getRaw('uglify.plugin-image-viewer-geojs.files')[0].src,
                tasks: ['uglify:plugin-image-viewer-geojs']
            }
        }
    });
};
