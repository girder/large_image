import pytest
import albumentations as A

import large_image

from ...datastore import datastore

from ..eager_helpers import run_eager_iterator_with_albumentations_transform

@pytest.mark.parametrize("transform", [
    A.Compose([
        A.ToFloat(),
        A.Resize(288, 288),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
])
def test_albumentations_transform(transform: A.Compose):
    test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
    source = large_image.open(test_file)
    output_image_count, tile_image_count, count = run_eager_iterator_with_albumentations_transform(source, transform)
    assert output_image_count == tile_image_count
    assert count == tile_image_count
    assert count == output_image_count

if __name__ == "__main__":
    transform = A.Compose([
        A.ToFloat(),
        A.Resize(288, 288),
        A.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])
    test_albumentations_transform(transform)