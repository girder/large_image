import numpy as np

import pytest

from ..eager_helpers import build_numpy_shared_array

@pytest.mark.parametrize("shared_array_shape", [(256, 256, 3), (512, 512, 4)])
def test_numpy_shared_array(shared_array_shape: tuple[int, int, int]):
    shared_array = build_numpy_shared_array(shared_array_shape)
    assert shared_array.view().shape == shared_array_shape
    assert shared_array.view().dtype == np.uint8
    assert shared_array.view().flags.owndata == False
    assert shared_array.view().flags.writeable == True
    assert shared_array.view().flags.aligned == True
    assert shared_array.view().flags.c_contiguous == True
    assert shared_array.view().flags.f_contiguous == False

# Test shared array default
if __name__ == "__main__":
    test_numpy_shared_array((256, 256, 3))