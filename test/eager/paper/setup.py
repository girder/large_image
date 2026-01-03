import os
import json
from typing import Optional
import random
import shutil

import large_image
from large_image.tilesource.eager_utils.eager_wsi_operations import calculate_slide_dimensions

def print_directory_slide_dimensions(file_dir: str, file_extensions: list[str] = [".tif", ".svs", ".mrxs", ".ndpi"], scale: Optional[dict] = None, tile_size: Optional[dict] = None):
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                file_path = os.path.join(root, file)
                source = large_image.open(file_path)
                metadata = source.getMetadata()
                slide_dimensions = calculate_slide_dimensions(source, scale=scale, tile_size=tile_size)
                print(f"{file_path}: \n {json.dumps(metadata, indent=4)} \n {json.dumps(slide_dimensions, indent=4)}")

def copy_random_files_from_file_directory(file_dir: str, n_files: int = 10, file_extensions: list[str] = [".tif", ".svs", ".mrxs", ".ndpi"], destination_dir: str = "./test_files", large_image_meta_match: Optional[dict] = None):
    os.makedirs(destination_dir, exist_ok=True)
    copy_paths = []

    # Use walk in case of nested directories
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                file_path = os.path.join(root, file)
                copy_paths.append(file_path)
            else:
                pass

    random.shuffle(copy_paths)

    count = 0
    
    for copy_path in copy_paths:
        filename = os.path.basename(copy_path)
        source = large_image.open(copy_path)

        acceptable_metadata = {}

        # Compare metadata if needed
        if large_image_meta_match is not None:
            metadata = source.getMetadata()

            for key, value in large_image_meta_match.items():
                if metadata[key] == value:
                    acceptable_metadata[key] = True
                else:
                    acceptable_metadata[key] = False
                    break
        else:
            acceptable_metadata['none_needed'] = True

        if all(acceptable_metadata.values()) and copy_path.endswith(".mrxs"):
            split_ext = os.path.splitext(filename)
            mrxs_dir = os.path.join(file_dir, split_ext[0])
            if not os.path.exists(mrxs_dir):
                raise FileNotFoundError(f"MRXS directory does not exist: {mrxs_dir}")
            destination_path = os.path.join(destination_dir, filename)

            if os.path.exists(destination_path):
                print(f"Skipping {copy_path} because destination path already exists: {destination_path}")
                continue

            shutil.copytree(mrxs_dir, os.path.join(destination_dir, split_ext[0]))
            shutil.copy(copy_path, destination_path)

            print(f"Copied {copy_path} to {destination_path}")

            count += 1
            if count >= n_files:
                break

            
            
        elif all(acceptable_metadata.values()):
            destination_path = os.path.join(destination_dir, filename)

            if os.path.exists(destination_path):
                print(f"Skipping {copy_path} because destination path already exists: {destination_path}")
                continue
            
            shutil.copy(copy_path, destination_path)

            print(f"Copied {copy_path} to {destination_path}")

            count += 1
            if count >= n_files:
                break

if __name__ == "__main__":
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/cancer_imaging_archive", destination_dir="/scr/arosado/large_image/ndpi")
    copy_random_files_from_file_directory(
        file_dir="/wsi_archive/public/HEROHEGC/Training", 
        destination_dir="/scr/arosado/large_image/mrxs_new",
         n_files=10, 
         large_image_meta_match={'magnification': 20.0, 'levels': 10, 'tileWidth': 256, 'tileHeight': 256}
    )
    # copy_random_files_from_file_directory(file_dir="/scr/arosado/tcga", destination_dir="/scr/arosado/large_image/svs", n_files=2, large_image_meta_match={'magnification': 40.0, 'levels': 10, 'tileWidth': 256, 'tileHeight': 256})
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/HEROHEGC/Training", destination_dir="/scr/arosado/large_image/mrxs", n_files=1, large_image_meta_match={'magnification': 20.0})
    print_directory_slide_dimensions(file_dir="/scr/arosado/large_image/mrxs_new", scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224})
    # print_directory_slide_dimensions(file_dir="/scr/arosado/large_image/svs", scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224})
    # print_directory_slide_dimensions(file_dir="/scr/arosado/large_image/ndpi", scale={'mm_x': 0.0005, 'mm_y': 0.0005}, tile_size={'width': 224, 'height': 224})
    pass