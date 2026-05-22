import torch

from ..eager_helpers import test_torch_shared_array

if __name__ == '__main__':
    shared_array = test_torch_shared_array()
    assert shared_array.view().shape == (256, 256, 3)
    assert shared_array.view().dtype == torch.uint8
    assert shared_array.view().flags.owndata
    assert shared_array.view().flags.writeable
    assert shared_array.view().flags.aligned
    assert shared_array.view().flags.c_contiguous
    assert not shared_array.view().flags.f_contiguous
