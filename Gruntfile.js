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
/* eslint-env node */
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
                extjs: '<%= plugin.large_image.root %>/web_client/js/ext'
            }
        },
        uglify: {
            'plugin-large_image-geojs': { // Bundle together geojs + dependencies
                files: [
                    {
                        src: [
                            '<%= plugin.large_image.geojs %>/geo.js'
                        ],
                        dest: '<%= plugin.large_image.static %>/geo.min.js'
                    }
                ]
            }
        },
        copy: {
            'li-tinycolor': {
                files: [{
                    src: ['<%= plugin.large_image.node_modules %>/tinycolor2/tinycolor.js'],
                    dest: '<%= plugin.large_image.extjs %>/tinycolor.js'
                }]
            }
        },
        default: { // Tell girder about our custom tasks
            'uglify:plugin-large_image-geojs': {}
        },
        init: {
            'copy:li-tinycolor': [
                'shell:plugin-large_image'
            ]
        }
    });

    // add watch tasks
    grunt.config.merge({
        watch: {
            'plugin-large_image-geojs': {
                files: grunt.config.getRaw('uglify.plugin-large_image-geojs.files')[0].src,
                tasks: ['uglify:plugin-large_image-geojs']
            }
        }
    });
};
