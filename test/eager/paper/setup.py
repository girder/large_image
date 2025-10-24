import os
import random
import shutil

def copy_random_files_from_file_directory(file_dir: str, n_files: int = 10, file_extensions: list[str] = [".tif", ".svs", ".mrxs", ".ndpi"], destination_dir: str = "./test_files"):
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
    
    for copy_path in copy_paths[:n_files]:
        filename = os.path.basename(copy_path)       
        if copy_path.endswith(".mrxs"):
            split_ext = os.path.splitext(filename)
            mrxs_dir = os.path.join(file_dir, split_ext[0])
            if not os.path.exists(mrxs_dir):
                raise FileNotFoundError(f"MRXS directory does not exist: {mrxs_dir}")
            shutil.copytree(mrxs_dir, os.path.join(destination_dir, split_ext[0]))
            shutil.copy(file_path, os.path.join(destination_dir, filename))

            destination_path = os.path.join(destination_dir, filename)
            
        else:
            destination_path = os.path.join(destination_dir, filename)
            shutil.copy(copy_path, destination_path)

if __name__ == "__main__":
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/cancer_imaging_archive", destination_dir="/scr/arosado/large_image/ndpi")
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/HEROHEGC/Training", destination_dir="/scr/arosado/large_image/mrxs")
    copy_random_files_from_file_directory(file_dir="/scr/arosado/tcga", destination_dir="/scr/arosado/large_image/svs", n_files=1)