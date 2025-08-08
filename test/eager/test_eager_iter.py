import os
import time
from typing import Callable

from matplotlib import pyplot as plt
import large_image

import numpy as np

def build_eager_iterator(test_image_path: str, scale_mode: str = 'mag', target_scale: int = 20, tile_size: tuple[int, int] = (224, 224), overlap: int = 0, chunk_mult: int = 4, mask: str = None, output_mode: str = 'tiles', transform: Callable = None, batch: int = 64):
    source = large_image.open(test_image_path)
    iterator = source.eagerIterator(scale_mode=scale_mode, target_scale=target_scale, tile_size=tile_size, overlap=overlap, chunk_mult=chunk_mult, mask=mask, output_mode=output_mode, transform=transform, batch=batch)
    return source, iterator

def test_eager_iterator_image(test_image_path: str, output_dir_path: str, target_scale: int = 5, tile_size: tuple[int, int] = (224, 224)):
    source, iterator = build_eager_iterator(test_image_path, target_scale=target_scale, tile_size=tile_size)
    
    thumbnail, _ = source.getThumbnail(size=(1024, 1024), format='numpy')
    thumbnail_output_path = os.path.join(output_dir_path, 'thumbnail.png')
    plt.imsave(thumbnail_output_path, thumbnail)
    
    test_large_image = np.zeros((iterator.slide_dimensions['tile_target_range_y']*tile_size[1], iterator.slide_dimensions['tile_target_range_x']*tile_size[0], 3), dtype=np.uint8)
    for batch in iterator:
        batch_images = batch[0].view()
        batch_read_kwargs = batch[1]
        for i in range(batch_images.shape[0]):
            x = int(batch_read_kwargs['tile_position']['region_x'][i].item())
            y = int(batch_read_kwargs['tile_position']['region_y'][i].item())
            image = batch_images[i]
            test_large_image[y*tile_size[1]:(y+1)*tile_size[1], x*tile_size[0]:(x+1)*tile_size[0], :] = image[:, :, :]

    large_image_output_path = os.path.join(output_dir_path, 'large_image.png')
    plt.imsave(large_image_output_path, test_large_image)


def test_eager_iterator_with_pytorch_transform(test_image_path: str, transform: Callable):
    # try:
    start_time = time.time()
    # test_image = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')

    source = large_image.open(test_image_path)
    iterator = source.eagerIterator(output_mode='tiles', transform=transform)

    # Count output images provided by the iterator
    output_image_count = iterator.get_output_image_count()
    # Count tiles provided by the iterator based on the slide dimensions if a subset not selected
    tile_image_count = iterator.slide_dimensions['tile_target_range_x'] * iterator.slide_dimensions['tile_target_range_y']

    # Count tiles provided by the iterator
    count = 0
    for batch in iterator:
        batch_images = batch[0].view()
        count += batch_images.shape[0]

    del iterator
    
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")

    return output_image_count, tile_image_count, count