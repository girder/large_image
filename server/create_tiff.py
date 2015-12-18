import os
import subprocess

out_path = os.path.join(_tempdir, out_filename)

convert_command = (
    'vips',
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

proc = subprocess.Popen(convert_command, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
out, err = proc.communicate()

if proc.returncode:
    print('stdout: ' + out)
    print('stderr: ' + err)
    raise Exception('VIPS command failed (rc=%d): %s' % (
        proc.returncode, ' '.join(convert_command)))
