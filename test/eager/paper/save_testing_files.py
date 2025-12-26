import os
from typing import Any

import large_image
import numpy as np
from matplotlib import pyplot as plt

# Define top-level function so it can be pickled in multiprocessing pool
def save_image_function(image: np.ndarray, tile_x: int, tile_y: int):
        output_path = os.path.join(output_dir, f"tile_{tile_x}_{tile_y}.png")
        if tile_x >= 0 and tile_y >= 0:
            plt.imsave(output_path, image)
        return image

def save_testing_file(file_path: str, output_dir: str, **kwargs: Any):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    if not os.path.exists(output_dir):
        raise FileNotFoundError(f"Output directory not found: {output_dir}")

    if not os.path.isdir(output_dir):
        raise ValueError(f"Output directory is not a directory: {output_dir}")
    
    source = large_image.open(file_path)

    eager_iter = source.eagerIterator(transform=save_image_function, **kwargs)

    for batch in eager_iter:
        print("Retrieved batch of tiles...")

    print("Saved all batches")


if __name__ == "__main__":
    input_path = '/scr/arosado/tcga/acc/5b9efa00e62914002e94791c_TCGA-OR-A5LL-01Z-00-DX1.08588029-C532-4CDD-B945-251315EFF5C0.svs'
    output_dir = '/scr/arosado/large_image/svs_test_tiles'

    save_testing_file(input_path, output_dir, transform_save_mode='tile_x_y')