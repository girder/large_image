import os

import large_image


def test_mrxs_file(file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f'File not found: {file_path}')

    if not file_path.endswith('.mrxs'):
        raise ValueError(f'File is not an MRXS file: {file_path}')

    source = large_image.open(file_path)
    eager_iterator = source.eagerIterator()
    for batch in eager_iterator:
        print(batch)


if __name__ == '__main__':
    test_mrxs_file('/wsi_archive/MTSinai/36816_8_Tau_1.mrxs')
