import os

import matplotlib.pyplot as plt
import large_image
import numpy as np

def test_tcga_image(image_path, save_dir):
    os.makedirs(save_dir, exist_ok=True)
    test_image_path = os.path.join(save_dir, 'test_image.png')
    test_large_image_path = os.path.join(save_dir, 'test_large_image.png')
    test_region_path = os.path.join(save_dir, 'test_region.png')
    
    source = large_image.open(image_path)
    eager_iter = source.eagerIterator(scale_mode='mm', target_scale=(0.000625*16, 0.000625*16), tile_size=(224, 224), dtype=np.uint8, batch=64)

    size_x = eager_iter.slide_dimensions['tile_target_range_x'] + 1
    size_y = eager_iter.slide_dimensions['tile_target_range_y'] + 1

    test_image, _ = source.getThumbnail(format='numpy')
    plt.imsave(test_image_path, test_image)

    metadata = source.getMetadata()

    kwargs = {'left': 0, 'top': 0, 'right': metadata['sizeX'], 'bottom': metadata['sizeY']}

    scale = {'mm_x': 0.000625*16, 'mm_y': 0.000625*16}

    # test_region, _ = source.getRegion(**kwargs, scale=scale, format='numpy')
    # tr = source.convertRegion(sourceRegion=kwargs, targetScale=scale)
    # test_region, _ = source.getRegionAtAnotherScale(sourceRegion=tr, targetScale=scale, format='numpy')
    # plt.imsave(test_region_path, test_region)

    test_large_image = np.zeros((size_y*224, size_x*224, 3), dtype=np.uint8)

    for batch in eager_iter:
        batch_images = batch[0].view()
        batch_read_kwargs = batch[1]

        for i in range(batch_images.shape[0]):
            x = int(batch_read_kwargs['tile_position']['region_x'][i].item())
            y = int(batch_read_kwargs['tile_position']['region_y'][i].item())
            
            image = batch_images[i]
            test_large_image[y*224:(y+1)*224, x*224:(x+1)*224, :] = image
            
    plt.imsave(test_large_image_path, test_large_image)

    pass

if __name__ == "__main__":
    test_tcga_image('/data1/tcga/read/9b8b8379-fd3a-4c53-8763-38125ae3ea4c.svs', '/data1/test_tcga')