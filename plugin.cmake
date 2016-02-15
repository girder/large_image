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

include(${CMAKE_CURRENT_LIST_DIR}/cmake/MIDAS3.cmake)
set(MIDAS_BASE_URL "https://midas3.kitware.com/midas")
set(MIDAS_REST_URL "${MIDAS_BASE_URL}/api/json")
set(MIDAS_KEY_DIR "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/test_keys")
set(MIDAS_DATA_DIR "${PROJECT_BINARY_DIR}/data/large_image_plugin")
set(MIDAS_DOWNLOAD_TIMEOUT 30)

add_download_target()
add_custom_target(download_data_files ALL DEPENDS ${MIDAS_DOWNLOAD_FILES})

add_python_style_test(
  python_static_analysis_large_image
  "${CMAKE_CURRENT_LIST_DIR}/server"
)

add_eslint_test(
  js_static_analysis_large_image_gruntfile
  "${CMAKE_CURRENT_LIST_DIR}/Gruntfile.js"
)
add_eslint_test(
  js_static_analysis_large_image_source
  "${CMAKE_CURRENT_LIST_DIR}/web_client"
)

add_python_test(tiles PLUGIN large_image BIND_SERVER)
set_property(TEST server_large_image.tiles APPEND PROPERTY ENVIRONMENT
  "LARGE_IMAGE_DATA=${PROJECT_BINARY_DIR}/data/large_image_plugin")
add_web_client_test(example "${CMAKE_CURRENT_LIST_DIR}/plugin_tests/exampleSpec.js" PLUGIN large_image)
