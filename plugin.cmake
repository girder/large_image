###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

add_python_style_test(
  python_static_analysis_large_image
  "${PROJECT_SOURCE_DIR}/plugins/large_image/server"
)

add_javascript_style_test(
  jsstyle_large_image_gruntfile
  "${PROJECT_SOURCE_DIR}/plugins/large_image/Gruntfile.js"
  JSHINT_EXTRA_CONFIGS "${PROJECT_SOURCE_DIR}/grunt_tasks/.jshintrc"
)
add_javascript_style_test(
  jsstyle_large_image_source
  "${PROJECT_SOURCE_DIR}/plugins/large_image/web_client"
)

add_python_test(example PLUGIN large_image)
add_web_client_test(example "${PROJECT_SOURCE_DIR}/plugins/large_image/plugin_tests/exampleSpec.js" PLUGIN large_image)
