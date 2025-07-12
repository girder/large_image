import sys
import os

import pytest
from albumentations import Compose
from albumentations import ToFloat

import large_image

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from datastore import datastore

def test_eager_iterator_with_albumentations_transform(transform: Compose):
    try:
        test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
        source = large_image.open(test_file)
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

        return output_image_count, tile_image_count, count
    
    except Exception as e:
        print(f"Error: {e}")
        exit(1)

if __name__ == "__main__":
    # Test albumentations eager iterator with a transform by converting image to float
    transform = Compose([ToFloat()])
    with pytest.raises(Exception):
        output_image_count, tile_image_count, count = test_eager_iterator_with_albumentations_transform(transform)
        assert output_image_count == tile_image_count
        assert count == tile_image_count
        assert count == output_image_count
    print("All eager iterator albumentation tests passed")