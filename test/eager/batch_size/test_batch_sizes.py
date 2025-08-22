import pytest

import large_image
from ..eager_helpers import run_batch_size

from ...datastore import datastore

@pytest.mark.parametrize("batch_size", [1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024])
def test_batch_size(batch_size: int):
    test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
    source = large_image.open(test_file)
    run_batch_size(source, batch_size)

if __name__ == "__main__":
    test_batch_size(64)