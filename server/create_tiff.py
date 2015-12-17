# A romanesco script to convert a slide to a TIFF using vips.
import subprocess
import os

out_path = os.path.join(_tempdir, out_filename)

convert_command = (
    'vips',
    'tiffsave',
    '"%s"' % in_path,
    '"%s"' % out_path,
    '--compression', 'jpeg',
    '--Q', '90',
    '--tile',
    '--tile-width', '256',
    '--tile-height', '256',
    '--pyramid',
    '--bigtiff'
)

proc = subprocess.Popen(convert_command)
proc.wait()

if proc.returncode:
    raise Exception('VIPS process failed (rc=%d).' % proc.returncode)
