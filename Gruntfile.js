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
        grunt.fail.fatal('To build image_viewer, run grunt from Girder\'s root directory');
    }

    grunt.config.merge({
        plugin: {
            image_viewer: {
                root: '<%= pluginDir %>/image_viewer',
                static: '<%= staticDir %>/built/plugins/image_viewer',
                node_modules: '<%= plugin.image_viewer.root %>/node_modules',
                geojs: '<%= plugin.image_viewer.node_modules %>/geojs',
                geojs_modules: '<%= plugin.image_viewer.geojs %>/node_modules',
                geojs_components: '<%= plugin.image_viewer.geojs %>/bower_components',
                pnltri: '<%= plugin.image_viewer.geojs_modules %>/pnltri/pnltri.js',
                proj4: '<%= plugin.image_viewer.geojs_components %>/proj4/dist/proj4-src.js',
                d3: '<%= plugin.image_viewer.geojs_components %>/d3/d3.js',
                glmatrix: '<%= plugin.image_viewer.geojs_components %>/gl-matrix/gl-matrix.js'
            }
        },
        uglify: {
            'plugin-image-viewer-geojs': { // Bundle together geojs + dependencies
                files: [
                    {   // leaving out jquery because girder includes it
                        src: [
                            '<%= plugin.image_viewer.pnltri %>',
                            '<%= plugin.image_viewer.proj4 %>',
                            '<%= plugin.image_viewer.d3 %>',
                            '<%= plugin.image_viewer.glmatrix %>',
                            '<%= plugin.image_viewer.geojs %>/geo.js'
                        ],
                        dest: '<%= plugin.image_viewer.static %>/geo.min.js'
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
