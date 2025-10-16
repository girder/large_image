import os
import random
import shutil

def copy_random_files_from_file_directory(file_dir: str, n_files: int = 10, file_extensions: list[str] = [".tif", ".svs", ".mrxs", ".ndpi"], destination_dir: str = "./test_files"):
    os.makedirs(destination_dir, exist_ok=True)
    files = []

    # Use walk in case of nested directories
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            if file.endswith(tuple(file_extensions)):
                files.append(os.path.join(root, file))

    random.shuffle(files)
    
    for file in files[:n_files]:
        file_path = os.path.join(file_dir, file)
        
        if file.endswith(".mrxs"):
            split_ext = os.path.splitext(file)
            mrxs_dir = os.path.join(file_dir, split_ext[0])
            if not os.path.exists(mrxs_dir):
                raise FileNotFoundError(f"MRXS directory does not exist: {mrxs_dir}")
            shutil.copytree(mrxs_dir, os.path.join(destination_dir, split_ext[0]))
            shutil.copy(file_path, os.path.join(destination_dir, file))

            destination_path = os.path.join(destination_dir, file)
            
        else:
            destination_path = os.path.join(destination_dir, file)
            shutil.copy(file_path, destination_path)

if __name__ == "__main__":
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/cancer_imaging_archive", destination_dir="/scr/arosado/large_image/ndpi")
    # copy_random_files_from_file_directory(file_dir="/wsi_archive/public/HEROHEGC/Training", destination_dir="/scr/arosado/large_image/mrxs")
    copy_random_files_from_file_directory(file_dir="/scr/arosado/tcga", destination_dir="/scr/arosado/large_image/svs")