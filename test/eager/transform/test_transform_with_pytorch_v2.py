import pytest
import torch
import torchvision.transforms.v2 as v2

import large_image

from ...datastore import datastore
from ..eager_helpers import run_eager_iterator_with_pytorch_transform


@pytest.mark.singular
@pytest.mark.parametrize(
    'transform',
    [
        v2.Compose(
            [
                v2.Resize(224),
                v2.ToTensor(),
                v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
            ],
        ),
        v2.Compose(
            [
                v2.ToImage(),
                v2.RandomResizedCrop(size=(288, 288), antialias=True),
                v2.RandomHorizontalFlip(p=0.5),
                v2.ToDtype(torch.float32, scale=True),
                v2.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ],
        ),
    ],
)
def test_pytorch_v2_transform(transform: v2.Compose):
    test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
    source = large_image.open(test_file)

    output_image_count, tile_image_count, count = run_eager_iterator_with_pytorch_transform(
        source,
        transform,
    )
    assert output_image_count == tile_image_count
    assert count == tile_image_count
    assert count == output_image_count


if __name__ == '__main__':
    transform = v2.Compose(
        [
            v2.Resize(224),
            v2.ToTensor(),
            v2.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ],
    )

    test_pytorch_v2_transform(transform)
