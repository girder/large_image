#!/usr/bin/env python

import concurrent.futures
import itertools
import os
import subprocess
import sys

import psutil

os.environ['GDAL_PAM_PROXY_DIR'] = '/tmp/gdal'

allOpts = ['-w', '--stats-full']
matrix = [[
    [],
    ['--compression', 'none'],
    ['--compression', 'jpeg'],
    ['--compression', 'jpeg', '-q', '95'],
    ['--compression', 'jpeg', '-q', '90'],
    ['--compression', 'jpeg', '-q', '80'],
    ['--compression', 'jpeg', '-q', '70'],
    ['--compression', 'deflate'],
    ['--compression', 'deflate', '--level', '1'],
    ['--compression', 'deflate', '--level', '9'],
    ['--compression', 'lzw'],
    ['--compression', 'lzw', '--predictor', 'none'],
    ['--compression', 'lzw', '--predictor', 'horizontal'],
    ['--compression', 'zstd'],
    ['--compression', 'zstd', '--level', '1'],
    ['--compression', 'zstd', '--level', '9'],
    ['--compression', 'zstd', '--level', '22'],
    ['--compression', 'packbits'],
    # ['--compression', 'jbig'],
    # ['--compression', 'lzma'],
    ['--compression', 'webp'],
    ['--compression', 'webp', '-q', '0'],
    ['--compression', 'webp', '-q', '100'],
    ['--compression', 'webp', '-q', '95'],
    ['--compression', 'webp', '-q', '90'],
    ['--compression', 'webp', '-q', '80'],
    ['--compression', 'webp', '-q', '70'],
    ['--compression', 'jp2k'],
    ['--compression', 'jp2k', '--psnr', '80'],
    ['--compression', 'jp2k', '--psnr', '70'],
    ['--compression', 'jp2k', '--psnr', '60'],
    ['--compression', 'jp2k', '--psnr', '50'],
    ['--compression', 'jp2k', '--psnr', '40'],
    ['--compression', 'jp2k', '--cr', '10'],
    ['--compression', 'jp2k', '--cr', '100'],
    ['--compression', 'jp2k', '--cr', '1000'],
], [
    [],  # 256
    ['--tile', '512'],
    ['--tile', '1024'],
]]

if not len(sys.argv[1:]) or '--help' in sys.argv[1:]:
    print("""test_compression.py [(concurrency)] (output directory) (input file ...)""")
    sys.exit(0)
args = sys.argv[1:]
# Set to 1 to disable concurrency, 0 for number of cpus
concurrency = 1
if args[0].isdigit():
    concurrency = int(args[0])
    if not concurrency:
        concurreny = psutil.cpu_count(logical=True)
    args = args[1:]
pool = concurrent.futures.ThreadPoolExecutor(max_workers=concurrency)
tasks = []
for input in args[1:]:
    root = os.path.join(args[0], os.path.basename(input))
    for optList in itertools.product(*matrix):
        opts = [opt for subList in optList for opt in subList]
        output = root + '.' + '.'.join(str(opt).strip('-') for opt in opts) + '.tiff'
        output = output.replace('..', '.')
        cmd = ['large_image_converter', input, output] + opts + allOpts
        tasks.append((cmd, pool.submit(subprocess.call, cmd)))
while len(tasks):
    try:
        tasks[0][-1].result(0.1)
    except concurrent.futures.TimeoutError:
        continue
    cmd, task = tasks.pop(0)
    print(' '.join(cmd))
pool.shutdown(False)
