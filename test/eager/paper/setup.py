import json
import os
import random
import shutil
from typing import Optional

import large_image
from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions


def print_directory_slide_dimensions(
    file_dir: str,
    file_extensions: list[str] = None,
    scale: Optional[dict] = None,
    tile_size: Optional[dict] = None,
):
    if file_extensions is None:
        file_extensions = ['.tif', '.svs', '.mrxs', '.ndpi']
    for root, _dirs, files in os.walk(file_dir):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                file_path = os.path.join(root, file)
                source = large_image.open(file_path)
                metadata = source.getMetadata()
                slide_dimensions = calculate_slide_dimensions(
                    source,
                    scale=scale,
                    tile_size=tile_size,
                )
                print(
                    f'{file_path}: '
                    f'{json.dumps(metadata, indent=4)} '
                    f'{json.dumps(slide_dimensions, indent=4)}',
                )


def iter_candidate_slide_paths(file_dir: str, file_extensions: list[str]):
    for root, _dirs, files in os.walk(file_dir):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                yield os.path.join(root, file)


def metadata_matches(source, large_image_meta_match: Optional[dict] = None):
    if large_image_meta_match is None:
        return True

    metadata = source.getMetadata()
    return all(metadata[key] == value for key, value in large_image_meta_match.items())


def copy_slide_path(copy_path: str, file_dir: str, destination_dir: str):
    filename = os.path.basename(copy_path)
    destination_path = os.path.join(destination_dir, filename)

    if os.path.exists(destination_path):
        print(
            f'Skipping {copy_path} because destination path already exists: {destination_path}',
        )
        return False

    if copy_path.endswith('.mrxs'):
        split_ext = os.path.splitext(filename)
        mrxs_dir = os.path.join(file_dir, split_ext[0])
        if not os.path.exists(mrxs_dir):
            msg = f'MRXS directory does not exist: {mrxs_dir}'
            raise FileNotFoundError(msg)
        shutil.copytree(mrxs_dir, os.path.join(destination_dir, split_ext[0]))

    shutil.copy(copy_path, destination_path)
    print(f'Copied {copy_path} to {destination_path}')
    return True


def copy_random_files_from_file_directory(
    file_dir: str,
    n_files: int = 10,
    file_extensions: list[str] = None,
    destination_dir: str = './test_files',
    large_image_meta_match: Optional[dict] = None,
):
    if file_extensions is None:
        file_extensions = ['.tif', '.svs', '.mrxs', '.ndpi']
    os.makedirs(destination_dir, exist_ok=True)

    copy_paths = list(iter_candidate_slide_paths(file_dir, file_extensions))
    random.shuffle(copy_paths)

    count = 0
    for copy_path in copy_paths:
        source = large_image.open(copy_path)
        if not metadata_matches(source, large_image_meta_match):
            continue

        copied = copy_slide_path(copy_path, file_dir, destination_dir)
        if copied:
            count += 1
        if count >= n_files:
            break


if __name__ == '__main__':
    copy_random_files_from_file_directory(
        file_dir='/wsi_archive/public/cancer_imaging_archive',
        destination_dir='/scr/arosado/large_image/ndpi',
        n_files=10,
        large_image_meta_match={
            'magnification': 40.0,
            'levels': 10,
            'tileWidth': 256,
            'tileHeight': 256,
        },
    )

    print_directory_slide_dimensions(
        file_dir='/scr/arosado/large_image/ndpi',
        scale={'mm_x': 0.0005, 'mm_y': 0.0005},
        tile_size={'width': 224, 'height': 224},
    )
