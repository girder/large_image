# A romanesco script to convert a slide to a TIFF using vips.
import os
import subprocess
import sys

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

proc = subprocess.Popen(convert_command, stdout=sys.stdout, stderr=sys.stderr)
proc.wait()

if proc.returncode:
    raise Exception('VIPS command failed (rc=%d): %s' % (
        proc.returncode, ' '.join(convert_command)))
