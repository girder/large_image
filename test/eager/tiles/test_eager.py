import numpy as np
import large_image
import cv2
from matplotlib import pyplot as plt

# test_wsi = '/wsi_archive/APOLLO_NP/2024/E24-12/scanned images/E24-12_ABETA_1.svs'
# test_wsi = '/scr/tmp/SSCMH14_12MO_LF_01_HE.ndpi'
test_wsi = '/localNVME/arosado/tmp/SSCMH14_12MO_LF_01_HE.ndpi'
test_mask = '/localNVME/arosado/tmp/SSCMH14_12MO_LF_01_HE.ndpi_mask.png'

def test_eager_iterator():
    source = large_image.open(test_wsi)
    metadata = source.getMetadata()
    test_image = np.zeros((metadata['sizeY'], metadata['sizeX'], 3), dtype=np.uint8)
    iterator = source.eagerIterator(scale_mode='mag', target_scale=20, tile_size=(224, 224), overlap=int(224/2), chunk_mult=4, mask=test_mask)

    for batch in iterator:
        batch_images = batch[0].view()
        batch_read_kwargs = batch[1]
        for i in range(batch_images.shape[0]):
            gx = batch_read_kwargs['gx'][i]
            gy = batch_read_kwargs['gy'][i]
            gwidth = batch_read_kwargs['gwidth']
            gheight = batch_read_kwargs['gheight']
            image = batch_images[i]
            image = cv2.resize(image, dsize=(gheight, gwidth), interpolation=cv2.INTER_CUBIC)
            test_image[int(gy):int(gy + gheight), int(gx):int(gx + gwidth), :] = image
            pass

    plt.imsave('test_image.png', test_image)

    print(test_image.shape)
    print(test_image.max())
    print(test_image.min())
    print(test_image.mean())
    print(test_image.std())

test_eager_iterator()