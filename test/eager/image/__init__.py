import os

import large_image

test_image = os.path.join('/wsi_archive', 'TCGA', 'acc', 'TCGA-OR-A5J1-01A-01-TS1.CFE08710-54B8-45B0-86AE-500D6E36D8A5.svs')

source = large_image.open(test_image)

iterator = source.eagerIterator(output_mode='tiles', transform=transform)

for batch in iterator:
    batch_images = batch[0].view()