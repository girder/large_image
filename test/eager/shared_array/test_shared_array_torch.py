import torch
from large_image.tilesource.eager_utils.eager_shared_array import SharedArray

# Test shared array default

shared_array = SharedArray([256, 256, 3], torch.uint8, True)

assert shared_array.view().shape == (256, 256, 3)
assert shared_array.view().dtype == torch.uint8

print("Shared array torch test passed")