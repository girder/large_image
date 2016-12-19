#!/usr/bin/env python

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

import os
import subprocess

# Define Girder Worker globals for the style checker
_tempdir = _tempdir   # noqa
in_path = in_path   # noqa
quality = quality   # noqa
tile_size = tile_size   # noqa
out_filename = out_filename  # noqa

out_path = os.path.join(_tempdir, out_filename)

convert_command = (
    'vips',
    # '--vips-concurrency', '1',
    # '--vips-progress',
    'tiffsave',
    in_path,
    out_path,
    '--compression', 'jpeg',
    '--Q', str(quality),
    '--tile',
    '--tile-width', str(tile_size),
    '--tile-height', str(tile_size),
    '--pyramid',
    '--bigtiff'
)

try:
    import six.moves
    print('Command: %s' % (
        ' '.join([six.moves.shlex_quote(arg) for arg in convert_command])))
except ImportError:
    pass
proc = subprocess.Popen(convert_command, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
out, err = proc.communicate()

if out.strip():
    print('stdout: ' + out)
if err.strip():
    print('stderr: ' + err)
if proc.returncode:
    raise Exception('VIPS command failed (rc=%d): %s' % (
        proc.returncode, ' '.join(convert_command)))
