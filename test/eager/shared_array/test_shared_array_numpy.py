import numpy as np
from large_image.tilesource.eager_utils.eager_shared_array import SharedArray

# Test shared array default

shared_array = SharedArray([256, 256, 3], np.uint8, False)

assert shared_array.view().shape == (256, 256, 3)
assert shared_array.view().dtype == np.uint8
assert shared_array.view().flags.owndata == False
assert shared_array.view().flags.writeable == True
assert shared_array.view().flags.aligned == True
assert shared_array.view().flags.c_contiguous == True
assert shared_array.view().flags.f_contiguous == False

print("Shared array numpy test passed")