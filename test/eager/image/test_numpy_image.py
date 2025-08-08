import os

from test.eager.test_eager_iter import test_eager_iterator_image

if __name__ == "__main__":
    test_image_path = os.path.join('/wsi_archive', 'TCGA', 'acc', 'TCGA-OR-A5J1-01A-01-TS1.CFE08710-54B8-45B0-86AE-500D6E36D8A5.svs')
    output_dir_path = os.path.join('/scr', 'arosado', 'test_eager_iterator_image', 'numpy_image')
    os.makedirs(output_dir_path, exist_ok=True)
    test_eager_iterator_image(test_image_path, output_dir_path)
    pass