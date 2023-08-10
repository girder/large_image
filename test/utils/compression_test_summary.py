#!/usr/bin/env python

import json
import os
import sys

import pandas as pd
import tifftools

if not len(sys.argv[1:]) or '--help' in sys.argv[1:]:
    print("""test_compression_summary.py (directory) (csv output file)

Check each file in the specified directory and gather appropriate statistics
into csv output.""")
    sys.exit(0)
results = []
for file in os.listdir(sys.argv[1]):
    path = os.path.join(sys.argv[1], file)
    entry = {'file': file}
    if '.compression' in file:
        entry['source'] = file.split('.compression')[0]
    elif '.tile' in file:
        entry['source'] = file.split('.tile')[0]
    else:
        entry['source'] = file.split('.tiff')[0]
    entry['error'] = None
    results.append(entry)
    try:
        info = tifftools.read_tiff(path)
    except Exception:
        entry['error'] = "Can't read"
        print(entry)
        continue
    try:
        details = json.loads(info['ifds'][0]['tags'][tifftools.Tag.ImageDescription.value]['data'])
    except Exception:
        entry['error'] = "Can't parse ImageDescription"
        print(entry)
        continue
    entry.update(details['large_image_converter']['arguments'])
    try:
        entry.update({
            k if k != 'psnr' else 'stats_psnr': v
            for k, v in details['large_image_converter']['conversion_stats'].items()})
    except Exception:
        entry['error'] = 'No conversion stats'
        print(entry)
        continue
    print(entry)
df = pd.DataFrame.from_dict(results)
df.to_csv(sys.argv[2], index=False)
