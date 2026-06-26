import numpy as np
import pytest

from ...datastore import datastore
from ..eager_helpers import run_eager_iterator_numpy_dtype


@pytest.mark.singular
@pytest.mark.parametrize(
    'dtype',
    [np.float32, np.uint8, np.uint16, np.uint32, np.uint64, np.int8, np.int16, np.int32, np.int64],
)
def test_numpy_dtype(dtype):
    test_file = datastore.fetch('TCGA-AA-A02O-11A-01-BS1.8b76f05c-4a8b-44ba-b581-6b8b4f437367.svs')
    run_eager_iterator_numpy_dtype(test_file, dtype)


if __name__ == '__main__':
    test_numpy_dtype()
